from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('view-payments/', RedirectView.as_view(url='/transactions/view-payments/', permanent=False)),
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('clients/', include('clients.urls')),
    path('users/', include('users.urls')),
    path('loans/', include('loans.urls')),
    path('transactions/', include('transactions.urls')),
    path('communications/', include('communications.urls')),
    #path('notifications/', include('notifications.urls')),
    path('billing/', include('billing.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
