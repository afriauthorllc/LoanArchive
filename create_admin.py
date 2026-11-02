import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LoanArchive.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

USERNAME = os.getenv("ADMIN_USER", "admin")
EMAIL = os.getenv("ADMIN_EMAIL", "admin@lms.com")
PASSWORD = os.getenv("ADMIN_PASS", "Admin123!")

if not User.objects.filter(username=USERNAME).exists():
    User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
    print(f"SUPERUSER CREATED: {USERNAME} / {PASSWORD}")
else:
    print(f"SUPERUSER EXISTS: {USERNAME}")

