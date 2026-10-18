from django.shortcuts import render
from django.utils import timezone
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
# --- SAFE LIVE FILTER - NO DB CHANGE ---
def repayment_live_filter(request):
    from django.db.models import Q
    from .models import Repayment
    q = request.GET.get('q','').strip()
    repayments = Repayment.objects.select_related('loan__client','branch').order_by('-payment_date')[:200]
    if q:
        repayments = Repayment.objects.select_related('loan__client','branch').filter(
            Q(book_number__icontains=q) |
            Q(loan__client__first_name__icontains=q) |
            Q(loan__client__last_name__icontains=q) |
            Q(loan__client__nin__icontains=q)
        ).order_by('-payment_date')[:200]
    return render(request, 'loans/live_filter.html', {'repayments': repayments, 'q': q})

def check_book_number_api(request):
    """AJAX check duplicate book_number - prevents duplicate without DB constraint"""
    from django.http import JsonResponse
    from .models import Repayment
    book = request.GET.get('book','')
    branch_id = request.GET.get('branch','')
    date = request.GET.get('date','')
    if not book:
        return JsonResponse({'exists': False})
    qs = Repayment.objects.filter(book_number__iexact=book)
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if date:
        qs = qs.filter(payment_date=date)
    exists = qs.exists()
    return JsonResponse({'exists': exists, 'count': qs.count()})

from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from clients.models import Client
from .models import Loan

@login_required
def create_loan_application(request):
    """Used by dashboard modal - creates PENDING loan for any client"""
    if request.method == 'POST':
        client_id = request.POST.get('client_id')
        client = get_object_or_404(Client, pk=client_id)
        Loan.objects.create(
            client=client,
            branch=client.branch,
            principal_amount=Decimal(request.POST.get('principal_amount')),
            interest_rate=Decimal(request.POST.get('interest_rate')),
            duration_months=int(request.POST.get('duration_months') or 6),
            collateral_details=request.POST.get('collateral_details'),
            status=Loan.Status.PENDING,
            created_by_officer=request.user
        )
        return redirect(request.POST.get('next') or '/')
    return redirect('/')

@login_required
def client_search_api(request):
    from django.http import JsonResponse
    from django.db.models import Q
    from clients.models import Client
    q = request.GET.get('q','').strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    clients = Client.objects.filter(
        Q(full_name__icontains=q) | 
        Q(nin__icontains=q) | 
        Q(telephone_number__icontains=q) |
        Q(client_code__icontains=q)
    )[:10]
    data = [{
        "id": c.id, 
        "name": c.full_name, 
        "code": c.client_code or c.nin[:8], 
        "phone": c.telephone_number,
        "branch": c.branch.name if c.branch else ""
    } for c in clients]
    return JsonResponse(data, safe=False)
    
    
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import IntegrityError
import json
from .models import Repayment, Loan

@login_required
def repayment_page(request):
    active_loans = Loan.objects.filter(status__in=['DISBURSED','DEFAULTED']).select_related('client')[:100]
    return render(request, 'loans/repayments.html', {'active_loans': active_loans})

def check_book_number(request):
    book_no = request.GET.get('book_number','').strip()
    if not book_no:
        return JsonResponse({'exists': False})
    try:
        rep = Repayment.objects.select_related('loan__client').get(book_number=book_no)
        return JsonResponse({'exists': True, 'client': rep.loan.client.full_name, 'book_number': book_no})
    except Repayment.DoesNotExist:
        return JsonResponse({'exists': False})

@login_required
@require_POST
def bulk_repayment_submit(request):
    try:
        data = json.loads(request.body)
        repayments = data.get('repayments', [])
        saved = 0
        errors = []
        for item in repayments:
            try:
                Repayment.objects.create(
                    book_number=item['book_number'].strip(),
                    loan_id=item['loan_id'],
                    amount_paid=item['amount_paid'],
                    payment_mode='CASH',
                    collected_by=request.user
                )
                saved += 1
            except IntegrityError:
                errors.append(f"Book #{item['book_number']} already exists")
            except Exception as e:
                errors.append(str(e))
        
        if errors and saved==0:
            return JsonResponse({'success': False, 'error': '; '.join(errors)})
        return JsonResponse({'success': True, 'saved': saved, 'errors': errors})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})    