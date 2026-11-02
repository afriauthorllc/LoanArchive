# tasks.py
from .models import StaffNotification
from django.utils import timezone
from datetime import timedelta

def clean_old_read_notifications(days=30):
    cutoff = timezone.now() - timedelta(days=days)
    StaffNotification.objects.filter(is_read=True, created_at__lt=cutoff).delete()
    
    