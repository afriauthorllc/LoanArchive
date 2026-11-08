from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch

class ForcePasswordChangeMiddleware:
    """
    If user must change password, force them to the change page.
    Allows logout, password change, admin, and static files.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, 'must_change_password', False):
            # URLs that are always allowed
            allowed_paths = [
                '/admin/logout/',
                '/logout/',
                '/users/change-password/',
                '/change-password/',
                '/accounts/password_change/',
            ]
            # Also allow the named url if you have it
            try:
                allowed_paths.append(reverse('password_change'))
            except NoReverseMatch:
                pass
            try:
                allowed_paths.append(reverse('force_password_change'))
            except NoReverseMatch:
                pass

            # Allow static / media
            if request.path.startswith('/static/') or request.path.startswith('/media/'):
                return self.get_response(request)

            if request.path not in allowed_paths:
                # Don't loop if already on change page
                if 'change' not in request.path and 'password' not in request.path:
                    return redirect('/users/change-password/')

        return self.get_response(request)
