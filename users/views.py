from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

def profile(request):
    return render(request, 'users/profile.html')
    
from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_view(request):
    logout(request)
    return redirect('users:login')    
    
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

@login_required
def force_password_change(request):
    # If they don't need to change, send them home
    if not request.user.must_change_password:
        return redirect('/')

    if request.method == 'POST':
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            # Clear the flag
            request.user.must_change_password = False
            request.user.save()
            # Keep them logged in after password change
            update_session_auth_hash(request, request.user)
            return redirect('/')
    else:
        form = SetPasswordForm(request.user)

    return render(request, 'users/force_password_change.html', {'form': form})
        
        
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView

class CustomPasswordResetView(PasswordResetView):
    template_name = 'users/password_reset_email.html'  # keep your existing form template if different, change this line if needed
    # If your reset form template is named differently, use that name here
    # e.g. template_name = 'users/password_reset_form.html'

    def form_valid(self, form):
        # Save email to session so the done page can show it
        self.request.session['reset_email'] = form.cleaned_data.get('email')
        return super().form_valid(form)

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email'] = self.request.session.get('reset_email', '')
        return context
        