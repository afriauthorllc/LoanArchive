from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('', views.client_list, name='list'), # /clients/
    path('<int:pk>/', views.client_detail, name='detail'),
    path('', views.client_list, name='list'),
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('clients/add/', views.add_new_client, name='add_new_client'),
]

