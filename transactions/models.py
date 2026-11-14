from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import UniqueConstraint, Sum
import secrets, string

class Repayment(models.Model):
    class ModeOfPayment(models.TextChoices):
        CASH = 'CASH', _('Cash')
        MOBILE_MONEY = 'MOBILE_MONEY', _('Mobile Money (MTN/Airtel)')
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')

    ID = models.BigAutoField(primary_key=True)

    # Book resets daily per branch: Branch A Day 1 = 1,2,3 / Day 2 = 1,2,3 again
    book_number = models.PositiveIntegerField(
        verbose_name="Book No / Receipt No",
        help_text=_("Type exactly as in physical book: 1, 2, 45")
    )
    collection_date = models.DateField(auto_now=True, db_index=True)

    branch = models.ForeignKey(
        'users.Branch',
        on_delete=models.PROTECT,
        related_name='transactions',
        editable=False
    )
    loan = models.ForeignKey(
        'loans.Loan',
        on_delete=models.PROTECT,
        related_name='repayments'
    )

    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('500.00'))]
    )
    payment_mode = models.CharField(max_length=20, choices=ModeOfPayment.choices, default=ModeOfPayment.CASH)
    transaction_reference = models.CharField(max_length=100, blank=True)

    collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='collections')
    collected_at = models.DateTimeField(default=timezone.now)

    # ===== QR Verification - RCT format, no branch code =====
    # Example: RCT-20261114-7-X8K29P
    verify_code = models.CharField(
        max_length=60, unique=True, blank=True, db_index=True,
        help_text="Secret code in QR: e.g. RCT-20261114-7-X8K29P"
    )
    is_voided = models.BooleanField(default=False)

    class Meta:
        ordering = ['-collected_at']
        verbose_name = "Repayment Record"
        verbose_name_plural = "Repayment Records"
        constraints = [
            UniqueConstraint(
                fields=['branch', 'collection_date', 'book_number'],
                name='unique_book_per_day_per_branch'
            )
        ]

    def __str__(self):
        return f"Book #{self.book_number} - UGX {self.amount_paid:,.0f} for {self.loan}"

    @property
    def verify_url(self):
        base = getattr(settings, 'SITE_URL', 'https://loanarchive.com')
        return f"{base}/verify/?code={self.verify_code}"

    @property
    def receipt_no(self):
        return f"Book #{self.book_number}"

    def clean(self):
        super().clean()

        # --- 1. Loan must be active ---
        loan = None
        if self.loan_id:
            try:
                loan = self.loan
            except Exception:
                loan = None
            if loan and loan.status not in ['DISBURSED', 'DEFAULTED']:
                raise ValidationError(_("Repayments can only be logged against Disbursed or Defaulted loans."))

        # --- 2. Duplicate Book No check ---
        if self.branch_id and self.collection_date and self.book_number:
            qs = self.__class__.objects.filter(
                branch=self.branch, collection_date=self.collection_date, book_number=self.book_number
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({
                    'book_number': _(f"Book No {self.book_number} already used today in {self.branch}.")
                })

        # --- 3. REJECT PAYMENT BEYOND BALANCE ---
        if self.loan_id and self.amount_paid:
            from loans.models import Loan
            try:
                loan_obj = Loan.objects.get(pk=self.loan_id)
            except Loan.DoesNotExist:
                return

            total_payable = loan_obj.total_payable or Decimal('0.00')

            # Sum of all NON-VOIDED repayments, excluding THIS one if editing
            qs = self.__class__.objects.filter(loan_id=self.loan_id, is_voided=False)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            already_paid = qs.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

            remaining = total_payable - already_paid

            if remaining <= 0:
                raise ValidationError({
                    'amount_paid': _("This loan is already fully paid. Balance is UGX 0. No more payments needed.")
                })

            if self.amount_paid > remaining:
                raise ValidationError({
                    'amount_paid': _(
                        f"Amount UGX {self.amount_paid:,.0f} is more than the remaining balance of UGX {remaining:,.0f}. "
                        f"Total payable is UGX {total_payable:,.0f}, already paid UGX {already_paid:,.0f}."
                    )
                })

    def save(self, *args, **kwargs):
        # Set branch BEFORE full_clean
        if not self.branch_id:
            if not self.loan_id:
                raise ValidationError(_("Loan is required to determine branch"))
            self.branch = self.loan.branch if hasattr(self.loan, 'branch') else self.loan.__class__.objects.select_related('branch').get(pk=self.loan_id).branch

        # If collection_date not set yet, use today for code generation
        if not self.collection_date:
            self.collection_date = timezone.now().date()

        # Generate verify_code once, on first save
        # NEW FORMAT: RCT-20261114-7-X8K29P  (no BUG / no branch)
        if not self.verify_code:
            alphabet = string.ascii_uppercase + string.digits
            random_part = ''.join(secrets.choice(alphabet) for _ in range(6))
            date_str = self.collection_date.strftime('%Y%m%d')
            self.verify_code = f"RCT-{date_str}-{self.book_number}-{random_part}"

        self.full_clean()
        super().save(*args, **kwargs)

        # Update balance + status
        parent_loan = self.loan
        total_loan_liability = parent_loan.total_payable
        total_collected = parent_loan.repayments.filter(is_voided=False).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

        updates = {}
        if hasattr(parent_loan, 'total_paid'):
            parent_loan.total_paid = total_collected
            updates['total_paid'] = total_collected
        if hasattr(parent_loan, 'balance'):
            parent_loan.balance = total_loan_liability - total_collected
            if parent_loan.balance < 0:
                parent_loan.balance = Decimal('0.00')
            updates['balance'] = parent_loan.balance

        if total_collected >= total_loan_liability:
            parent_loan.status = 'FULLY_PAID'
            updates['status'] = 'FULLY_PAID'

        if updates:
            parent_loan.save(update_fields=list(updates.keys()))
            
            
            