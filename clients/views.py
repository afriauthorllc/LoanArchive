from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from decimal import Decimal
from django.utils import timezone
from django.http import JsonResponse
from loans.models import Loan
from .models import Client
from .forms import ClientEntryForm

@login_required
def staff_dashboard(request):
    from django.db.models import Sum
    from decimal import Decimal
    from django.utils import timezone

    # FORCE all clients, no branch filter at all for debug
    all_clients_qs = Client.objects.all().order_by('id')[:200]
    
    print(f"DEBUG: Client.objects.count() = {Client.objects.count()}")
    print(f"DEBUG: all_clients_qs count = {all_clients_qs.count()}")
    print(f"DEBUG: user={request.user} super={request.user.is_superuser} branch={getattr(request.user,'branch', None)}")

    user_branch = getattr(request.user, 'branch', None)
    is_super = request.user.is_superuser

    if is_super or not user_branch:
        loan_qs = Loan.objects.all()
    else:
        loan_qs = Loan.objects.filter(branch=user_branch)

    active_loans_count = loan_qs.filter(status='DISBURSED').count()
    pending_approvals_count = loan_qs.filter(status='PENDING').count()
    at_risk_count = loan_qs.filter(status='DEFAULTED').count()
    
    today_date = timezone.now().date()
    collections_today = loan_qs.filter(
        schedules__due_date=today_date, 
        schedules__status__in=['UNPAID','PARTIAL']
    ).aggregate(total=Sum('schedules__total_due'))['total'] or Decimal('0.00')

    recent_loans = loan_qs.select_related('client','created_by_officer').order_by('-created_at')[:10]

    context = {
        'active_loans_count': active_loans_count,
        'pending_count': pending_approvals_count,
        'at_risk_count': at_risk_count,
        'todays_due': collections_today,
        'recent_loans': recent_loans,
        'all_clients': all_clients_qs,  # this is what the FAB uses
    }
    return render(request, 'dashboard.html', context)
    

@login_required
def client_list(request):
    q = request.GET.get('q', '')
    clients = Client.objects.select_related('branch', 'assigned_field_officer').all()
    if q:
        clients = clients.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(nin__icontains=q)
        )
    return render(request, 'clients/client_list.html', {'clients': clients})

@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    return render(request, 'clients/client_detail.html', {'client': client})

@login_required
def add_loan_for_client(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    if request.method == 'POST':
        try:
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
        except Exception as e:
            print("Loan create error:", e)
    return redirect('clients:detail', pk=client_id)

@login_required
def client_search_api(request):
    q = request.GET.get('q','').strip()
    clients = Client.objects.all()
    
    if q:
        clients = clients.filter(
            Q(first_name__icontains=q) | 
            Q(last_name__icontains=q) | 
            Q(nin__icontains=q) | 
            Q(telephone_number__icontains=q)
        )
    
    clients = clients.order_by('first_name')[:50]
    
    data = []
    for c in clients:
        name = f"{c.first_name} {c.last_name}".strip()
        data.append({
            "id": c.id,
            "name": name,
            "code": c.nin or f"C-{c.id}",
            "phone": c.telephone_number or ""
        })
    return JsonResponse(data, safe=False)
    
    
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Client
from users.models import Branch  # <-- FIXED: Branch is in users, not branches

def get_user_branch(user):
    # where does your user store branch? Check all possibilities
    if hasattr(user, 'profile') and hasattr(user.profile, 'branch') and user.profile.branch:
        return user.profile.branch
    if hasattr(user, 'branch') and user.branch:
        return user.branch
    if hasattr(user, 'staff_profile') and hasattr(user.staff_profile, 'branch'):
        return user.staff_profile.branch
    return None

def is_branch_manager(user):
    if user.is_superuser:
        return True
    # adjust if your Company Owner role is stored differently
    if user.groups.filter(name__in=['Company Owner', 'Owner', 'Admin']).exists():
        return True
    if hasattr(user, 'profile') and getattr(user.profile, 'role', '') in ['owner', 'company_owner', 'admin']:
        return True
    return False

@login_required
def add_new_client(request):
    can_choose_branch = is_branch_manager(request.user)
    user_branch = get_user_branch(request.user)
    branches = Branch.objects.all() if can_choose_branch else []

    if request.method == 'POST':
        branch = None
        
        if can_choose_branch:
            branch_id = request.POST.get('branch')
            if not branch_id:
                messages.error(request, "Please select a branch")
                return render(request, 'clients/add.html', {
                    'branches': branches,
                    'can_choose_branch': can_choose_branch,
                    'user_branch': user_branch
                })
            branch = Branch.objects.filter(id=branch_id).first()
            if not branch:
                messages.error(request, "Invalid branch selected")
                return render(request, 'clients/add.html', {
                    'branches': branches,
                    'can_choose_branch': can_choose_branch,
                    'user_branch': user_branch
                })
        else:
            # Normal user: auto-assign their branch
            branch = user_branch
            if not branch:
                # last fallback - first branch in system
                branch = Branch.objects.first()
            if not branch:
                messages.error(request, "Your account has no branch. Contact admin to assign you a branch.")
                return redirect('clients:add')

        try:
            client = Client(
                first_name=request.POST.get('first_name','').strip(),
                last_name=request.POST.get('last_name','').strip(),
                telephone_number=request.POST.get('telephone_number'),
                nin=request.POST.get('nin'),
                district=request.POST.get('district'),
                parish=request.POST.get('parish'),
                village=request.POST.get('village'),
                landmark=request.POST.get('landmark'),
                sub_county=request.POST.get('sub_county'),
                branch=branch,  # <-- Now always set, no more IntegrityError
                assigned_field_officer=request.user
            )
            client.save()
            messages.success(request, f"Client {client.full_name} added to {branch.name}")
            return redirect('clients:list')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'clients/add_client.html', {
        'branches': branches,
        'can_choose_branch': can_choose_branch,
        'user_branch': user_branch
    })