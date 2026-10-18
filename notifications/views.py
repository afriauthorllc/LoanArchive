from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notification

# --- 1. VIEW ALL PAGE - for /notifications/ ---
@login_required
def notification_list(request):
    # Use direct query, not request.user.notifications (avoids related_name bugs)
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'notifications/list.html', {
        'notifications': notifs
    })

# --- 2. JSON API - for bell dropdown (optional, if you want AJAX) ---
@login_required
def notification_api(request):
    qs = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    data = []
    for n in qs:
        data.append({
            'id': n.id,
            'type': getattr(n, 'type', ''),
            'priority': getattr(n, 'priority', ''),
            'title': n.title,
            'message': n.message,
            'link': getattr(n, 'link', '/notifications/'),
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%d %b %H:%M') if hasattr(n.created_at, 'strftime') else str(n.created_at),
        })
    unread = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'notifications': data, 'unread': unread})

# --- 3. MARK ALL READ ---
@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', '/notifications/'))

# --- 4. MARK SINGLE READ - then go to its link ---
@login_required
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()
    if getattr(notif, 'link', None):
        return redirect(notif.link)
    return redirect(request.META.get('HTTP_REFERER', '/notifications/'))

# Alias for backward compatibility with your old urls
@login_required
def mark_single_read(request, pk):
    return mark_read(request, pk)