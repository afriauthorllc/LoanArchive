from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import UniqueConstraint, Sum

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

    class Meta:
        ordering = ['-collected_at']
        verbose_name = "Repayment Record"
        verbose_name_plural = "Repayment Records"
        # FIX 1: constraints must be INSIDE Meta
        constraints = [
            UniqueConstraint(
                fields=['branch', 'collection_date', 'book_number'], 
                name='unique_book_per_day_per_branch'
            )
        ]

    def __str__(self):
        return f"Book #{self.book_number} - UGX {self.amount_paid:,.0f} for {self.loan}"

    def clean(self):
        super().clean()
        # loan may not be loaded yet
        if self.loan_id:
            loan = self.loan if hasattr(self, 'loan') and self.loan else None
            # if not in memory, fetch status quickly
            status = getattr(loan, 'status', None) if loan else self.__class__.objects.filter(pk=self.loan_id).values_list('loan__status', flat=True).first()
            # safer: check via self.loan
            if hasattr(self, 'loan') and self.loan and self.loan.status not in ['DISBURSED', 'DEFAULTED']:
                raise ValidationError(_("Repayments can only be logged against Disbursed or Defaulted loans."))

        # Manual duplicate check for nice error message
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

    def save(self, *args, **kwargs):
        # FIX 2: set branch BEFORE full_clean
        if not self.branch_id:
            if not self.loan_id:
                raise ValidationError(_("Loan is required to determine branch"))
            # get branch from loan without extra query if possible
            self.branch = self.loan.branch if hasattr(self.loan, 'branch') else self.loan.__class__.objects.select_related('branch').get(pk=self.loan_id).branch

        self.full_clean()
        super().save(*args, **kwargs)
        
        # FIX 3: update balance + status properly
        parent_loan = self.loan
        total_loan_liability = parent_loan.total_payable
        total_collected = parent_loan.repayments.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

        # update loan fields if you have them
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
            
            
            