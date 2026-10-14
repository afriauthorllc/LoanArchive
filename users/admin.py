from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Company, Branch

# --- Inline Configuration ---
class BranchInline(admin.TabularInline):
    """Allows adding/editing branches directly inside the Company detail page."""
    model = Branch
    extra = 1

# --- Model Registrations ---
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'get_branch_count')
    search_fields = ('name',)
    inlines = [BranchInline]

    def get_branch_count(self, obj):
        return obj.branches.count()
    get_branch_count.short_description = 'Number of Branches'


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'location', 'created_at')
    list_filter = ('company',)
    search_fields = ('name', 'company__name', 'location')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Extends Django's default UserAdmin to support role choices,
    company ownership, and branch office staff sorting.
    """
    # UI Dashboard Table columns
    list_display = ('username', 'email', 'role', 'company', 'branch', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'company', 'branch')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'company__name', 'branch__name')
    ordering = ('username',)

    # Injection of Custom fields into Django User Detail View Form sections
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Role & Hierarchy Management'), {
            'fields': ('role', 'company', 'branch'),
            'description': _('Assign the architectural role and boundary mapping for this organizational user.')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # Fields to show when creating a brand-new user inside the backend panel
    add_fieldsets = UserAdmin.add_fieldsets + (
        (_('Organizational Alignment'), {
            'classes': ('collapse',),
            'fields': ('role', 'company', 'branch'),
        }),
    )
