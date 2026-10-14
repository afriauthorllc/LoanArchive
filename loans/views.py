from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from . models import Loan



@login_required
def loan_list(request):
    status = request.GET.get('status', '')
    q = request.GET.get('q', '')

    loans = Loan.objects.select_related('client', 'branch', 'created_by_officer').order_by('-applied_at')
    
    if status in ['PENDING','APPROVED','DISBURSED','FULLY_PAID','REJECTED','DEFAULTED']:
        loans = loans.filter(status=status)
    
    if q:
        loans = loans.filter(client__first_name__icontains=q) | loans.filter(client__last_name__icontains=q) | loans.filter(client__nin__icontains=q)

    if hasattr(request.user, 'role') and request.user.role == 'FIELD_OFFICER':
        loans = loans.filter(created_by_officer=request.user)

    # For dashboard recent widget
    recent = loans[:10] if not status and not q else loans

    return render(request, 'loans/loan_list.html', {
        'loans': recent,
        'status_filter': status,
        'search_q': q,
        'all_count': Loan.objects.count(),
    })

@login_required
def loan_detail(request, pk):
    loan = get_object_or_404(Loan.objects.select_related('client','branch','created_by_officer','reviewed_by'), pk=pk)
    repayments = loan.repayments.select_related('collected_by').order_by('-collected_at')
    return render(request, 'loans/loan_detail.html', {
        'loan': loan,
        'client': loan.client,
        'repayments': repayments,
        'total_paid': loan.total_repayments_made,
        'balance': loan.outstanding_balance,
        'total_due': loan.total_payable,
        'progress': int((loan.total_repayments_made / loan.total_payable * 100)) if loan.total_payable > 0 else 0,
    })       
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import LoanApplicationForm

@login_required
def create_loan(request):
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST, user=request.user)
        if form.is_valid():
            loan = form.save(commit=False)
            # Bypass the FIELD_OFFICER limit - allow SUPERUSER/MANAGER to create too
            loan.created_by_officer = request.user
            loan.status = 'PENDING'
            loan.save()
            return redirect('dashboard:home')
    else:
        form = LoanApplicationForm(user=request.user)
    
    return render(request, 'loans/create.html', {'form': form})   
        
@login_required
def loan_detail(request, pk):
    loan = get_object_or_404(
        Loan.objects.select_related('client', 'branch', 'created_by_officer', 'reviewed_by'),
        pk=pk
    )
    repayments = loan.repayments.select_related('collected_by').order_by('-collected_at')
    
    total_paid = loan.total_repayments_made
    balance = loan.outstanding_balance
    total_due = loan.total_payable
    
    progress = 0
    if total_due > 0:
        progress = int((total_paid / total_due) * 100)
        if progress > 100:
            progress = 100

    # Action: Approve / Disburse
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve' and loan.status == 'PENDING':
            loan.status = 'APPROVED'
            loan.reviewed_by = request.user
            loan.actioned_at = timezone.now()
            loan.save()
            return redirect('loans:detail', pk=loan.pk)
        elif action == 'disburse' and loan.status == 'APPROVED':
            loan.status = 'DISBURSED'
            loan.disbursed_at = timezone.now()
            loan.save()
            return redirect('loans:detail', pk=loan.pk)

    context = {
        'loan': loan,
        'client': loan.client,
        'repayments': repayments,
        'total_paid': total_paid,
        'balance': balance,
        'total_due': total_due,
        'progress': progress,
    }
    return render(request, 'loans/loan_detail.html', context)        
    
    
    
    
from django.contrib import messages
from decimal import Decimal

# keep your existing loan_list and loan_detail above...

@login_required
def create_repayment(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    
    if loan.status not in ['DISBURSED', 'DEFAULTED']:
        messages.error(request, f"Cannot collect - loan is {loan.get_status_display()}")
        return redirect('loans:detail', pk=loan.pk)

    if request.method == 'POST':
        try:
            # Import inside to avoid circular import - Repayment is in same app
            from .models import Repayment
            
            amount = Decimal(request.POST.get('amount_paid', '0'))
            mode = request.POST.get('payment_mode', 'CASH')
            ref = request.POST.get('transaction_reference', '').strip()

            repayment = Repayment(
                loan=loan,
                amount_paid=amount,
                payment_mode=mode,
                transaction_reference=ref,
                collected_by=request.user
            )
            repayment.save()  # runs your clean() + FULLY_PAID auto logic
            
            messages.success(request, f"UGX {amount:,.0f} collected. Balance now UGX {loan.outstanding_balance:,.0f}")
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return redirect('loans:detail', pk=loan.pk)    