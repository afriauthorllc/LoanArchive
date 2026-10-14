from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    path('', views.loan_list, name='list'), # /loans/
    path('create/', views.create_loan, name='create_loan'),
    path('<int:pk>/', views.loan_detail, name='loan_detail'),
    path('<int:pk>/', views.loan_detail, name='detail'),
    path('<int:loan_id>/repay/', views.create_repayment, name='repay'),
]