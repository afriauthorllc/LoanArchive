from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('passport_preview', 'full_name', 'nin', 'telephone_number', 'district', 'branch', 'assigned_field_officer', 'created_at')
    list_filter = ('branch', 'district', 'created_at')
    search_fields = ('full_name', 'nin', 'telephone_number', 'village', 'district')
    list_select_related = ('branch', 'assigned_field_officer')
    readonly_fields = ('created_at', 'updated_at', 'passport_preview_large')
    autocomplete_fields = ('branch', 'assigned_field_officer')
    
    fieldsets = (
        ('Photo', {
            'fields': ('passport_photo', 'passport_preview_large')
        }),
        ('Personal Info', {
            'fields': ('full_name', 'nin', 'telephone_number')
        }),
        ('Location', {
            'fields': ('village', 'parish', 'sub_county', 'district', 'landmark')
        }),
        ('Assignment', {
            'fields': ('branch', 'assigned_field_officer')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def passport_preview(self, obj):
        if obj.passport_photo:
            return format_html('<img src="{}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;" />', obj.passport_photo.url)
        return "-"
    passport_preview.short_description = "Photo"

    def passport_preview_large(self, obj):
        if obj.passport_photo:
            return format_html('<img src="{}" style="width:150px;height:150px;border-radius:8px;object-fit:cover;" />', obj.passport_photo.url)
        return "No photo"
    passport_preview_large.short_description = "Preview"
    
    