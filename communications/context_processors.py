from .models import StaffNotification

def notifications_preview(request):
    if not request.user.is_authenticated:
        return {'notifications_preview': [], 'unread_count': 0, 'unread_today_count': 0}
    qs = StaffNotification.objects.filter(recipient=request.user, is_read=False)
    return {
        'notifications_preview': qs.order_by('-created_at')[:5],
        'unread_count': qs.count(),
        'unread_today_count': qs.count(),
    }
    