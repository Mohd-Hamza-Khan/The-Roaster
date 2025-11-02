from django.contrib import admin
from .models import Team, Availability, MatchRequest, ChatMessage

# --- Custom ModelAdmin classes ---

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Admin configuration for the Team model."""
    list_display = ('name', 'manager', 'skill_level', 'location')
    list_filter = ('skill_level', 'location', 'manager')
    search_fields = ('name', 'manager__username', 'location')
    ordering = ('name',)

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    """Admin configuration for the Availability model."""
    list_display = ('team', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('team', 'day_of_week')
    search_fields = ('team__name',)
    ordering = ('team__name', 'day_of_week', 'start_time')

@admin.register(MatchRequest)
class MatchRequestAdmin(admin.ModelAdmin):
    """Admin configuration for the MatchRequest model."""
    list_display = (
        'requester', 
        'receiver', 
        'match_time', 
        'location', 
        'status', 
        'created_at'
    )
    list_filter = ('status', 'requester', 'receiver')
    search_fields = (
        'requester__name', 
        'receiver__name', 
        'location'
    )
    # Allows direct modification of the status on the list page
    list_editable = ('status',) 
    date_hierarchy = 'match_time'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin configuration for the ChatMessage model."""
    list_display = (
        'match_request', 
        'sender', 
        'timestamp', 
        'content_preview'
    )
    list_filter = ('match_request', 'sender')
    search_fields = (
        'match_request__pk', 
        'sender__username', 
        'content'
    )
    readonly_fields = ('match_request', 'sender', 'timestamp', 'content')

    def content_preview(self, obj):
        """Displays a truncated version of the message content."""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
