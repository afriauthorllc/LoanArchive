# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from loans.models import Loan, Repayment

@login_required
def home(request):
    user = request.user
    today = timezone.now().date()

    # Filter by branch if user is not superuser (Loan Archive Mobile Staff logic)
    base_loans = Loan.objects.all()
    if hasattr(user, 'branch') and user.branch and user.role != 'SUPERUSER':
        base_loans = base_loans.filter(branch=user.branch)

    # Cards from your screenshot
    active_loans_count = base_loans.filter(status=Loan.Status.DISBURSED).count()
    pending_approvals_count = base_loans.filter(status=Loan.Status.PENDING).count()
    at_risk_count = base_loans.filter(status=Loan.Status.DEFAULTED).count()

    # Today's collections - sum of all repayments collected today
    todays_collections = Repayment.objects.filter(
        collected_at__date=today
    )
    if hasattr(user, 'branch') and user.branch and user.role != 'SUPERUSER':
        todays_collections = todays_collections.filter(loan__branch=user.branch)
    
    todays_total = todays_collections.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')

    # Recent Loan Applications & Approvals - last 10
    recent_loans = base_loans.select_related('client').order_by('-applied_at')[:10]

    context = {
        'active_loans': active_loans_count,
        'pending_approvals': pending_approvals_count,
        'at_risk_loans': at_risk_count,
        'todays_collections_total': todays_total,
        'todays_collections_count': todays_collections.count(),
        'recent_loans': recent_loans,
    }
    return render(request, 'dashboard/home.html', context)
    
def reports(request):
    return render(request, 'dashboard/reports.html')    