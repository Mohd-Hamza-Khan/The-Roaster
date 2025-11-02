from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import time, timedelta
from .models import Team, Availability, MatchRequest, ChatMessage

class ModelValidationTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='manager1', password='password')
        self.user2 = User.objects.create_user(username='manager2', password='password')
        self.teamA = Team.objects.create(name='Dragons', manager=self.user1, skill_level='3', location='Park A')
        self.teamB = Team.objects.create(name='Tigers', manager=self.user2, skill_level='3', location='Park B')

    def test_team_creation(self):
        self.assertEqual(self.teamA.skill_level, '3')
        self.assertEqual(self.teamA.manager.username, 'manager1')

    def test_availability_creation(self):
        Availability.objects.create(team=self.teamA, day_of_week='MON', start_time=time(18, 0), end_time=time(20, 0))
        self.assertEqual(self.teamA.availabilities.count(), 1)
        
    def test_match_request_self_validation(self):
        # Test the constraint that a team cannot request a match against itself
        with self.assertRaises(Exception): # Catches the IntegrityError from the CheckConstraint
            MatchRequest.objects.create(
                requester=self.teamA, 
                receiver=self.teamA, 
                match_time=timezone.now() + timedelta(days=7)
            )

    def test_chat_message_creation(self):
        match_time = timezone.now() + timedelta(days=1)
        match_req = MatchRequest.objects.create(
            requester=self.teamA, 
            receiver=self.teamB, 
            match_time=match_time
        )
        msg = ChatMessage.objects.create(
            match_request=match_req, 
            sender=self.user1, 
            content="Can we meet at 7?"
        )
        self.assertEqual(msg.content, "Can we meet at 7?")
        self.assertEqual(match_req.chat_messages.count(), 1)


class MatchingLogicTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='u1', password='p')
        self.user2 = User.objects.create_user(username='u2', password='p')
        self.user3 = User.objects.create_user(username='u3', password='p')

        # Target Team (Team X) - Skill 3
        self.teamX = Team.objects.create(name='Team X', manager=self.user1, skill_level='3')
        Availability.objects.create(team=self.teamX, day_of_week='MON', start_time=time(19, 0), end_time=time(21, 0))
        
        # Potential Match 1 (Team A) - Skill 3, Available MON
        self.teamA = Team.objects.create(name='Team A', manager=self.user2, skill_level='3')
        Availability.objects.create(team=self.teamA, day_of_week='MON', start_time=time(18, 0), end_time=time(22, 0))
        
        # Potential Match 2 (Team B) - Skill 2, Available TUE
        self.teamB = Team.objects.create(name='Team B', manager=self.user3, skill_level='2')
        Availability.objects.create(team=self.teamB, day_of_week='TUE', start_time=time(18, 0), end_time=time(22, 0))
        
        # Potential Match 3 (Team C) - Skill 4, Available MON
        self.teamC = Team.objects.create(name='Team C', manager=self.user3, skill_level='4')
        Availability.objects.create(team=self.teamC, day_of_week='MON', start_time=time(18, 0), end_time=time(22, 0))
        
    def test_skill_level_filtering(self):
        # Teams with skill level 2, 3, or 4 should be found for a skill 3 search (skill +/- 1)
        eligible_teams = Team.objects.filter(skill_level__range=('2', '4')).exclude(pk=self.teamX.pk)
        self.assertIn(self.teamA, eligible_teams) # Skill 3
        self.assertIn(self.teamB, eligible_teams) # Skill 2
        self.assertIn(self.teamC, eligible_teams) # Skill 4
        self.assertEqual(eligible_teams.count(), 3)
        
    def test_availability_and_skill_matching(self):
        # Search for skill 3 on Monday
        target_skill = 3
        target_day = 'MON'
        
        skill_low = max(1, target_skill - 1)
        skill_high = min(4, target_skill + 1)
        
        eligible_teams = Team.objects.filter(
            skill_level__range=(str(skill_low), str(skill_high))
        ).exclude(manager=self.user1) # Exclude teams managed by user1 (Team X)

        available_teams_ids = Availability.objects.filter(
            day_of_week=target_day,
            team__in=eligible_teams
        ).values_list('team_id', flat=True).distinct()
        
        final_matches = Team.objects.filter(id__in=available_teams_ids)
        
        # Should find Team A (Skill 3, MON) and Team C (Skill 4, MON)
        self.assertIn(self.teamA, final_matches)
        self.assertIn(self.teamC, final_matches)
        self.assertNotIn(self.teamB, final_matches) # Available TUE
        self.assertEqual(final_matches.count(), 2)

    def test_no_match_found(self):
        # Search for skill 1 (only Team B is skill 2) on Sunday
        target_skill = 1
        target_day = 'SUN'
        
        skill_low = max(1, target_skill - 1) # 1
        skill_high = min(4, target_skill + 1) # 2
        
        eligible_teams = Team.objects.filter(
            skill_level__range=(str(skill_low), str(skill_high))
        ).exclude(manager=self.user1)
        
        # Eligible teams for skill 1 (range 1-2) are only Team B (Skill 2)
        # However, Team B is only available TUE, not SUN
        
        available_teams_ids = Availability.objects.filter(
            day_of_week=target_day, # SUN
            team__in=eligible_teams
        ).values_list('team_id', flat=True).distinct()
        
        final_matches = Team.objects.filter(id__in=available_teams_ids)
        self.assertEqual(final_matches.count(), 0)
