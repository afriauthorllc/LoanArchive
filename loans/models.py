from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

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

    # 💰 Financial Particulars (Using Decimal for financial accuracy)
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

    @property
    def total_payable(self):
        """Calculates simple flat interest total."""
        interest_amount = (self.principal_amount * (self.interest_rate / Decimal('100'))) * self.duration_months
        return self.principal_amount + interest_amount
        

    def __str__(self):
        return f"Loan #{self.id} - {self.client.full_name} ({self.get_status_display()})"
        
    @property
    def total_repayments_made(self):
        """
        Dynamically aggregates the sum of all transaction logs recorded for this loan.
        """
        # We handle the import inside the method to cleanly bypass any potential circular import errors
        total = self.repayments.aggregate(models.Sum('amount_paid'))['amount_paid__sum']
        return total or Decimal('0.00')

    @property
    def outstanding_balance(self):
        """
        Computes the remaining debt balance (Total Payable minus Total Payments Made).
        """
        balance = self.total_payable - self.total_repayments_made
        # Safeguard against micro-fraction floating balance outputs under 0
        return max(balance, Decimal('0.00'))
    
        
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.core.exceptions import ValidationError

class Repayment(models.Model):
    """
    Tracks transaction installments collected against active loans.
    Uses Physical Book Number as the Primary Key.
    """
    class ModeOfPayment(models.TextChoices):
        CASH = 'CASH', _('Cash')
        MOBILE_MONEY = 'MOBILE_MONEY', _('Mobile Money (MTN/Airtel)')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')

    # 🔑 PRIMARY KEY IS THE BOOK NUMBER
    # This is the number written against the payment in the book: 1, 2, 3...
    book_number = models.CharField(
        primary_key=True,
        max_length=50,
        help_text=_("The entry number from the physical collection book (e.g. 1, 2, 45 or CB-2026-001)"),
        verbose_name="Book No / Receipt No"
    )

    # 🔗 Account Relationships
    loan = models.ForeignKey(
        'loans.Loan', 
        on_delete=models.PROTECT, 
        related_name='repayments'
    )
    
    # 💰 Transaction Particulars
    amount_paid = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('500.00'))],
        help_text=_("The payment amount collected (UGX).")
    )
    payment_mode = models.CharField(
        max_length=20,
        choices=ModeOfPayment.choices,
        default=ModeOfPayment.CASH
    )
    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Enter Mobile Money Transaction ID or Bank Slip number if applicable.")
    )
    
    # 👥 Audit Trails
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='collections',
        help_text=_("The staff member who processed the payment.")
    )
    
    # ⏳ Timestamps
    collected_at = models.DateTimeField(
        default=timezone.now,
        help_text=_("The exact date and time the payment was made.")
    )

    class Meta:
        ordering = ['-collected_at']
        verbose_name = "Repayment Record"
        verbose_name_plural = "Repayment Records"

    def __str__(self):
        return f"Book #{self.book_number} - UGX {self.amount_paid:,.0f} for {self.loan}"

    def clean(self):
        super().clean()
        if self.loan.status not in ['DISBURSED', 'DEFAULTED']:
            raise ValidationError(
                _("Repayments can only be logged against Disbursed or Defaulted loans.")
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        
        parent_loan = self.loan
        total_loan_liability = parent_loan.total_payable
        total_collected = parent_loan.repayments.aggregate(
            total=models.Sum('amount_paid')
        )['total'] or Decimal('0.00')

        if total_collected >= total_loan_liability:
            parent_loan.status = 'FULLY_PAID'
            parent_loan.save(update_fields=['status'])