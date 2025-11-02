from rest_framework import serializers
from .models import Team, Availability, MatchRequest, ChatMessage
from django.contrib.auth.models import User

# Basic Serializer for related fields
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class TeamSerializer(serializers.ModelSerializer):
    manager_username = serializers.CharField(source='manager.username', read_only=True)
    
    class Meta:
        model = Team
        fields = ['id', 'name', 'skill_level', 'location', 'manager', 'manager_username']
        read_only_fields = ['manager']

class AvailabilitySerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = Availability
        fields = ['id', 'team', 'team_name', 'day_of_week', 'start_time', 'end_time']
        read_only_fields = ['team']

class MatchRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source='requester.name', read_only=True)
    receiver_name = serializers.CharField(source='receiver.name', read_only=True)

    class Meta:
        model = MatchRequest
        fields = ['id', 'requester', 'requester_name', 'receiver', 'receiver_name', 
                  'status', 'match_time', 'location', 'created_at', 'updated_at']
        read_only_fields = ['requester', 'status', 'created_at', 'updated_at']

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = ChatMessage
        fields = ['id', 'match_request', 'sender', 'sender_username', 'timestamp', 'content']
        read_only_fields = ['sender', 'match_request']
