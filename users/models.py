from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class Company(models.Model):
    """
    Represents the overarching corporate entity owned by a Company Owner.
    """
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Branch(models.Model):
    """
    Represents individual branches belonging to a Company.
    """
    #  CORRECT
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Branches"

    def __str__(self):
        return f"{self.company.name} - {self.name}"

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    Custom User Model supporting system admins, company owners, and branch staff roles.
    Username and email are SEPARATE fields.
    Login can be with either username OR email.
    """
    class Role(models.TextChoices):
        SUPERUSER = 'SUPERUSER', _('Admin Superuser')
        OWNER = 'OWNER', _('Company Owner')
        LOAN_APPROVAL = 'LOAN_APPROVAL', _('Loan Approval Officer')
        MANAGER = 'MANAGER', _('Manager')
        CASHIER = 'CASHIER', _('Cashier')
        FIELD_OFFICER = 'FIELD_OFFICER', _('Field Officer')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.FIELD_OFFICER
    )

    # Username and email are separate, both unique, no syncing
    email = models.EmailField(unique=True, help_text="Used for login and temp password email.")
    must_change_password = models.BooleanField(
        default=True,
        help_text="If True, user is forced to change password on next login."
    )

    company = models.ForeignKey(
        'Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text="Applicable for Company Owners and Staff members."
    )
    branch = models.ForeignKey(
        'Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff',
        help_text="Applicable for Branch-level staff members."
    )

    # Login field is still email for Django internals,
    # but our custom backend also allows login with username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.SUPERUSER
        # No syncing username <-> email. They stay separate.
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # Helpers for your permission checks
    def is_loan_approver(self):
        return self.role in [self.Role.LOAN_APPROVAL, self.Role.MANAGER, self.Role.OWNER, self.Role.SUPERUSER]

    def is_manager_or_above(self):
        return self.role in [self.Role.MANAGER, self.Role.OWNER, self.Role.SUPERUSER]
        
        