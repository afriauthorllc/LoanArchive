# users/utils.py
import secrets
import string
from django.core.mail import send_mail
from django.conf import settings
from .models import User

def generate_temp_password(length=10):
    """Generate a random temp password like 'aB3xK9pQ2z'"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_staff_and_email(admin_user, first_name, last_name, email, role, branch=None):
    """
    Creates a staff user for the same company as admin_user,
    sets a temp password, and emails it to them.
    Returns: (user, temp_password)
    """
    temp_password = generate_temp_password()

    user = User.objects.create(
        first_name=first_name,
        last_name=last_name,
        email=email,
        username=email,
        role=role,
        company=admin_user.company,  # auto-inherit company
        branch=branch,
        must_change_password=True,
        is_active=True,
    )
    user.set_password(temp_password)
    user.save()

    send_mail(
        subject='Your LoanArchive Account is Ready',
        message=f"""Hello {first_name},

Your LoanArchive account has been created by {admin_user.get_full_name()}.

Login at: https://loanarchive.com/login
Email: {email}
Temporary Password: {temp_password}
Role: {user.get_role_display()}
Company: {user.company}

Please login and change your password immediately.

- LoanArchive Team
        """,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
    return user, temp_password
    
    
    