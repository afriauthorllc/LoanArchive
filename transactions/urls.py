from django.urls import path
from .services.executions import create_repayment, bulk_repayment_submit, edit_repayment
from .import views
app_name = 'transactions'
urlpatterns = [
    path('repayments/', views.repayments_view, name='repayments'),
    path('repayments-page/', views.repayment_page, name='repayments_page'),
    path('repayments-live/', views.repayment_live_filter, name='repayment_live_filter'),
    path('api/check-book/', views.check_book_number, name='check_book_number'),
    path('check-book/', views.check_book_number_api, name='check_book_number_api'),
    path('api/check-book-number/', views.check_book_number, name='check_book_number_alt'),
    path('<int:loan_id>/repay/', create_repayment, name='repay'),
    path('api/bulk-repay/', bulk_repayment_submit, name='bulk_repayment_submit'),
    
    path('view-payments/', views.view_repayments, name='view_repayments'),
    path('check-book/', views.check_book_number, name='check_book_number'),
    path('bulk-repayment/', bulk_repayment_submit, name='bulk_repayment_submit'),
    path('edit-payments/<int:pk>/', edit_repayment, name='edit_payment'),
    
    path('scanner/', views.scanner, name='scanner'),
    path('verify/', views.verify, name='verify'),
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('receipt/<str:verify_code>/', views.receipt, name='receipt'),
    path('receipts/bulk/', views.bulk_print_receipts, name='bulk_print_receipts'),
    
]