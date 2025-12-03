from django.db import models
from django.contrib.auth.models import User

class Team(models.Model):
    """Represents a competitive team."""
    name = models.CharField(max_length=100, unique=True)
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_teams')
    location = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name

    def get_available_slots(self, day_code=None):
        """
        Returns QuerySet of availability slots, optionally filtered by day.
        Args:
            day_code (str, optional): One of MON, TUE, WED, THU, FRI, SAT, SUN
        """
        slots = self.availabilities.all()
        if day_code:
            slots = slots.filter(day_of_week=day_code)
        return slots.order_by('day_of_week', 'start_time')

    def to_dict(self, day_code=None):
        """
        Returns serialized team data with availabilities.
        Args:
            day_code (str, optional): If provided, only includes availability for that day
        """
        return {
            'id': self.pk,
            'name': self.name,
            'location': self.location,
            'availabilities': [
                {
                    'day_of_week': av.day_of_week,
                    'start_time': av.start_time.strftime('%H:%M'),
                    'end_time': av.end_time.strftime('%H:%M')
                }
                for av in self.get_available_slots(day_code)
            ]
        }

class Availability(models.Model):
    """Represents when a team is available to play."""
    DAY_CHOICES = [
        ('MON', 'Monday'), ('TUE', 'Tuesday'), ('WED', 'Wednesday'),
        ('THU', 'Thursday'), ('FRI', 'Friday'), ('SAT', 'Saturday'),
        ('SUN', 'Sunday')
    ]
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        verbose_name_plural = "Availabilities"
        unique_together = ('team', 'day_of_week', 'start_time', 'end_time')

    def __str__(self):
        return f"{self.team.name} available on {self.day_of_week} from {self.start_time} to {self.end_time}"

    def format_time(self, time_field):
        """Helper to format TimeField values consistently."""
        return time_field.strftime('%H:%M') if time_field else ''

    def to_dict(self):
        """Returns serialized availability data."""
        return {
            'day_of_week': self.day_of_week,
            'start_time': self.format_time(self.start_time),
            'end_time': self.format_time(self.end_time)
        }

class MatchRequest(models.Model):
    """Represents a request for a match between two teams."""
    STATUS_CHOICES = [
        ('P', 'Pending'),
        ('A', 'Accepted'),
        ('R', 'Rejected'),
        ('C', 'Cancelled'),
    ]
    requester = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='outgoing_requests')
    receiver = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='incoming_requests')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')
    
    # Proposed Match Details
    match_time = models.DateTimeField(verbose_name="Proposed Match Time")
    location = models.TextField(blank=True, verbose_name="Proposed Location")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # A team cannot request a match against themselves
        constraints = [
            models.CheckConstraint(
                check=~models.Q(requester=models.F('receiver')),
                name='requester_not_receiver'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Match Request: {self.requester} vs {self.receiver} ({self.status})"

    # --- Convenience helpers used by views/templates ---
    @property
    def responder(self):
        """
        Alias for 'receiver' — some views/templates referenced 'responder'.
        Keeps both names working.
        """
        return self.receiver

    def other_team(self, team):
        """
        Given one participant team instance (or its pk), return the other team.
        Useful for templates / views that need to display the opposite team.
        """
        team_pk = getattr(team, 'pk', team)
        if team_pk == self.requester_id:
            return self.receiver
        if team_pk == self.receiver_id:
            return self.requester
        return None

    def is_pending(self):
        return self.status == 'P'

    def is_accepted(self):
        return self.status == 'A'

    def is_rejected(self):
        return self.status == 'R'

    def is_requester(self, user):
        """
        Checks if the given user is the manager of the team that sent the request.
        Returns False if user is not authenticated.
        """
        return user.is_authenticated and self.requester.manager == user

class ChatMessage(models.Model):
    """Represents a message within the context of a MatchRequest."""
    match_request = models.ForeignKey(MatchRequest, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    content = models.TextField()
    sender_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='sent_messages', null=True)

    class Meta:
        ordering = ['timestamp']
        
    def __str__(self):
        return f"Msg by {self.sender.username} in {self.match_request.id}"
