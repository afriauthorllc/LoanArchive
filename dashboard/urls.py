#dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),  # http://127.0.0.1:8000/ -> home.html
    path('reports/', views.reports, name='reports'), # http://127.0.0.1:8000/reports/
]