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