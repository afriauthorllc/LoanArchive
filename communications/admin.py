from django.contrib import admin
from .models import StaffNotification

@admin.register(StaffNotification)
class StaffNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'title', 'is_read', 'loan', 'created_at')
    list_filter = ('is_read', 'created_at', 'recipient')
    search_fields = ('title', 'message', 'recipient__username', 'recipient__email')
    list_editable = ('is_read',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    # Make loan clickable
    def loan_link(self, obj):
        if obj.loan:
            return f"Loan #{obj.loan.id}"
        return "-"
    loan_link.short_description = "Loan"

    list_per_page = 25
    
    