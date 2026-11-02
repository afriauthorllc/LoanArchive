from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    # main list
    path('', views.notification_list, name='list'),
    
    # actions called from topbar.html
    path('<int:pk>/read/', views.mark_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('delete-read/', views.delete_read, name='delete_read'),
    
    # APIs for JS bell
    path('api/count/', views.unread_count, name='unread_count'),
    path('api/recent/', views.recent_notifications, name='recent'),
    path('api/preview/', views.recent_notifications, name='preview'),  # alias
]
