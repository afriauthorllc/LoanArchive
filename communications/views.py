from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import StaffNotification

@login_required
def notification_list(request):
    notifications = StaffNotification.objects.filter(recipient=request.user).order_by('-created_at')[:50]
    return render(request, 'communications/list.html', {'notifications': notifications})

@login_required
def mark_read(request, pk):
    n = get_object_or_404(StaffNotification, pk=pk, recipient=request.user)
    n.is_read = True
    n.save(update_fields=['is_read'])
    return redirect(n.link or 'communications:list')

@login_required
def mark_all_read(request):
    StaffNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'communications:list'))

@login_required
def delete_read(request):
    StaffNotification.objects.filter(recipient=request.user, is_read=True).delete()
    return redirect(request.META.get('HTTP_REFERER', 'communications:list'))

@login_required
def unread_count(request):
    count = StaffNotification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})

@login_required
def recent_notifications(request):
    qs = StaffNotification.objects.filter(recipient=request.user).order_by('-created_at')[:5]
    data = [{
        'id': n.id, 
        'title': n.title, 
        'message': n.message, 
        'is_read': n.is_read, 
        'link': n.link,
        'created_at': n.created_at.isoformat()
    } for n in qs]
    unread = StaffNotification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'notifications': data, 'unread': unread, 'count': unread})
        
        