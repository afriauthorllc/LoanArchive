#transactions/views.py
from django.shortcuts import render, get_object_or_404, redirect
from .services.executions import create_repayment, edit_repayment
from django.utils import timezone
from loans.models import Loan
from .models import Repayment
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse

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
    # Get date from ?date=2026-10-27 or default to today
    selected_date = request.GET.get('date')
    if not selected_date:
        selected_date = timezone.now().date().isoformat()
    
    repayments = Repayment.objects.filter(collection_date=selected_date).select_related('loan')
    
    return render(request, 'loans/view_repayments.html', {
        'payments': repayments,
        'selected_date': selected_date
    })
    