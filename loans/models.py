from decimal import Decimal
import re
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# reuse your existing phone normalizer if you have it
def normalize_phone_number(phone):
    try:
        from clients.models import normalize_phone_number as norm
        return norm(phone)
    except Exception:
        return phone.strip() if phone else phone

class Loan(models.Model):
    """
    Represents a loan application and its lifecycle tracking.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending Evaluation')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        DISBURSED = 'DISBURSED', _('Disbursed / Active')
        FULLY_PAID = 'FULLY_PAID', _('Fully Paid')
        DEFAULTED = 'DEFAULTED', _('Defaulted')

    class Relationship(models.TextChoices):
        FAMILY = 'FAMILY', _('Family Member')
        FRIEND = 'FRIEND', _('Friend')
        COLLEAGUE = 'COLLEAGUE', _('Work Colleague')
        SPOUSE = 'SPOUSE', _('Spouse')
        PARENT = 'PARENT', _('Parent')
        SIBLING = 'SIBLING', _('Sibling')
        OTHER = 'OTHER', _('Other')

    # 🔗 Account Relationships
    client = models.ForeignKey(
        'clients.Client', 
        on_delete=models.PROTECT, 
        related_name='loans'
    )
    branch = models.ForeignKey(
        'users.Branch', 
        on_delete=models.PROTECT, 
        related_name='loans'
    )

    # 💰 Financial Particulars
    principal_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1000.00'))],
        help_text=_("The core amount requested or given (UGX).")
    )
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text=_("Flat interest percentage per period (e.g., 10.00 for 10%).")
    )
    duration_months = models.PositiveIntegerField(
        default=1,
        help_text=_("The repayment window in months.")
    )
    
    # 📝 Tracking & Collateral Description
    collateral_details = models.TextField(
        help_text=_("Detailed description of assets pinned down as security (e.g., Logbook, Land agreement).")
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )

    # 👥 Guarantor Information - nullable so old loans don't break
    guarantor_name = models.CharField(
        max_length=150,
        blank=True, null=True,
        help_text=_("Full name of the guarantor.")
    )
    guarantor_nin = models.CharField(
        max_length=14,
        blank=True, null=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9]{14}$',
                message=_("NIN must be 14 uppercase alphanumeric characters.")
            )
        ],
        help_text=_("Guarantor's 14-character NIN.")
    )
    guarantor_telephone = models.CharField(
        max_length=20,
        blank=True, null=True,
        help_text=_("Guarantor's phone contact.")
    )
    guarantor_relationship = models.CharField(
        max_length=20,
        choices=Relationship.choices,
        blank=True, null=True,
        help_text=_("Relationship of guarantor to client.")
    )

    # 👥 Audit Trails & Governance
    created_by_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_loans',
        help_text=_("The field officer who took the application.")
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_loans',
        limit_choices_to={'role__in': ['LOAN_APPROVAL', 'MANAGER', 'SUPERUSER']},
        help_text=_("The authorized staff member who evaluated or approved this loan.")
    )

    # ⏳ Timestamps
    applied_at = models.DateTimeField(auto_now_add=True)
    actioned_at = models.DateTimeField(null=True, blank=True, help_text=_("When it was approved or rejected."))
    disbursed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-applied_at']
        verbose_name = "Loan Application"
        verbose_name_plural = "Loan Applications"

    def clean(self):
        super().clean()
        if self.guarantor_nin:
            self.guarantor_nin = self.guarantor_nin.strip().upper()
            if not re.match(r'^[A-Z0-9]{14}$', self.guarantor_nin):
                raise ValidationError({'guarantor_nin': _("NIN must be a valid 14 character uppercase string.")})
        
        if self.guarantor_name:
            self.guarantor_name = ' '.join(self.guarantor_name.strip().split()).title()
        
        if self.guarantor_telephone:
            self.guarantor_telephone = normalize_phone_number(self.guarantor_telephone)

    @property
    def total_payable(self):
        interest_amount = (self.principal_amount * (self.interest_rate / Decimal('100'))) * self.duration_months
        return self.principal_amount + interest_amount

    def __str__(self):
        return f"Loan #{self.id} - {self.client.full_name} ({self.get_status_display()})"
        
    @property
    def total_repayments_made(self):
        total = self.repayments.aggregate(models.Sum('amount_paid'))['amount_paid__sum']
        return total or Decimal('0.00')

    @property
    def outstanding_balance(self):
        balance = self.total_payable - self.total_repayments_made
        return max(balance, Decimal('0.00'))
        
