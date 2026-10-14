from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from loans.models import Loan
from .models import Client
from .forms import ClientEntryForm
from django.shortcuts import render, get_object_or_404, redirect

@login_required
def staff_dashboard(request):
    """
    Renders system analytics metrics and loops active profile entries.
    """
    # Fetch core database analytics numbers based on the user's branch
    user_branch = request.user.branch
    
    # Base filter querysets to keep branch boundaries safe
    loan_qs = Loan.objects.filter(branch=user_branch) if user_branch else Loan.objects.all()
    client_qs = Client.objects.filter(branch=user_branch) if user_branch else Client.objects.all()

    # Calculate real KPI metrics dynamically
    active_loans_count = loan_qs.filter(status='DISBURSED').count()
    pending_approvals_count = loan_qs.filter(status='PENDING').count()
    at_risk_count = loan_qs.filter(status='DEFAULTED').count()
    
    # Sum collections due today
    today_date = timezone.now().date()
    collections_today = loan_qs.filter(
        schedules__due_date=today_date, 
        schedules__status__in=['UNPAID', 'PARTIAL']
    ).aggregate(total=Sum('schedules__total_due'))['total'] or Decimal('0.00')

    # Pull the 5 most recent records to populate the front-end layout grid
    recent_loans = loan_qs.select_related('client', 'created_by_officer')[:5]

    context = {
        'active_loans': active_loans_count,
        'pending_approvals': pending_approvals_count,
        'at_risk_loans': at_risk_count,
        'collections_due': collections_today,
        'recent_loans': recent_loans,
    }
    return render(request, 'dashboard.html', context)


@login_required
def add_new_client(request):
    """
    Processes file submissions and signs off client assignments to the logged-in field officer.
    """
    if request.method == 'POST':
        # File parsing arrays MUST take request.FILES for passport image parsing
        form = ClientEntryForm(request.POST, request.FILES)
        if form.is_valid():
            client = form.save(commit=False)
            
            # Automatically lock the client down to the current officer's organizational zone
            client.branch = request.user.branch
            if request.user.role == 'FIELD_OFFICER':
                client.assigned_field_officer = request.user
                
            client.save()
            messages.success(request, f"Client profile for {client.full_name} created successfully.")
            return redirect('staff_dashboard')
        else:
            messages.error(request, "Failed to register client. Please fix the highlighted errors below.")
    else:
        form = ClientEntryForm()

    return render(request, 'clients/add_client.html', {'form': form})
        
        
@login_required
def client_list(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    clients = Client.objects.select_related('branch', 'assigned_field_officer').all()
    
    if q:
        clients = clients.filter(first_name__icontains=q) | clients.filter(last_name__icontains=q) | clients.filter(nin__icontains=q)
    if status:
        # if you add status field later, filter here
        pass
        
    return render(request, 'clients/client_list.html', {'clients': clients})       
        
@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    return render(request, 'clients/client_detail.html', {'client': client})        
