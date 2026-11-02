from clients.models import Client
from loans.models import Loan
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from decimal import Decimal

@login_required
def create_loan_application(request):
    if request.method == 'POST':
        client = get_object_or_404(Client, pk=request.POST.get('client_id'))
        Loan.objects.create(
            client=client, 
            branch=client.branch, 
            principal_amount=Decimal(request.POST.get('principal_amount')), 
            interest_rate=Decimal(request.POST.get('interest_rate')), 
            duration_months=int(request.POST.get('duration_months') or 6), 
            collateral_details=request.POST.get('collateral_details'),
            # 👥 Guarantor fields
            guarantor_name=request.POST.get('guarantor_name','').strip(),
            guarantor_nin=request.POST.get('guarantor_nin','').upper().strip(),
            guarantor_telephone=request.POST.get('guarantor_telephone','').strip(),
            guarantor_relationship=request.POST.get('guarantor_relationship'),
            status=Loan.Status.PENDING, 
            created_by_officer=request.user
        )
        return redirect(request.POST.get('next') or '/')
    return redirect('/')
    
