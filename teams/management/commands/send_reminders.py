from django.core.management.base import BaseCommand
from django.utils import timezone
from teams.models import MatchRequest

from datetime import timedelta

class Command(BaseCommand):
    help = 'Sends reminders for accepted matches scheduled in the next 24 hours.'

    def handle(self, *args, **options):
        # Calculate time window: 24 hours from now
        now = timezone.now()
        one_day_later = now + timedelta(hours=24)

        # Find accepted matches within the next 24 hours
        upcoming_matches = MatchRequest.objects.filter(
            status='ACCEPTED',
            match_time__gte=now,
            match_time__lt=one_day_later
        )

        if not upcoming_matches.exists():
            self.stdout.write(self.style.NOTICE('No upcoming accepted matches found for reminder window.'))
            return

        for match in upcoming_matches:
            message = (
                f"[REMINDER] Match scheduled! {match.requester.name} vs {match.receiver.name} "
                f"is happening in less than 24 hours on {match.match_time.strftime('%Y-%m-%d %H:%M')}. "
                f"Location: {match.location[:50]}..."
            )
            # In a real application, you would send an email/notification here.
            self.stdout.write(self.style.SUCCESS(message))

        self.stdout.write(self.style.SUCCESS(f'Successfully checked and sent {len(upcoming_matches)} reminders.'))
