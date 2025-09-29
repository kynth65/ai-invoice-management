from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for User model
    """
    list_display = [
        'email', 'first_name', 'last_name', 'company_name',
        'is_active', 'is_staff', 'date_joined', 'last_login'
    ]
    list_filter = [
        'is_active', 'is_staff', 'is_superuser', 'date_joined',
        'preferred_currency', 'timezone'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'company_name']
    ordering = ['-date_joined']
    readonly_fields = ['date_joined', 'last_login', 'last_login_ip']

    fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone_number', 'profile_picture')
        }),
        ('Business Info', {
            'fields': ('company_name', 'preferred_currency', 'timezone')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important dates', {
            'fields': ('last_login', 'last_login_ip', 'date_joined')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    def get_inline_instances(self, request, obj=None):
        if obj:
            return [UserProfileInline(self.model, self.admin_site)]
        return []


class UserProfileInline(admin.StackedInline):
    """
    Inline admin for UserProfile
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = [
        'bio', 'business_type', 'tax_id',
        'email_notifications', 'invoice_reminders', 'monthly_reports'
    ]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin for UserProfile model
    """
    list_display = [
        'user', 'business_type', 'email_notifications',
        'invoice_reminders', 'created_at'
    ]
    list_filter = [
        'business_type', 'email_notifications', 'invoice_reminders',
        'monthly_reports', 'created_at'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'business_type']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Business Information', {
            'fields': ('bio', 'business_type', 'tax_id')
        }),
        ('Notification Preferences', {
            'fields': ('email_notifications', 'invoice_reminders', 'monthly_reports')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
