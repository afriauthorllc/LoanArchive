from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Subscription, Payment

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('branch', 'status', 'is_trial', 'days_left', 'expires_at', 'amount')
    list_filter = ('status', 'is_trial')
    search_fields = ('branch__name',)
    readonly_fields = ('days_left',)
    
    actions = ['extend_7_days', 'extend_30_days']

    @admin.action(description='Extend trial/subscription by 7 days')
    def extend_7_days(self, request, queryset):
        from datetime import timedelta
        from django.utils import timezone
        for sub in queryset:
            if sub.is_trial:
                sub.trial_ends_at += timedelta(days=7)
                sub.expires_at = sub.trial_ends_at
            else:
                sub.expires_at += timedelta(days=7)
            sub.save()

    @admin.action(description='Extend by 30 days (Paid)')
    def extend_30_days(self, request, queryset):
        from datetime import timedelta
        for sub in queryset:
            sub.is_trial = False
            sub.status = 'active'
            sub.expires_at += timedelta(days=30)
            sub.save()

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('branch', 'amount', 'method', 'status', 'created_at')
    list_filter = ('method', 'status')
    
    