import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LoanArchive.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

USERNAME = os.getenv("ADMIN_USER", "admin")
EMAIL = "methtrevor3@gmail.com"
PASSWORD = os.getenv("ADMIN_PASS", "Admin123!")

# 1. Fix the Neon bug: blank emails break the unique index
blank_users = User.objects.filter(email__isnull=True) | User.objects.filter(email='')
for u in blank_users:
    if u.username == USERNAME:
        continue
    u.email = f"user_{u.id}@temp.local"
    u.save(update_fields=['email'])
    print(f"FIXED blank email for: {u.username}")

# 2. If another user already owns this admin email, free it
conflict = User.objects.filter(email=EMAIL).exclude(username=USERNAME).first()
if conflict:
    print(f"Email {EMAIL} was taken by {conflict.username}, freeing it...")
    conflict.email = f"old_{conflict.id}@temp.local"
    conflict.save(update_fields=['email'])

# 3. Create or UPDATE admin
user, created = User.objects.get_or_create(
    username=USERNAME,
    defaults={'email': EMAIL}
)
user.email = EMAIL
user.set_password(PASSWORD)
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.save()

if created:
    print(f"SUPERUSER CREATED: {USERNAME} / {EMAIL}")
else:
    print(f"SUPERUSER UPDATED: {USERNAME} / {EMAIL} (password reset)")
    
