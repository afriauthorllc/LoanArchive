from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Loan

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    # 📋 Columns visible in the dashboard grid list
    list_display = (
        'id', 
        'client', 
        'branch', 
        'principal_formatted', 
        'interest_rate_display',
        'duration_display',
        'total_payable_formatted', 
        'outstanding_balance_formatted',
        'status_badge', 
        'applied_at'
    )
    
    def outstanding_balance_formatted(self, obj):
        """Formats outstanding ledger calculations cleanly with commas for Uganda Shillings."""
        balance = obj.outstanding_balance
        if balance == 0:
            # 🛡️ FIX: Pass the style attributes securely using template interpolation placeholders
            return format_html('<span style="color: {}; font-weight: {};">{}</span>', '#4caf50', 'bold', 'Settled')
        return f"UGX {balance:,.0f}"
    
    outstanding_balance_formatted.short_description = _("Outstanding Balance")

    # 🔍 Quick filters on the sidebar
    list_filter = ('status', 'branch', 'applied_at', 'duration_months')
    
    # 🔎 Search text query bindings
    search_fields = (
        'id', 
        'client__first_name', 
        'client__last_name', 
        'client__nin', 
        'collateral_details'
    )
    
    # 🗂️ Clean structural visual form layouts
    fieldsets = (
        (None, {
            'fields': ('client', 'branch', 'status')
        }),
        (_('Financial Breakdowns'), {
            'fields': ('principal_amount', 'interest_rate', 'duration_months'),
            'description': _('Enter core accounting values. Total payable amounts will compute automatically.')
        }),
        (_('Security & Assets'), {
            'fields': ('collateral_details',),
        }),
        (_('Audit Logs & Governance'), {
            'fields': ('created_by_officer', 'reviewed_by', 'actioned_at', 'disbursed_at'),
            'classes': ('collapse',), # Collapses this section by default to save mobile screen space
        }),
    )

    # 🛑 Fields that are computed or automatically updated by system logic
    readonly_fields = ('actioned_at', 'disbursed_at')

    # --- 💡 Smart Formatting Methods ---

    def principal_formatted(self, obj):
        """Formats principal currency cleanly with commas (e.g. UGX 5,000,000)."""
        return f"UGX {obj.principal_amount:,.0f}"
    principal_formatted.short_description = _("Principal")
    principal_formatted.admin_order_field = 'principal_amount'

    def interest_rate_display(self, obj):
        return f"{obj.interest_rate}%"
    interest_rate_display.short_description = _("Interest")

    def duration_display(self, obj):
        return _(f"{obj.duration_months} Month(s)")
    duration_display.short_description = _("Term")

    def total_payable_formatted(self, obj):
        """Displays total payable from the model logic directly on the main index table."""
        return f"UGX {obj.total_payable:,.0f}"
    total_payable_formatted.short_description = _("Total Payable")

    def status_badge(self, obj):
        """Renders color-coded HTML badges matching your system workflow stages."""
        colors = {
            'PENDING': '#ff9800',      # Orange
            'APPROVED': '#2196f3',     # Blue
            'REJECTED': '#f44336',     # Red
            'DISBURSED': '#4caf50',    # Green
            'FULLY_PAID': '#9c27b0',   # Purple
            'DEFAULTED': '#333333',    # Dark Grey
        }
        color = colors.get(obj.status, '#ccc')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px; text-transform: uppercase;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _("Status")
    status_badge.admin_order_field = 'status'

    # --- ⚙️ Custom Automation Rules ---

    def save_model(self, request, obj, form, change):
        """
        Intercepts the save action to update the audit trail.
        Automatically stamps action/disbursement dates when statuses change.
        """
        if change: # If updating an existing application
            old_obj = Loan.objects.get(pk=obj.pk)
            
            # If changing from PENDING to APPROVED or REJECTED
            if old_obj.status == 'PENDING' and obj.status in ['APPROVED', 'REJECTED']:
                obj.reviewed_by = request.user
                obj.actioned_at = timezone.now()
                
            # If changing to DISBURSED
            if old_obj.status != 'DISBURSED' and obj.status == 'DISBURSED':
                if not obj.actioned_at:
                    obj.actioned_at = timezone.now()
                    obj.reviewed_by = request.user
                obj.disbursed_at = timezone.now()
        else:
            # When creating a brand-new application, assign the logged-in Field Officer
            if not obj.created_by_officer and request.user.role == 'FIELD_OFFICER':
                obj.created_by_officer = request.user
                
        super().save_model(request, obj, form, change)
        
        
from django.contrib import admin
from django.db import models
from .models import Repayment

# 📊 Inline configuration: View repayments inside the Loan view screen
class RepaymentInline(admin.TabularInline):
    model = Repayment
    extra = 0
    readonly_fields = ('book_number', 'branch', 'book_date', 'collected_by', 'collected_at', 'amount_paid', 'payment_mode')
    fields = ('book_number', 'book_date', 'branch', 'amount_paid', 'payment_mode', 'collected_by', 'collected_at')
    can_delete = False
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Repayment)
class RepaymentAdmin(admin.ModelAdmin):
    list_display = ('book_number', 'book_date', 'branch', 'get_client_name', 'loan_link', 'amount_formatted', 'payment_mode', 'collected_by', 'collected_at')
    list_display_links = ('book_number',)
    list_filter = ('payment_mode', 'collected_at', 'book_date', 'branch', 'loan__branch')
    search_fields = ('loan__id', 'loan__client__first_name', 'loan__client__last_name', 'transaction_reference')
    
    # book_number / branch / book_date auto, so readonly
    fields = ('book_number', 'book_date', 'branch', 'loan', 'amount_paid', 'payment_mode', 'transaction_reference', 'collected_by', 'collected_at')
    readonly_fields = ('book_number', 'book_date', 'branch', 'collected_by', 'collected_at')

    def get_client_name(self, obj):
        return obj.loan.client.full_name
    get_client_name.short_description = _("Client")

    def loan_link(self, obj):
        return f"Loan #{obj.loan.id}"
    loan_link.short_description = _("Loan Reference")

    def amount_formatted(self, obj):
        return f"UGX {obj.amount_paid:,.0f}"
    amount_formatted.short_description = _("Amount Paid")

    def save_model(self, request, obj, form, change):
        if not change:
            if not obj.collected_by_id:
                obj.collected_by = request.user
            if not obj.branch_id and obj.loan_id:
                obj.branch = obj.loan.branch
        try:
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            # show overpayment error in admin
            from django.contrib import messages
            messages.set_level(request, messages.ERROR)
            self.message_user(request, str(e), level=messages.ERROR)
        
        
