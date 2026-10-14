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

class User(AbstractUser):
    """
    Custom User Model supporting system admins, company owners, and branch staff roles.
    """
    class Role(models.TextChoices):
        SUPERUSER = 'SUPERUSER', _('Admin Superuser')
        OWNER = 'OWNER', _('Company Owner')
        LOAN_APPROVAL = 'LOAN_APPROVAL', _('Loan Approval Officer')
        MANAGER = 'MANAGER', _('Manager')
        CASHIER = 'CASHIER', _('Cashier')
        FIELD_OFFICER = 'FIELD_OFFICER', _('Field Officer')

    # Extend base fields with role designation
    role = models.CharField(
        max_length=20, 
        choices=Role.choices, 
        default=Role.FIELD_OFFICER
    )
    
    # Relationships mapping to organizations
    company = models.ForeignKey(
        Company, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='users',
        help_text="Applicable for Company Owners and Staff members."
    )
    branch = models.ForeignKey(
        Branch, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='staff',
        help_text="Applicable for Branch-level staff members."
    )

    def save(self, *args, **kwargs):
        # Auto-assign role flag for Django's built-in superuser creation commands
        if self.is_superuser:
            self.role = self.Role.SUPERUSER
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
