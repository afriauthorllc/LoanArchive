from django.urls import path
from . import views

urlpatterns = [
    path('', views.billing_page, name='billing'),
    path('pay/', views.billing_pay, name='billing_pay'),
]
