from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    path('', views.loan_list, name='list'),
    path('create/', views.create_loan, name='create_loan'),
    path('create-application/', views.create_loan_application, name='create_application'),
    path('<int:pk>/', views.loan_detail, name='detail'),
    path('detail/<int:pk>/', views.loan_detail, name='loan_detail'),
    path('<int:loan_id>/repay/', views.create_repayment, name='repay'),
    
       
    path('repayments/', views.repayments_view, name='repayments'),
    path('repayments-page/', views.repayment_page, name='repayments_page'),
    path('repayments-live/', views.repayment_live_filter, name='repayment_live_filter'),
    
    path('api/search/', views.loan_search_api, name='loan_search_api'),
    path('api/clients/search/', views.client_search_api, name='client_search_api'),
    path('api/check-book/', views.check_book_number, name='check_book_number'),
    path('check-book/', views.check_book_number_api, name='check_book_number_api'),
    path('api/check-book-number/', views.check_book_number, name='check_book_number_alt'),
    path('api/bulk-repay/', views.bulk_repayment_submit, name='bulk_repayment_submit'),
]