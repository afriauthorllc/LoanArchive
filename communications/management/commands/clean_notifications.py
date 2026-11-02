# management/commands/clean_notifications.py
from django.core.management.base import BaseCommand
from communications.tasks import clean_old_read_notifications
class Command(BaseCommand):
    def handle(self, *args, **options):
        clean_old_read_notifications()
        self.stdout.write("Cleaned old notifications")
        
        