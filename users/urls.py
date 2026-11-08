# users/urls.py
from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views
from django.core.mail import send_mail
from django.http import HttpResponse

app_name = 'users'
def debug_email(request):
    import os, requests
    try:
        r = requests.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f"Bearer {os.environ.get('RESEND_API_KEY')}", 'Content-Type': 'application/json'},
            json={
                'from': 'LoanArchive <noreply@loanarchive.com>',
                'to': ['methtrevor3@gmail.com'],
                'subject': 'LoanArchive Test',
                'html': '<p>If you got this, Resend is working!</p>'
            },
            timeout=10,
        )
        return HttpResponse(f"STATUS: {r.status_code} - {r.text}")
    except Exception as e:
        return HttpResponse(f"ERROR: {e}")
        
urlpatterns = [
    path('debug-email/', debug_email),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.force_password_change, name='force_password_change'),

    # --- Password Reset ---
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='users/password_reset.html',
        email_template_name='users/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        success_url=reverse_lazy('users:password_reset_done'),
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html',
        success_url=reverse_lazy('users:password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'
    ), name='password_reset_complete'),
]

