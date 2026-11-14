#transactions/views.py
from django.shortcuts import render, get_object_or_404, redirect
from .services.executions import create_repayment, edit_repayment
from django.utils import timezone
from loans.models import Loan
from .models import Repayment
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
import datetime

@login_required
def repayment_page(request):
    return redirect('transactions:repayments')

# --- REPAYMENTS CORE ---
@login_required
def repayments_view(request):
    # Only DISBURSED and DEFAULTED loans can be repaid
    loans = Loan.objects.select_related('client', 'branch')\
        .filter(status__in=[Loan.Status.DISBURSED, Loan.Status.DEFAULTED])\
        .order_by('-disbursed_at', '-applied_at')

    # Field officers only see their own
    if hasattr(request.user, 'role') and request.user.role == 'FIELD_OFFICER':
        loans = loans.filter(created_by_officer=request.user)
    
    # Optional: filter by branch
    if hasattr(request.user, 'branch') and request.user.branch:
        loans = loans.filter(branch=request.user.branch)

    return render(request, 'loans/repayments.html', {
        'loans': loans,
        'disbursed_count': loans.filter(status='DISBURSED').count(),
        'defaulted_count': loans.filter(status='DEFAULTED').count(),
    })

@login_required
def check_book_number(request):
    book_no = request.GET.get('book_number','') or request.GET.get('book','')
    book_no = book_no.strip()
    if not book_no:
        return JsonResponse({'exists': False})
    
    today = timezone.localdate()
    exists = Repayment.objects.filter(
        book_number=book_no,
        collection_date=today
    ).exists()
    return JsonResponse({'exists': exists, 'date': str(today)})

def check_book_number_api(request):
    return check_book_number(request)
    
def repayment_live_filter(request):
    q = request.GET.get('q','').strip()
    repayments = Repayment.objects.select_related('loan__client').order_by('-collected_at')[:200]
    if q:
        repayments = repayments.filter(Q(book_number__icontains=q) | Q(loan__client__first_name__icontains=q) | Q(loan__client__last_name__icontains=q))
    return render(request, 'loans/live_filter.html', {'repayments': repayments, 'q': q})

def view_repayments(request):
    selected_date_str = request.GET.get('date', '').strip()

    if not selected_date_str:
        # default to TODAY in your timezone
        selected_date = timezone.localdate()
    else:
        try:
            selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.localdate()

    repayments = Repayment.objects.filter(
        collection_date=selected_date
    ).select_related('loan')

    return render(request, 'loans/view_repayments.html', {
        'payments': repayments,
        'selected_date': selected_date.isoformat(),  # YYYY-MM-DD for input
    })
    
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from transactions.models import Repayment

def _receipt_context(repayment):
    loan = repayment.loan

    # --- Identity ---
    verify_code = getattr(repayment, 'verify_code', '') or f"RCT-{repayment.pk:03d}"
    # Template uses repayment.collected_at, your model may call it collection_date
    # -> alias it so template never shows blank
    collected_at = getattr(repayment, 'collected_at', None) or getattr(repayment, 'collection_date', None)
    repayment.collected_at = collected_at  # makes {{ repayment.collected_at }} work

    client = getattr(loan, 'client', None)
    client_name = getattr(client, 'full_name', '') or str(client) if client else '-'

    loan_id = loan.pk
    # Try common field names for loan dates - first one that exists wins
    loan_date = (
        getattr(loan, 'disbursement_date', None)
        or getattr(loan, 'date_issued', None)
        or getattr(loan, 'start_date', None)
        or getattr(loan, 'created_at', None)
    )
    end_date = (
        getattr(loan, 'due_date', None)
        or getattr(loan, 'end_date', None)
        or getattr(loan, 'maturity_date', None)
        or getattr(loan, 'expected_end_date', None)
    )

    # --- Money ---
    # Template calls it total_payable (= Loan Amount)
    total_payable = (
        getattr(loan, 'total_payable', None)
        or getattr(loan, 'amount', None)
        or getattr(loan, 'principal', None)
        or getattr(loan, 'loan_amount', None)
        or 0
    )
    total_paid = Repayment.objects.filter(loan=loan).aggregate(
        total=Sum('amount_paid')
    )['total'] or 0
    balance = total_payable - total_paid

    # --- QR ---
    # If your model has verify_url use it, otherwise build verify link
    qr_data = (
        getattr(repayment, 'verify_url', '')
        or f"https://www.loanarchive.com/verify/?code={verify_code}"
    )

    return {
        'repayment': repayment,
        'r': repayment,
        'loan': loan,
        'receipt_no': verify_code,
        'verify_code': verify_code,
        'client_name': client_name,
        'loan_id': loan_id,
        'loan_date': loan_date,
        'end_date': end_date,
        'total_payable': total_payable,
        'total_paid': total_paid,
        'balance': balance,
        'qr_data': qr_data,
    }

@login_required
def receipt_detail(request, pk):
    repayment = get_object_or_404(Repayment, pk=pk)
    context = _receipt_context(repayment)
    return render(request, 'transactions/receipt_detail.html', context)

@login_required
def bulk_receipts(request):
    ids_raw = request.GET.get('ids', '')
    try:
        ids = [int(x.strip()) for x in ids_raw.split(',') if x.strip()]
    except ValueError:
        ids = []

    repayments = Repayment.objects.filter(pk__in=ids).order_by('book_number')
    receipts = [_receipt_context(rep) for rep in repayments]

    return render(request, 'transactions/bulk_receipts.html', {
        'receipts': receipts,
        'repayments': repayments,
    })

@login_required
def receipt_list(request):
    # Needed because your template does {% url 'receipt_list' %} for Back button
    repayments = Repayment.objects.select_related('loan', 'loan__client').order_by('-pk')[:100]
    return render(request, 'transactions/receipt_list.html', {
        'repayments': repayments,
    })