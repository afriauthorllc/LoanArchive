# transactions/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
import datetime

from loans.models import Loan
from .models import Repayment
from .services.executions import create_repayment, edit_repayment

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
    book_no = (request.GET.get('book_number', '') or request.GET.get('book', '')).strip()
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

@login_required
def repayment_live_filter(request):
    q = request.GET.get('q', '').strip()
    repayments = Repayment.objects.select_related('loan__client').order_by('-collected_at')[:200]
    if q:
        repayments = repayments.filter(
            Q(book_number__icontains=q)
            | Q(loan__client__first_name__icontains=q)
            | Q(loan__client__last_name__icontains=q)
        )
    return render(request, 'loans/live_filter.html', {'repayments': repayments, 'q': q})

@login_required
def view_repayments(request):
    selected_date_str = request.GET.get('date', '').strip()

    if not selected_date_str:
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

# --- RECEIPTS / VERIFY / SCANNER ---
def _receipt_context(repayment, request=None):
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
    # Your Loan model uses disbursed_at / applied_at (see repayments_view)
    loan_date = (
        getattr(loan, 'disbursed_at', None)
        or getattr(loan, 'disbursement_date', None)
        or getattr(loan, 'applied_at', None)
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
    # YOUR REAL FIELD: principal_amount (loans/models.py line 51)
    # e.g. Peter Okello: principal_amount = 80,000
    # Total Paid 38,000 + Balance 42,000 = 80,000 ✓
    total_payable = (
        getattr(loan, 'principal_amount', None)
        or getattr(loan, 'total_payable', None)
        or getattr(loan, 'total_due', None)
        or getattr(loan, 'total_repayable', None)
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
    # Must point to the real public receipt URL: /transactions/receipt/RCT-002/
    # NOT /verify/?code=...
    if request is not None:
        try:
            qr_data = request.build_absolute_uri(
                reverse('transactions:receipt', kwargs={'verify_code': verify_code})
            )
        except NoReverseMatch:
            try:
                qr_data = request.build_absolute_uri(
                    reverse('receipt', kwargs={'verify_code': verify_code})
                )
            except NoReverseMatch:
                qr_data = getattr(repayment, 'verify_url', '') or f"https://www.loanarchive.com/transactions/receipt/{verify_code}/"
    else:
        qr_data = getattr(repayment, 'verify_url', '') or f"https://www.loanarchive.com/transactions/receipt/{verify_code}/"

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
    context = _receipt_context(repayment, request)
    return render(request, 'transactions/receipt_detail.html', context)

def receipt(request, verify_code):
    """Public receipt page opened from QR code: /transactions/receipt/RCT-002/"""
    code = (verify_code or '').strip()
    repayment = Repayment.objects.filter(verify_code=code).first()
    if not repayment:
        repayment = Repayment.objects.filter(verify_code__iexact=code).first()
    if not repayment:
        # Fallback: RCT-006 -> pk 6, or plain number
        try:
            pk = int(code.replace('RCT-', '').split('-')[0])
            repayment = Repayment.objects.filter(pk=pk).first()
        except (ValueError, IndexError):
            repayment = None

    if not repayment:
        return render(request, 'transactions/verify.html', {
            'code': code,
            'repayment': None,
            'searched': True,
            'error': f"No receipt found for {code}",
        }, status=404)

    context = _receipt_context(repayment, request)
    return render(request, 'transactions/receipt_detail.html', context)

@login_required
def bulk_receipts(request):
    ids_raw = request.GET.get('ids', '')
    try:
        ids = [int(x.strip()) for x in ids_raw.split(',') if x.strip()]
    except ValueError:
        ids = []

    repayments = Repayment.objects.filter(pk__in=ids).order_by('book_number')
    receipts = [_receipt_context(rep, request) for rep in repayments]

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

@login_required
def scanner(request):
    # Try namespaced name first, then plain
    verify_url = '/verify/'
    for name in ('transactions:verify', 'verify', 'transactions:verify_receipt', 'verify_receipt'):
        try:
            verify_url = reverse(name)
            break
        except NoReverseMatch:
            continue
    return render(request, 'transactions/scanner.html', {
        'verify_url': verify_url,
    })

@login_required
def verify(request):
    code = request.GET.get('code', '').strip()
    repayment = None
    if code:
        repayment = Repayment.objects.filter(verify_code=code).first()
        if not repayment:
            repayment = Repayment.objects.filter(verify_code__iexact=code).first()

    context = {'code': code, 'repayment': repayment, 'searched': bool(code)}
    if repayment:
        context.update(_receipt_context(repayment, request))
        context['repayment'] = repayment
        context['code'] = code
    return render(request, 'transactions/verify.html', context)
    