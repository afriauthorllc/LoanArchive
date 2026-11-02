# billing/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Subscription

@login_required
def billing_page(request):
    # Get branch from logged in user
    branch = getattr(request.user, 'branch', None)
    if not branch:
        # If user model has branch_id or similar, adjust here
        branch = request.user.branch_set.first() if hasattr(request.user, 'branch_set') else None
    
    subscription = None
    payments = []
    if branch:
        subscription = getattr(branch, 'billing_subscription', None)
        payments = branch.billing_payments.all().order_by('-created_at')[:10]
    
    return render(request, 'billing.html', {
        'branch': branch,
        'subscription': subscription,
        'days_left': subscription.days_left if subscription else 0,
        'progress_percent': subscription.progress_percent if subscription else 0,
        'payments': payments,
    })

@login_required
def billing_pay(request):
    # For now just redirect - we will add MoMo logic later
    return redirect('billing')
    
    