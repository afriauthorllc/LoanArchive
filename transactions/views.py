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
    
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from .models import Repayment

def _loan_end_date(loan):
    # End Date = disbursed_at + duration_months
    if loan.disbursed_at and loan.duration_months:
        return loan.disbursed_at + relativedelta(months=loan.duration_months)
    return None

def _receipt_context(repayment):
    loan = repayment.loan
    client = loan.client  # clients.Client - has full_name, nin, telephone_number, village, parish, sub_county, district
    base = getattr(settings, 'SITE_URL', 'https://loanarchive.com')

    # Build address from real fields: Village, Parish, Sub-County, District
    address_parts = [client.village, client.parish, client.sub_county, client.district]
    address = ", ".join([p for p in address_parts if p])

    return {
        'repayment': repayment,
        'payment': repayment,
        'loan': loan,
        'client': client,
        'branch': repayment.branch,

        # Client - exact fields
        'client_name': client.full_name,
        'client_nin': client.nin,
        'client_phone': client.telephone_number,
        'client_address': address,
        'client_village': client.village,
        'client_district': client.district,

        # Loan - exact fields
        'loan_id': f"Loan #{loan.id}",
        'loan_date': loan.disbursed_at,
        'end_date': _loan_end_date(loan),
        'principal_amount': loan.principal_amount,
        'interest_rate': loan.interest_rate,
        'duration_months': loan.duration_months,
        'loan_status': loan.get_status_display(),

        # Money - exact properties on Loan
        'total_payable': loan.total_payable,
        'total_paid': loan.total_repayments_made,
        'balance': loan.outstanding_balance,

        # Receipt / QR
        'receipt_no': f"Book #{repayment.book_number}",
        'verify_code': repayment.verify_code,
        'qr_data': f"{base}/verify/?code={repayment.verify_code}",
    }

@login_required
def scanner(request):
    return render(request, 'scanner.html')

def verify(request):
    code = request.GET.get('code', '').strip().upper()
    if not code:
        return render(request, 'verify.html', {'status': 'empty'})

    repayment = Repayment.objects.select_related('loan__client', 'loan__branch', 'branch', 'collected_by').filter(verify_code=code).first()

    if not repayment and code.isdigit():
        repayment = Repayment.objects.select_related('loan__client', 'loan__branch', 'branch', 'collected_by').filter(
            book_number=int(code), collection_date=timezone.now().date()
        ).first()

    if not repayment:
        return render(request, 'verify.html', {'status': 'invalid', 'code': code})

    if repayment.is_voided:
        return render(request, 'verify.html', {
            'status': 'voided', 'code': code, **_receipt_context(repayment),
        })

    return render(request, 'verify.html', {
        'status': 'verified', 'code': code, **_receipt_context(repayment),
    })

@login_required
def receipt_list(request):
    repayments = Repayment.objects.select_related('loan__client', 'branch', 'collected_by').order_by('-collected_at')[:50]
    return render(request, 'receipt_list.html', {'repayments': repayments, 'payments': repayments})

@login_required
def receipt(request, verify_code):
    repayment = get_object_or_404(
        Repayment.objects.select_related('loan__client', 'loan__branch', 'branch', 'collected_by'),
        verify_code=verify_code.upper()
    )
    return render(request, 'receipt.html', _receipt_context(repayment))

@login_required
def void_repayment(request, verify_code):
    repayment = get_object_or_404(Repayment, verify_code=verify_code.upper())
    repayment.is_voided = True
    repayment.save(update_fields=['is_voided'])
    messages.warning(request, f"Book #{repayment.book_number} voided. Scanning it will now show INVALID.")
    return redirect('receipt_list')
    
@login_required
def bulk_print_receipts(request):
    """
    Print the latest bulk.
    Usage:
      /receipts/bulk/?ids=12,13,14   <- from bulk payment form (best)
      /receipts/bulk/                <- fallback: today's payments, latest batch
    """
    ids_param = request.GET.get('ids', '').strip()

    if ids_param:
        # Exact bulk that was just created - e.g. ids=12,13,14
        ids = [int(x) for x in ids_param.split(',') if x.strip().isdigit()]
        repayments = Repayment.objects.select_related(
            'loan__client', 'loan__branch', 'branch', 'collected_by'
        ).filter(id__in=ids).order_by('collected_at')
    else:
        # Fallback: latest bulk = payments collected today, newest first
        # If you do bulk payments once per session, this = that bulk
        repayments = Repayment.objects.select_related(
            'loan__client', 'loan__branch', 'branch', 'collected_by'
        ).filter(collection_date=timezone.now().date()).order_by('collected_at')

    # Build the same context as single receipt, for each one
    receipt_list = [_receipt_context(r) for r in repayments]

    return render(request, 'bulk_receipts.html', {
        'receipts': receipt_list,
        'repayments': repayments,
        'count': len(receipt_list),  # <-- this drives the button
    })
    