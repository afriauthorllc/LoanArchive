from django.core.mail import send_mail
from ..models import EmailLog

def send_password_reset_email(user, reset_link):
    subject = "Reset your LoanArchive Password"
    body = f"Hi {user.get_full_name()}, click here to reset: {reset_link}"
    log = EmailLog.objects.create(recipient=user, to_email=user.email, subject=subject, body=body, type='password_reset')
    try:
        send_mail(subject, body, 'noreply@loanarchive.ug', [user.email])
        log.is_sent = True
    except Exception:
        log.is_sent = False
    log.save()
    
    