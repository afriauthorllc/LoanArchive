from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from clients.models import Client
from loans.models import Loan
from .models import Notification

def notify_admins(type, priority, title, message, link):
    User = get_user_model()
    admins = User.objects.filter(is_staff=True)
    for admin in admins:
        Notification.objects.create(
            user=admin, 
            type=type, 
            priority=priority,
            title=title, 
            message=message, 
            link=link
        )

@receiver(post_save, sender=Client)
def client_created(sender, instance, created, **kwargs):
    if created:
        notify_admins('client','low',
            'New Client Registered',
            f'{instance.full_name} added',
            f'/clients/{instance.id}/')

@receiver(post_save, sender=Loan)
def loan_created(sender, instance, created, **kwargs):
    if created:
        notify_admins('loan_application','medium',
            'New Loan Application',
            f'{instance.client.full_name} - UGX {instance.amount} needs approval',
            f'/loans/{instance.id}/')