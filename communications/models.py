from django.db import models
from django.conf import settings

class BaseLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# --- 1. STAFF BELL NOTIFICATIONS ---
class StaffNotification(BaseLog):
    class Type(models.TextChoices):
        SUBSCRIPTION_RENEWED = 'subscription_renewed', 'Branch Renewed Subscription'
        SUBSCRIPTION_EXPIRING = 'subscription_expiring', 'Subscription Expiring Soon'
        SUBSCRIPTION_EXPIRED = 'subscription_expired', 'Subscription Expired'
        LOAN_CREATED = 'loan_created', 'New Loan Created'
        LOAN_CLEARED = 'loan_cleared', 'Client Cleared Loan'  # maps to Loan.FULLY_PAID
        LOAN_EXPIRED = 'loan_expired', 'Loan Expired'
        LOAN_OVERDUE = 'loan_overdue', 'Loan Overdue'
        QUALIFIES_FOR_LOAN = 'qualifies_for_loan', 'Qualifies For New Loan'
        PAYMENT_RECEIVED = 'payment_received', 'Payment Received'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='staff_notifications',
        db_index=True
    )
    branch = models.ForeignKey(
        'users.Branch', 
        null=True, blank=True, 
        on_delete=models.CASCADE,
        db_index=True
    )
    client = models.ForeignKey(
        'clients.Client', 
        null=True, blank=True, 
        on_delete=models.CASCADE,
        db_index=True
    )
    loan = models.ForeignKey(
        'loans.Loan', 
        null=True, blank=True, 
        on_delete=models.CASCADE,
        db_index=True
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=35, choices=Type.choices, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    link = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['branch', 'type']),
        ]
        verbose_name = "Staff Notification"
        verbose_name_plural = "Staff Notifications"

    def __str__(self):
        # Uses your real Loan id, not loan_number
        loan_ref = f"Loan #{self.loan.id}" if self.loan_id else ""
        return f"[{self.get_type_display()}] {self.title} {loan_ref}"

    @property
    def is_payment(self):
        return self.type == self.Type.PAYMENT_RECEIVED

# --- 2. CLIENT SMS (DISABLED FOR NOW) ---
class SMSLog(BaseLog):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        DISABLED = 'disabled', 'Disabled'

    branch = models.ForeignKey('users.Branch', on_delete=models.CASCADE, related_name='sms_logs')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='sms_logs')
    loan = models.ForeignKey('loans.Loan', null=True, blank=True, on_delete=models.SET_NULL)
    phone = models.CharField(max_length=20, db_index=True)
    message = models.TextField()
    type = models.CharField(max_length=30, default='payment_received', db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DISABLED)
    provider_response = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SMS to {self.client.full_name} - {self.status}"

# --- 3. EMAILS ---
class EmailLog(BaseLog):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_logs')
    to_email = models.EmailField(db_index=True)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    type = models.CharField(max_length=30, db_index=True) # password_reset, invite
    is_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"Email to {self.to_email} - {self.subject}"

# --- 4. WHATSAPP ---
class WhatsAppLog(BaseLog):
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='whatsapp_logs')
    loan = models.ForeignKey('loans.Loan', null=True, blank=True, on_delete=models.SET_NULL)
    phone = models.CharField(max_length=20)
    template_name = models.CharField(max_length=100)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='pending', db_index=True)

# --- 5. BROADCAST MARKETING ---
class BroadcastMessage(BaseLog):
    branch = models.ForeignKey('users.Branch', on_delete=models.CASCADE, related_name='broadcasts')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='broadcasts_created')
    message = models.TextField()
    channel = models.CharField(max_length=10, choices=[('sms','SMS'),('whatsapp','WhatsApp')], db_index=True)
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    @property
    def success_rate(self):
        if self.total_recipients == 0:
            return 0
        return (self.sent_count / self.total_recipients) * 100

class BroadcastRecipient(BaseLog):
    broadcast = models.ForeignKey(BroadcastMessage, on_delete=models.CASCADE, related_name='recipients')
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, default='pending', db_index=True)
    error_message = models.TextField(blank=True)

    class Meta:
        unique_together = ('broadcast', 'client')
        
        