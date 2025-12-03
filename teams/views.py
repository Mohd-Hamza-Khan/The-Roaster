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
    # MatchRequestSerializer,
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
# create a fuction which accept and reject match request named as match_request_detail
class MatchRequestDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'teams/match_request_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match_request = get_object_or_404(MatchRequest, pk=self.kwargs['pk'])
        
        # Authorization check: must be a manager of one of the participating teams
        if not (match_request.requester.manager == self.request.user or match_request.receiver.manager == self.request.user):
            raise PermissionDenied("You do not have permission to view this match request.")
        
        context['match_request'] = match_request
        context['chat_messages'] = ChatMessage.objects.filter(match_request=match_request).order_by('timestamp')
        return context


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
    next_page = reverse_lazy('teams:home')
    
    # This override forces the logout to be processed when a GET request hits the URL.
    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

# --- Profile View (NEW) ---

class ProfileView(LoginRequiredMixin, TemplateView):
    """Displays the currently logged-in user's profile information."""
    template_name = 'teams/profile.html'
    # No extra context needed, as Django automatically provides 'user

class HomeView(TemplateView):
    """The main landing page for the application."""
    template_name = 'teams/home.html'
    # No extra context needed, as Django automatically provides 'user

class DashboardView(LoginRequiredMixin, TemplateView):
    """User dashboard showing managed teams and match requests."""
    template_name = 'teams/dashboard.html'

    # Redirect unauthenticated users to the login page
    login_url = '/teams/login/'  # or use reverse_lazy('login') if named URL
    redirect_field_name = 'next'  # optional, Django uses this by default

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
            # --- 2. Use first team as 'current' team (if multiple) ---
            current_team = user_teams.first()
            context['current_team'] = current_team

            # --- 3. Filter match requests for the team(s) ---
            match_requests = MatchRequest.objects.filter(
                Q(requester__in=user_teams) | Q(receiver__in=user_teams)
            ).select_related('requester', 'receiver').order_by('-created_at')

            # --- 4. Split pending into incoming/outgoing ---
            outgoing_pending = match_requests.filter(requester=current_team, status__in=['P', 'A', 'R', 'C'])
            incoming_pending = match_requests.filter(receiver=current_team,  status__in=['P', 'A', 'R', 'C'])

            # --- 5. Add all categorized data to context ---
            context.update({
                'outgoing_pending': outgoing_pending,
                'incoming_pending': incoming_pending,
                'pending_count': outgoing_pending.count() + incoming_pending.count(),
                'active_requests': match_requests.filter(status__in=['A', 'C']),
                'history_requests': match_requests.filter(status='R'),
            })

            return context

class TeamCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """View to create a new team."""
    model = Team
    fields = ['name', 'location']
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
    fields = ['name','location'] 
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
