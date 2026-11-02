# billing/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

class SubscriptionLockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow these URLs even if expired
        allowed_paths = [
            '/admin/',
            '/billing/',
            '/users/logout/',
            '/users/login/',
            '/static/',
            '/media/',
        ]
        
        # Don't lock superusers
        if request.user.is_authenticated and request.user.is_superuser:
            return self.get_response(request)
            
        # Check if path is allowed
        if any(request.path.startswith(p) for p in allowed_paths):
            return self.get_response(request)
            
        # Check subscription only for logged in users with branch
        if request.user.is_authenticated:
            try:
                branch = None
                if hasattr(request.user, 'branch') and request.user.branch:
                    branch = request.user.branch
                elif hasattr(request.user, 'branch_set'):
                    branch = request.user.branch_set.first()
                
                if branch and hasattr(branch, 'billing_subscription'):
                    sub = branch.billing_subscription
                    # Lock if expired
                    is_expired = False
                    if sub.is_trial:
                        is_expired = sub.trial_ends_at < timezone.now()
                    else:
                        is_expired = sub.expires_at < timezone.now()
                    
                    if is_expired:
                        return redirect('billing')
            except Exception:
                pass  # Don't break site if billing not set up yet
                
        return self.get_response(request)
        