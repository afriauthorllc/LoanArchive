"""
URL configuration for LoanArchive project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),      # dashboard at /
    path('clients/', include('clients.urls')),
    path('users/', include('users.urls')),
    path('loans/', include('loans.urls')),
    
]

# 📸 Serve uploaded media files while in DEBUG mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)