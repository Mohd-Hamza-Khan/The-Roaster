from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, CreateView, UpdateView
from django.contrib.auth.views import LoginView, LogoutView 
from django.forms import modelformset_factory  # Add this import
from .forms import CustomUserCreationForm, AvailabilityForm  # Also import AvailabilityForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied

from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models import Prefetch

from .models import Team, Availability, MatchRequest, ChatMessage
from .serializers import (
    TeamSerializer,
    AvailabilitySerializer,
    MatchRequestSerializer,
    ChatMessageSerializer,
    MatchingTeamSerializer,
)


from django.db.models import Q, Max
from django.contrib.auth import get_user_model
from teams import serializers # NOTE: This import should be reviewed if not explicitly used for forms/serializers validation

User = get_user_model()

# --- Permissions and Mixins ---

class IsTeamManagerMixin(UserPassesTestMixin):
    """Mixin to ensure the user is the manager of the team being accessed."""
    def test_func(self):
        team_pk = self.kwargs.get('pk')
        try:
            team = Team.objects.get(pk=team_pk)
            return team.manager == self.request.user
        except Team.DoesNotExist:
            return False

class IsMatchParticipantPermission(IsAuthenticated):
    """
    Custom DRF permission to allow access only to users who are 
    either the requester's manager or the receiver's manager.
    """
    def has_object_permission(self, request, view, obj):
        # We need to find if the user manages EITHER the requester or the receiver team
        is_manager_of_requester = obj.requester.manager == request.user
        is_manager_of_receiver = obj.receiver.manager == request.user
        
        return is_manager_of_requester or is_manager_of_receiver

# --- Helper Logic for Matchmaking ---

def find_available_teams(requesting_team):
    """
    Find teams with the same skill_level, different manager, and overlapping availability.
    Accepts a Team instance or a team PK. Returns a Team QuerySet.
    """
    # allow passing pk or instance
    if isinstance(requesting_team, int):
        requesting_team = Team.objects.filter(pk=requesting_team).first()
        if requesting_team is None:
            return Team.objects.none()

    # 1) candidate teams: same skill, different manager, not the same team
    candidates = Team.objects.exclude(pk=requesting_team.pk).filter(
        skill_level=requesting_team.skill_level
    ).exclude(manager=requesting_team.manager)

    if not candidates.exists():
        return Team.objects.none()

    # 2) requester availabilities
    requester_avails = list(requesting_team.availabilities.all())
    if not requester_avails:
        return Team.objects.none()

    # 3) collect team ids that have any overlapping availability
    available_team_ids = set()
    for r in requester_avails:
        overlapping = Availability.objects.filter(
            team__in=candidates,
            day_of_week=r.day_of_week,
            start_time__lt=r.end_time,   # A_start < B_end
            end_time__gt=r.start_time    # A_end > B_start
        ).values_list('team_id', flat=True)
        available_team_ids.update(overlapping)

    if not available_team_ids:
        return Team.objects.none()

    # return final queryset (distinct, ordered)
    return Team.objects.filter(pk__in=available_team_ids).distinct().order_by('name')
# --- 1. Template Views (Django Class-Based Views) ---

# NEW: Authentication Views
class RegisterView(CreateView):
    """View to register a new user using the default UserCreationForm."""
    form_class = CustomUserCreationForm
    template_name = 'teams/registration/register.html'
    success_url = reverse_lazy('teams:login') 

class CustomLoginView(LoginView):
    """Overrides default LoginView to use custom template."""
    template_name = 'teams/registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('teams:dashboard')

class CustomLogoutView(LogoutView):
    """
    Custom LogoutView to define the next page after logout.
    Fixes the HTTP 405 error by handling GET requests as POST requests.
    """
    next_page = reverse_lazy('teams:login')
    
    # This override forces the logout to be processed when a GET request hits the URL.
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

# --- Profile View (NEW) ---

class ProfileView(LoginRequiredMixin, TemplateView):
    """Displays the currently logged-in user's profile information."""
    template_name = 'teams/profile.html'
    # No extra context needed, as Django automatically provides 'user

class DashboardView(LoginRequiredMixin, TemplateView):
    """User dashboard showing managed teams and match requests."""
    template_name = 'teams/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Correctly fetching managed teams and annotating with last match date
        user_teams = Team.objects.filter(manager=user).annotate(
            # Using the correct related name 'outgoing_requests' for the Team model
            last_match_date=Max('outgoing_requests__match_time') 
        ).order_by('-last_match_date')
        
        context['user_teams'] = user_teams
        
        if user_teams.exists():
            current_team = user_teams.first() 
            context['current_team'] = current_team
            
            # Match requests where the user's team is the requester or receiver
            match_requests = MatchRequest.objects.filter(
                Q(requester__in=user_teams) | Q(receiver__in=user_teams) # CORRECTED: using 'receiver'
            ).order_by('-created_at')
            
            context['pending_requests'] = match_requests.filter(status='P')
            context['active_requests'] = match_requests.filter(status__in=['A', 'C'])
            context['history_requests'] = match_requests.filter(status__in=['R'])

        return context

class TeamCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """View to create a new team."""
    model = Team
    fields = ['name', 'skill_level', 'location']
    template_name = 'teams/team_form.html'
    success_message = "Team '%(name)s' was created successfully!"

    def form_valid(self, form):
        # Set the current logged-in user as the manager
        form.instance.manager = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('teams:dashboard')

class TeamUpdateView(LoginRequiredMixin, IsTeamManagerMixin, SuccessMessageMixin, UpdateView):
    """View to edit an existing team."""
    model = Team
    # NOTE: Assuming 'description' is a field on your Team model. 
    # If not, remove it. Fields here should match your model.
    fields = ['name', 'skill_level', 'location'] 
    template_name = 'teams/team_form.html'
    success_message = "Team '%(name)s' was updated successfully!"

    def get_success_url(self):
        return reverse('teams:dashboard')

class AvailabilityManagementView(LoginRequiredMixin, TemplateView):
    template_name = 'teams/availability_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = get_object_or_404(Team, pk=self.kwargs['pk'], manager=self.request.user)
        
        AvailabilityFormSet = modelformset_factory(
            Availability, 
            form=AvailabilityForm,
            extra=0,
            max_num=10,  # Maximum number of slots allowed
            can_delete=True
        )
        
        formset = AvailabilityFormSet(
            queryset=Availability.objects.filter(team=team),
            prefix='form'
        )
        
        context.update({
            'team': team,
            'formset': formset,
            'availability_list': team.availabilities.all().order_by('day_of_week', 'start_time')
        })
        return context

    def post(self, request, *args, **kwargs):
        team = get_object_or_404(Team, pk=self.kwargs['pk'], manager=request.user)
        
        AvailabilityFormSet = modelformset_factory(
            Availability, 
            form=AvailabilityForm,
            extra=0,
            max_num=10,
            can_delete=True
        )
        
        formset = AvailabilityFormSet(
            request.POST,
            prefix='form',
            queryset=Availability.objects.filter(team=team)
        )
        
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.team = team
                instance.save()
            formset.save_m2m()
            
            # Handle deletions
            for obj in formset.deleted_objects:
                obj.delete()
                
            return redirect('teams:availability_manage', pk=team.pk)
        
        return self.render_to_response(self.get_context_data(formset=formset))

class MatchFinderView(LoginRequiredMixin, TemplateView):
    template_name = 'teams/match_finder.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the day parameter from the request
        day = self.request.GET.get('day')
        
        # Get the current user's managed teams
        user_teams = self.request.user.managed_teams.all()
        
        # Initialize available teams queryset
        available_teams = Team.objects.none()
        
        if day:
            # Get teams that have availability on the selected day
            # excluding the user's own teams
            available_teams = Team.objects.filter(
                availabilities__day_of_week=day
            ).exclude(
                id__in=user_teams.values_list('id', flat=True)
            ).prefetch_related(
                Prefetch(
                    'availabilities',
                    queryset=Availability.objects.filter(day_of_week=day).order_by('start_time'),
                    to_attr='day_availabilities'
                )
            ).distinct()

        context.update({
            'day_choices': Availability.DAY_CHOICES,
            'available_teams': available_teams,
            'selected_day': day,
            'user_teams': user_teams
        })
        
        return context

class MatchRequestDetailView(LoginRequiredMixin, TemplateView):
    """Template view to show match request status and integrated chat."""
    template_name = 'teams/match_request_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match_request = get_object_or_404(MatchRequest, pk=self.kwargs['pk'])
        user_teams = Team.objects.filter(manager=self.request.user)

        # Ensure the user manages one of the participant teams (requester or receiver)
        is_participant = user_teams.filter(
            Q(pk=match_request.requester.pk) | Q(pk=match_request.receiver.pk)
        ).exists()

        if not is_participant:
            raise PermissionDenied("You are not a participant in this match request.")

        context['match_request'] = match_request

        # Role booleans for the template
        is_requester_manager = (match_request.requester.manager == self.request.user)
        is_receiver_manager = (match_request.receiver.manager == self.request.user)

        context['is_requester'] = is_requester_manager
        context['is_receiver'] = is_receiver_manager

        # current_team = the team managed by the current user; other_team_name for display
        context['current_team'] = match_request.requester if is_requester_manager else match_request.receiver
        context['other_team_name'] = match_request.receiver.name if is_requester_manager else match_request.requester.name

        # JS endpoints used by match_request_detail.html — adjust if your API routes differ
        context['chat_api_url'] = reverse('api:chatmessage-list') + f'?match_request_pk={match_request.pk}'
        context['request_api_url'] = reverse('api:matchrequest-detail', kwargs={'pk': match_request.pk})

        return context

# --- 2. API Views (Django REST Framework) ---

class MatchingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        day_param = request.GET.get('day')
        user_team = request.user.managed_teams.first()

        if not day_param:
            return Response({"detail": "A 'day' query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not user_team:
            return Response({"detail": "You must manage a team to find matches."}, status=status.HTTP_403_FORBIDDEN)

        # Find teams available on the selected day, excluding the user's own team.
        # We also prefetch the availabilities for that specific day to optimize queries.
        available_teams = Team.objects.filter(
            availabilities__day_of_week=day_param
        ).exclude(
            id=user_team.id
        ).prefetch_related(
            Prefetch(
                'availabilities',
                queryset=Availability.objects.filter(day_of_week=day_param).order_by('start_time')
            )
        ).distinct()

        # Serialize the data. The serializer will handle the nested structure.
        serializer = MatchingTeamSerializer(available_teams, many=True)
        return Response(serializer.data)

class AvailabilityViewSet(viewsets.ModelViewSet):
    """
    API for managing a team's availability.
    Users can only manage availability for their own team.
    """
    serializer_class = AvailabilitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_teams_pk = self.request.user.managed_teams.values_list('pk', flat=True)
        return Availability.objects.filter(team_id__in=user_teams_pk)

    def perform_create(self, serializer):
        team_id = self.request.data.get('team')
        # Ensure the team exists and is managed by the current user
        team = get_object_or_404(Team, pk=team_id, manager=self.request.user)
        serializer.save(team=team)


class ChatMessageViewSet(viewsets.ModelViewSet):
    """
    API for creating and viewing chat messages within a match request.
    Only allows read and create operations.
    """
    serializer_class = ChatMessageSerializer
    
    # We apply the participant check later for flexibility
    permission_classes = [IsAuthenticated] 
    
    def get_queryset(self):
        match_request_pk = self.kwargs.get('match_request_pk')
        if not match_request_pk:
            return ChatMessage.objects.none()

        match_request = get_object_or_404(MatchRequest, pk=match_request_pk)
        
        # Authorization check: must be a manager of one of the participating teams
        if not IsMatchParticipantPermission().has_object_permission(self.request, self, match_request):
            raise PermissionDenied("You are not a participant in this chat.")

        return ChatMessage.objects.filter(match_request__pk=match_request_pk).order_by('timestamp')

    def perform_create(self, serializer):
        match_request_pk = self.kwargs.get('match_request_pk')
        match_request = get_object_or_404(MatchRequest, pk=match_request_pk)
        
        user_team = Team.objects.filter(manager=self.request.user).first()

        serializer.save(match_request=match_request, sender=self.request.user, sender_team=user_team)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class MatchRequestViewSet(viewsets.ModelViewSet):
    """
    API for creating, viewing, and managing Match Requests.
    Includes custom actions for accepting and rejecting requests.
    """
    serializer_class = MatchRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_teams_pk = self.request.user.managed_teams.values_list('pk', flat=True)
        return MatchRequest.objects.filter(
            Q(requester_id__in=user_teams_pk) | Q(receiver_id__in=user_teams_pk)
        ).order_by('-created_at')

    def perform_create(self, serializer):
        # Set the requester team automatically
        requester_team = Team.objects.filter(manager=self.request.user).first()
        if not requester_team:
            raise serializers.ValidationError("User must manage a team to send a match request.")
        
        serializer.save(requester=requester_team, status='P') # Status is pending by default

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        match_request = self.get_object()
        user_team = Team.objects.filter(manager=request.user).first()
        
        if match_request.receiver != user_team:
            return Response(
                {"detail": "Only the receiving team can accept this request."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if match_request.status != 'P':
            return Response(
                {"detail": "Match request is not pending."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        match_request.status = 'A' # Accepted
        match_request.save()
        
        serializer = self.get_serializer(match_request)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        match_request = self.get_object()
        user_team = Team.objects.filter(manager=request.user).first()

        if match_request.receiver != user_team:
            return Response(
                {"detail": "Only the receiving team can reject this request."},
                status=status.HTTP_403_FORBIDDEN
            )

        if match_request.status != 'P':
            return Response(
                {"detail": "Match request is not pending."},
                status=status.HTTP_400_BAD_REQUEST
            )

        match_request.status = 'R' # Rejected
        match_request.save()
        
        serializer = self.get_serializer(match_request)
        return Response(serializer.data)