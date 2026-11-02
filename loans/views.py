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
from django.db.models import Sum
from django.utils import timezone

from .models import Loan
from transactions.models import Repayment
from .forms import LoanApplicationForm
from clients.models import Client

from .services.application import create_loan_application

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
        try:
            loan = create_loan_application(
                client_id=request.POST.get('client_id'),
                user=request.user,
                data=request.POST
            )
            messages.success(request, f'Loan for {loan.client.full_name} created')
            return redirect('loan_list')
        except Exception as e:
            messages.error(request, str(e))
            # re-render with data so user doesn't lose input
            form = LoanApplicationForm(request.POST, user=request.user, company=company)
            form.fields['product'].queryset = LoanProduct.objects.filter(company=company, is_active=True)
            return render(request, 'loans/create.html', {'form': form, 'company': company})

    # GET - your old LoanForm logic
    form = LoanApplicationForm(user=request.user, company=company)
    form.fields['product'].queryset = LoanProduct.objects.filter(company=company, is_active=True)
    
    return render(request, 'loans/create.html', {
        'form': form, 
        'company': company,
        'title': 'New Loan Application'
    })
    
    
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
def reports_page(request):
    today = timezone.now().date()
    total_disbursed = Loan.objects.filter(status='DISBURSED').aggregate(s=Sum('principal_amount'))['s'] or 0
    # add other aggregates as you need
    return render(request, 'loans/reports.html', {
        'total_disbursed': total_disbursed,
        'active_loans': Loan.objects.filter(status='DISBURSED').count(),
    }) 
    
    
@login_required
def add_loan_for_client(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                principal = Decimal(request.POST.get('principal_amount') or 0)
                interest = Decimal(request.POST.get('interest_rate') or 0)
                duration = int(request.POST.get('duration_months') or 6)
                collateral = request.POST.get('collateral_details', '').strip()

                # Guarantor - exact names from your form
                g_name = request.POST.get('guarantor_name', '').strip()
                g_nin = request.POST.get('guarantor_nin', '').strip().upper()
                g_tel = request.POST.get('guarantor_telephone', '').strip()
                g_rel = request.POST.get('guarantor_relationship', '').strip()

                # Basic validation
                if not g_name or not g_nin or not g_tel or not g_rel:
                    messages.error(request, "All guarantor fields are required.")
                    return redirect('clients:detail', pk=client_id)

                loan = Loan.objects.create(
                    client=client,
                    branch=client.branch,
                    principal_amount=principal,
                    interest_rate=interest,
                    duration_months=duration,
                    collateral_details=collateral,
                    # Guarantor fields on Loan
                    guarantor_name=g_name,
                    guarantor_nin=g_nin,
                    guarantor_telephone=g_tel,
                    guarantor_relationship=g_rel,
                    status=Loan.Status.PENDING,
                    created_by_officer=request.user
                )

                # If you have separate Guarantor model instead, replace above 4 guarantor fields with:
                # Guarantor.objects.create(
                #     loan=loan,
                #     full_name=g_name,
                #     nin=g_nin,
                #     telephone=g_tel,
                #     relationship=g_rel
                # )

                messages.success(request, f"Loan created for {client.full_name} with guarantor {g_name}")

        except (InvalidOperation, ValueError) as e:
            messages.error(request, f"Invalid number: {e}")
        except Exception as e:
            messages.error(request, f"Failed to create loan: {e}")
            print("Loan create error:", e)

    return redirect('dashboard:home')
   
   
   