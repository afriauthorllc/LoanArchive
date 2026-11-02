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
from users.models import Branch
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages


def get_user_branch(user):
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
    if user.groups.filter(name__in=['Company Owner', 'Owner', 'Admin']).exists():
        return True
    if hasattr(user, 'profile') and getattr(user.profile, 'role', '') in ['owner', 'company_owner', 'admin']:
        return True
    return False

@login_required
def staff_dashboard(request):
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
        'all_clients': all_clients_qs,
    }
    return render(request, 'dashboard.html', context)

@login_required
def client_list(request):
    q = request.GET.get('q', '').strip()
    clients = Client.objects.select_related('branch', 'assigned_field_officer').all()
    if q:
        # SAFE: searches both new full_name AND old fields
        clients = clients.filter(
            Q(full_name__icontains=q) | 
            Q(first_name__icontains=q) | 
            Q(last_name__icontains=q) | 
            Q(nin__icontains=q) |
            Q(telephone_number__icontains=q)
        )
    return render(request, 'clients/client_list.html', {'clients': clients, 'q': q})

@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    return render(request, 'clients/client_detail.html', {'client': client})

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
    
@login_required
def client_search_api(request):
    q = request.GET.get('q','').strip()
    clients = Client.objects.all()
    
    if q:
        clients = clients.filter(
            Q(full_name__icontains=q) | 
            Q(nin__icontains=q) | 
            Q(telephone_number__icontains=q)
        )
    
    clients = clients.order_by('full_name')[:50]
    
    data = []
    for c in clients:
        data.append({
            "id": c.id,
            "name": c.full_name,
            "code": c.nin or f"C-{c.id}",
            "phone": c.telephone_number or ""
        })
    return JsonResponse(data, safe=False)
    
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
                return render(request, 'clients/add_client.html', {
                    'branches': branches,
                    'can_choose_branch': can_choose_branch,
                    'user_branch': user_branch
                })
            branch = Branch.objects.filter(id=branch_id).first()
            if not branch:
                messages.error(request, "Invalid branch selected")
                return render(request, 'clients/add_client.html', {
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
                return redirect('clients:add_new_client')

        try:
            client = Client(
                full_name=request.POST.get('full_name','').strip(),
                telephone_number=request.POST.get('telephone_number'),
                nin=request.POST.get('nin','').strip(),
                district=request.POST.get('district'),
                parish=request.POST.get('parish'),
                village=request.POST.get('village'),
                landmark=request.POST.get('landmark'),
                sub_county=request.POST.get('sub_county'),
                branch=branch,
                assigned_field_officer=request.user
            )
            # handle passport photo
            if request.FILES.get('passport_photo'):
                client.passport_photo = request.FILES.get('passport_photo')
                
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