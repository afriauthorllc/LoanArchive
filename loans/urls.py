from django.urls import path
from . import views
from .views import repayment_live_filter, check_book_number_api

app_name = 'loans'

urlpatterns = [
    path('repayments-live/', views.repayment_live_filter, name='repayment_live_filter'),
    path('check-book/', views.check_book_number_api, name='check_book_number_api'),
    path('', views.loan_list, name='list'), # /loans/
    path('create/', views.create_loan, name='create_loan'),
    
    # NEW - for your dashboard + Create New Application modal (doesn't conflict with create/)
    path('create-application/', views.create_loan_application, name='create_application'),
    path('api/clients/search/', views.client_search_api, name='client_search_api'),

    path('<int:pk>/', views.loan_detail, name='loan_detail'),
    path('<int:pk>/', views.loan_detail, name='detail'), # kept duplicate for compatibility
    path('<int:loan_id>/repay/', views.create_repayment, name='repay'),
    
    #Repayments
    path('repayments/', views.repayment_page, name='repayments_page'),
    path('api/check-book-number/', views.check_book_number, name='check_book_number'),
    path('api/bulk-repay/', views.bulk_repayment_submit, name='bulk_repayment_submit'),
]