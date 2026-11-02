# billing/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

def default_trial_end():
    return timezone.now() + timedelta(days=30)

def default_expiry():
    return timezone.now() + timedelta(days=30)

class Subscription(models.Model):
    branch = models.OneToOneField('users.Branch', on_delete=models.CASCADE, related_name='billing_subscription')
    plan_name = models.CharField(max_length=50, default='1 Branch - 65k')
    amount = models.IntegerField(default=65000)
    
    is_trial = models.BooleanField(default=True)
    trial_started_at = models.DateTimeField(default=timezone.now)
    trial_ends_at = models.DateTimeField(default=default_trial_end)
    
    status = models.CharField(max_length=20, default='trial')
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(default=default_expiry)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def days_left(self):
        if self.is_trial:
            delta = self.trial_ends_at - timezone.now()
        else:
            delta = self.expires_at - timezone.now()
        return max(0, delta.days)

    @property
    def is_trial_active(self):
        return self.is_trial and self.trial_ends_at > timezone.now()

    @property
    def progress_percent(self):
        if self.is_trial:
            elapsed = (timezone.now() - self.trial_started_at).days
        else:
            elapsed = (timezone.now() - self.starts_at).days if self.starts_at else 0
        return min(100, int((elapsed/30)*100))

    def activate_paid(self):
        self.is_trial = False
        self.status = 'active'
        self.starts_at = timezone.now()
        self.expires_at = timezone.now() + timedelta(days=30)
        self.save()

class Payment(models.Model):
    branch = models.ForeignKey('users.Branch', on_delete=models.CASCADE, related_name='billing_payments')
    amount = models.IntegerField()
    method = models.CharField(max_length=10, default='mtn')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, default='completed')
    created_at = models.DateTimeField(auto_now_add=True)
    
    