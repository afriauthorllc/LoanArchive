from decimal import Decimal
from django.utils import timezone
from . import staff
# from . import sms  # SMS DISABLED for now - uncomment when ready for Africa's Talking

def on_payment_received(client, loan, amount):
    """
    Triggered when a Repayment with amount_paid is saved.
    - loan is loans.Loan instance
    - client is clients.Client with full_name
    - amount is Decimal from repayment.amount_paid
    """
    amount = Decimal(amount)
    
    # Use your real properties: total_payable, total_repayments_made, outstanding_balance
    balance = getattr(loan, 'outstanding_balance', Decimal('0.00'))
    total_paid = getattr(loan, 'total_repayments_made', amount)

    staff.notify_all_branch_staff(
        client, loan, 
        type='payment_received', 
        title=f"UGX {amount:,.0f} Received",
        message=f"{client.full_name} paid UGX {amount:,.0f} for Loan #{loan.id}. Total paid: UGX {total_paid:,.0f}, Balance: UGX {balance:,.0f}",
        link=f"/loans/{loan.id}/"
    )
    
    # SMS disabled - leave commented
    # sms.send_payment_confirmation(client, loan, amount)

def on_loan_cleared(client, loan):
    """
    Triggered when loan.outstanding_balance == 0
    Should also update Loan.status to FULLY_PAID
    """
    # Auto-update status to your real Status choice
    if loan.status != loan.Status.FULLY_PAID:
        loan.status = loan.Status.FULLY_PAID
        loan.save(update_fields=['status'])

    # 1. Cleared notification
    staff.notify_all_branch_staff(
        client, loan, 
        type='loan_cleared',
        title=f"Loan #{loan.id} Fully Paid",
        message=f"{client.full_name} has fully cleared Loan #{loan.id} (UGX {loan.total_payable:,.0f}).",
        link=f"/clients/{client.id}/"
    )

    # 2. Qualifies for new loan
    staff.notify_all_branch_staff(
        client, loan, 
        type='qualifies_for_loan',
        title="Qualifies For New Loan",
        message=f"{client.full_name} now qualifies for another loan - previous Loan #{loan.id} cleared. Guarantor: {loan.guarantor_name or 'N/A'}",
        link=f"/clients/{client.id}/loans/create/"
    )

def on_loan_created(client, loan):
    """Call this from loans/views.py after Loan.objects.create()"""
    staff.notify_all_branch_staff(
        client, loan,
        type='loan_created',
        title=f"New Loan Application #{loan.id}",
        message=f"{client.full_name} applied for UGX {loan.principal_amount:,.0f} at {loan.interest_rate}% for {loan.duration_months} month(s).",
        link=f"/loans/{loan.id}/"
    )

def on_branch_renewed(branch, subscription=None):
    staff.notify_superuser(branch, subscription, type='subscription_renewed')

def on_loan_overdue(client, loan):
    """Use this in a daily cron for overdue loans"""
    days_overdue = (timezone.now().date() - loan.disbursed_at.date()).days - (loan.duration_months * 30) if loan.disbursed_at else 0
    staff.notify_all_branch_staff(
        client, loan,
        type='loan_overdue',
        title=f"Loan #{loan.id} Overdue",
        message=f"Loan #{loan.id} for {client.full_name} is overdue by {days_overdue} days. Balance: UGX {loan.outstanding_balance:,.0f}",
        link=f"/loans/{loan.id}/"
    )
    