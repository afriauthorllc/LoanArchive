from django.db import models
from django.conf import settings

class Notification(models.Model):
    TYPES = [
        ('loan_application', 'New Loan Application'),
        ('collection', 'Collection Due'),
        ('risk', 'At-Risk Alert'),
        ('client', 'New Client'),
        ('system', 'System'),
    ]
    PRIORITY = [('low','Low'),('medium','Medium'),('high','High'),('urgent','Urgent')]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='user_notifications'
    )
    type = models.CharField(max_length=20, choices=TYPES, default='system')
    priority = models.CharField(max_length=10, choices=PRIORITY, default='medium')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)  # e.g. /loans/5/
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"