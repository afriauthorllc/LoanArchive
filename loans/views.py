# loans/views.py - FINAL WORKING - DO NOT DELETE PARTS
from decimal import Decimal
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.db import IntegrityError

from .models import Loan, Repayment
from .forms import LoanApplicationForm
from clients.models import Client

def loan_list(request):
    status = request.GET.get('status', '')
    q = request.GET.get('q', '')
    loans = Loan.objects.select_related('client', 'branch', 'created_by_officer').order_by('-applied_at')
    if status:
        loans = loans.filter(status=status)
    if q:
        loans = loans.filter(Q(client__first_name__icontains=q) | Q(client__last_name__icontains=q) | Q(client__nin__icontains=q))
    if hasattr(request.user, 'role') and request.user.role == 'FIELD_OFFICER':
        loans = loans.filter(created_by_officer=request.user)
    return render(request, 'loans/loan_list.html', {'loans': loans[:100], 'status_filter': status, 'search_q': q})

@login_required
def loan_detail(request, pk):
    loan = get_object_or_404(Loan.objects.select_related('client','branch','created_by_officer','reviewed_by'), pk=pk)
    repayments = loan.repayments.select_related('collected_by').order_by('-collected_at')
    total_paid = loan.total_repayments_made
    balance = loan.outstanding_balance
    total_due = loan.total_payable
    progress = int((total_paid / total_due * 100)) if total_due > 0 else 0
    if progress > 100:
        progress = 100
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve' and loan.status == 'PENDING':
            loan.status = 'APPROVED'; loan.reviewed_by = request.user; loan.actioned_at = timezone.now(); loan.save()
            return redirect('loans:detail', pk=loan.pk)
        elif action == 'disburse' and loan.status == 'APPROVED':
            loan.status = 'DISBURSED'; loan.disbursed_at = timezone.now(); loan.save()
            return redirect('loans:detail', pk=loan.pk)
    return render(request, 'loans/loan_detail.html', {'loan': loan, 'client': loan.client, 'repayments': repayments, 'total_paid': total_paid, 'balance': balance, 'total_due': total_due, 'progress': progress})

@login_required
def create_loan(request):
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST, user=request.user)
        if form.is_valid():
            loan = form.save(commit=False); loan.created_by_officer = request.user; loan.status = 'PENDING'; loan.save()
            return redirect('dashboard:home')
    else:
        form = LoanApplicationForm(user=request.user)
    return render(request, 'loans/create.html', {'form': form})

@login_required
def create_loan_application(request):
    if request.method == 'POST':
        client = get_object_or_404(Client, pk=request.POST.get('client_id'))
        Loan.objects.create(client=client, branch=client.branch, principal_amount=Decimal(request.POST.get('principal_amount')), interest_rate=Decimal(request.POST.get('interest_rate')), duration_months=int(request.POST.get('duration_months') or 6), collateral_details=request.POST.get('collateral_details'), status=Loan.Status.PENDING, created_by_officer=request.user)
        return redirect(request.POST.get('next') or '/')
    return redirect('/')

@login_required
def client_search_api(request):
    q = request.GET.get('q','').strip()
    if len(q) < 1:
        return JsonResponse([], safe=False)
    clients = Client.objects.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(nin__icontains=q) | Q(telephone_number__icontains=q))[:20]
    data = []
    for c in clients:
        try:
            name = c.full_name
        except:
            name = f"{c.first_name} {c.last_name}"
        data.append({"id": c.id, "name": name, "code": c.nin or f"C-{c.id}", "phone": c.telephone_number or "", "branch": c.branch.name if c.branch else ""})
    return JsonResponse(data, safe=False)

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
def loan_search_api(request):
    q = request.GET.get('q','').strip()
    loans = Loan.objects.select_related('client').all().order_by('-id')[:100]
    if q:
        loans = loans.filter(Q(client__first_name__icontains=q) | Q(client__last_name__icontains=q))
    data = []
    for loan in loans:
        try:
            name = loan.client.full_name
        except:
            name = f"{loan.client.first_name} {loan.client.last_name}" if loan.client else f"Client {loan.client_id}"
        data.append({"id": loan.id, "loan_id": f"LN-{loan.id:04d}", "client_name": name, "status": loan.status, "principal": float(loan.principal_amount), "date": loan.disbursed_at.strftime("%d %b %Y") if loan.disbursed_at else loan.applied_at.strftime("%d %b %Y")})
    return JsonResponse(data, safe=False)

@login_required
def check_book_number(request):
    book_no = request.GET.get('book_number','') or request.GET.get('book','')
    book_no = book_no.strip()
    if not book_no:
        return JsonResponse({'exists': False})
    exists = Repayment.objects.filter(book_number=book_no).exists()
    return JsonResponse({'exists': exists})

def check_book_number_api(request):
    return check_book_number(request)

@login_required
@require_POST
def bulk_repayment_submit(request):
    try:
        payload = json.loads(request.body)
        repayments = payload.get('repayments', [])
        saved = 0; errors = []
        for item in repayments:
            try:
                Repayment.objects.create(book_number=str(item.get('book_number','')).strip(), loan_id=item.get('loan_id'), amount_paid=Decimal(str(item.get('amount') or item.get('amount_paid'))), payment_mode='CASH', collected_by=request.user)
                saved += 1
            except Exception as e:
                errors.append(str(e))
        return JsonResponse({'success': True, 'saved': saved, 'errors': errors})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def create_repayment(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    if request.method == 'POST':
        try:
            Repayment.objects.create(book_number=request.POST.get('book_number','').strip() or f"TEMP-{loan_id}", loan=loan, amount_paid=Decimal(request.POST.get('amount_paid','0')), payment_mode=request.POST.get('payment_mode','CASH'), collected_by=request.user)
            messages.success(request, 'Collected')
        except Exception as e:
            messages.error(request, str(e))
    return redirect('loans:detail', pk=loan.pk)

def repayment_live_filter(request):
    q = request.GET.get('q','').strip()
    repayments = Repayment.objects.select_related('loan__client').order_by('-collected_at')[:200]
    if q:
        repayments = repayments.filter(Q(book_number__icontains=q) | Q(loan__client__first_name__icontains=q) | Q(loan__client__last_name__icontains=q))
    return render(request, 'loans/live_filter.html', {'repayments': repayments, 'q': q})

@login_required
def repayment_page(request):
    return redirect('loans:repayments')