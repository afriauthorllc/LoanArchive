from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    path('', views.loan_list, name='list'),
    path('create/', views.create_loan, name='create_loan'),
    path('create-application/', views.create_loan_application, name='create_application'),
    path('<int:pk>/', views.loan_detail, name='detail'),
    path('detail/<int:pk>/', views.loan_detail, name='loan_detail'),
    path('api/search/', views.loan_search_api, name='loan_search_api'),
    path('api/clients/search/', views.client_search_api, name='client_search_api'),
    path('reports/', views.reports_page, name='reports_page'),
    
]