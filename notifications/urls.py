from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('api/', views.notification_api, name='api'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('mark-read/<int:pk>/', views.mark_read, name='mark_read'),
    # keep old name working
    path('mark/<int:pk>/', views.mark_read, name='mark_single'),
]