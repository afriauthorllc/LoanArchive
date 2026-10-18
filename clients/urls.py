from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('api/search/', views.client_search_api, name='client_search_api'), # FIRST
    path('', views.client_list, name='list'),
    path('add/', views.add_new_client, name='add'),
    path('add/', views.add_new_client, name='add_new_client'), # alias
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('<int:pk>/', views.client_detail, name='detail'),
    path('<int:client_id>/add-loan/', views.add_loan_for_client, name='add_loan_for_client'),
]