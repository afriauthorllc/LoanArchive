from .models import Notification

def unread_count(request):
    if request.user.is_authenticated:
        qs = Notification.objects.filter(user=request.user).order_by('-created_at')
        return {
            'unread_count': qs.filter(is_read=False).count(),
            'recent_notifications': qs[:5]
        }
    return {'unread_count': 0, 'recent_notifications': []}