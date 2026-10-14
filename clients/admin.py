from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    # 📋 Columns visible in the dashboard list
    list_display = ('passport_thumbnail', 'full_name', 'nin', 'telephone_number', 'branch', 'assigned_field_officer', 'district', 'created_at')
    
    # 🔍 Side sidebar filters and text search parameters
    list_filter = ('branch', 'assigned_field_officer', 'district', 'created_at')
    search_fields = ('first_name', 'last_name', 'nin', 'telephone_number', 'village', 'district')
    
    # 🗂️ Clean visual layout groups for the client editing form
    fieldsets = (
        (None, {
            'fields': ('passport_photo', 'passport_preview_large')
        }),
        (_('Personal Information'), {
            'fields': ('first_name', 'last_name', 'nin')
        }),
        (_('Contact & Physical Address'), {
            'fields': ('telephone_number', 'district', 'sub_county', 'parish', 'village', 'landmark'),
            'description': _('Ensure details match local council (LC1) documentation for physical tracking.')
        }),
        (_('System Assignment'), {
            'fields': ('branch', 'assigned_field_officer'),
        }),
    )

    # 🛑 Set fields as read-only where we only display generated html
    readonly_fields = ('passport_preview_large',)

    # --- 📸 Image Preview Methods ---
    def passport_thumbnail(self, obj):
        """Displays a tiny image snippet in the dashboard list table."""
        if obj.passport_photo:
            return format_html(
                '<img src="{}" style="width: 45px; height: 45px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd;" />',
                obj.passport_photo.url
            )
        return _("No Photo")
    passport_thumbnail.short_description = _("Photo")

    def passport_preview_large(self, obj):
        """Displays a larger profile image preview inside the profile detail edit form."""
        if obj.passport_photo:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 8px; border: 2px solid #ccc;" />',
                obj.passport_photo.url
            )
        return _("No photo uploaded yet.")
    passport_preview_large.short_description = _("Current Photo Preview")
