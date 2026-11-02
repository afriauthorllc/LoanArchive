from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from .models import Client
from communications.models import StaffNotification
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=Client)
def notify_branch_on_new_client(sender, instance, created, **kwargs):
    if not created:
        return
    
    # Who added the client
    added_by = getattr(instance, 'created_by', None) or getattr(instance, 'added_by', None)
    branch = getattr(instance, 'branch', None) or getattr(added_by, 'branch', None) if added_by else None
    
    # Get all staff in same branch, except the one who created
    staff_qs = User.objects.filter(is_active=True)
    if branch:
        staff_qs = staff_qs.filter(branch=branch)
    
    # Exclude creator
    if added_by and added_by.id:
        staff_qs = staff_qs.exclude(id=added_by.id)
    
    # Fallback if no branch field - notify all staff
    if not staff_qs.exists():
        staff_qs = User.objects.filter(is_active=True).exclude(id=getattr(added_by, 'id', None))
    
    client_name = f"{instance.first_name} {instance.last_name}" if hasattr(instance, 'first_name') else str(instance)
    creator_name = str(added_by) if added_by else "A staff"
    
    # Build link - to client detail page
    try:
        link = reverse('clients:detail', args=[instance.id])
    except:
        link = f"/clients/{instance.id}/"
    
    notifications = []
    for user in staff_qs:
        notifications.append(
            StaffNotification(
                recipient=user,
                title="New Client Added",
                message=f"{creator_name} added new client: {client_name} in {branch or 'branch'}",
                client=instance,
                loan=None,
                link=link,
            )
        )
    
    if notifications:
        StaffNotification.objects.bulk_create(notifications)
        
        