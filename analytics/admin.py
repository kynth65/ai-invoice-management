from django.contrib import admin
from django.utils.html import format_html
from .models import ExpenseSummary, BudgetAlert, SpendingTrend, UserDashboardMetrics


@admin.register(ExpenseSummary)
class ExpenseSummaryAdmin(admin.ModelAdmin):
    """
    Admin for ExpenseSummary model
    """
    list_display = [
        'user', 'period_type', 'year', 'month', 'total_amount',
        'total_invoices', 'avg_invoice_amount', 'last_calculated'
    ]
    list_filter = ['period_type', 'year', 'month', 'quarter', 'last_calculated']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-year', '-month', '-day']
    readonly_fields = ['last_calculated', 'created_at']

    fieldsets = (
        ('User & Period', {
            'fields': ('user', 'period_type')
        }),
        ('Time Period', {
            'fields': ('year', 'month', 'week', 'day', 'quarter')
        }),
        ('Summary Data', {
            'fields': ('total_amount', 'total_invoices', 'avg_invoice_amount')
        }),
        ('Breakdown Data', {
            'fields': ('vendor_breakdown',)
        }),
        ('Metadata', {
            'fields': ('last_calculated', 'created_at')
        }),
    )

    def has_add_permission(self, request):
        # These are auto-generated, so prevent manual addition
        return False


@admin.register(BudgetAlert)
class BudgetAlertAdmin(admin.ModelAdmin):
    """
    Admin for BudgetAlert model
    """
    list_display = [
        'user', 'alert_type', 'status', 'threshold_amount',
        'current_amount', 'progress_display', 'triggered_at', 'created_at'
    ]
    list_filter = ['alert_type', 'status', 'is_email_sent', 'created_at', 'triggered_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'message']
    ordering = ['-created_at']
    readonly_fields = ['current_amount', 'is_email_sent', 'triggered_at', 'created_at', 'updated_at']

    fieldsets = (
        ('User & Alert', {
            'fields': ('user', 'alert_type', 'status')
        }),
        ('Thresholds', {
            'fields': ('threshold_amount', 'current_amount')
        }),
        ('Filters', {
            'fields': ('vendor',)
        }),
        ('Time Period', {
            'fields': ('period_start', 'period_end')
        }),
        ('Alert Details', {
            'fields': ('message', 'is_email_sent', 'triggered_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def progress_display(self, obj):
        """Display progress towards threshold"""
        if obj.threshold_amount and obj.threshold_amount > 0:
            percentage = (obj.current_amount / obj.threshold_amount) * 100
            color = 'red' if percentage >= 100 else 'orange' if percentage >= 80 else 'green'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, percentage
            )
        return "—"
    progress_display.short_description = 'Progress'

    actions = ['dismiss_alerts', 'trigger_alerts']

    def dismiss_alerts(self, request, queryset):
        """Dismiss selected alerts"""
        updated = queryset.update(status='dismissed')
        self.message_user(request, f'{updated} alerts dismissed.')
    dismiss_alerts.short_description = "Dismiss selected alerts"

    def trigger_alerts(self, request, queryset):
        """Trigger selected alerts"""
        updated = queryset.update(status='triggered')
        self.message_user(request, f'{updated} alerts triggered.')
    trigger_alerts.short_description = "Trigger selected alerts"


@admin.register(SpendingTrend)
class SpendingTrendAdmin(admin.ModelAdmin):
    """
    Admin for SpendingTrend model
    """
    list_display = [
        'user', 'year', 'month', 'total_spent',
        'percentage_change_display', 'top_vendor', 'created_at'
    ]
    list_filter = ['year', 'month', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-year', '-month']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('User & Period', {
            'fields': ('user', 'month', 'year')
        }),
        ('Spending Data', {
            'fields': ('total_spent', 'previous_month_spent', 'percentage_change')
        }),
        ('Top Vendors', {
            'fields': (
                'top_vendor', 'top_vendor_amount'
            )
        }),
        ('Insights', {
            'fields': ('insights',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def percentage_change_display(self, obj):
        """Display percentage change with color coding"""
        if obj.percentage_change:
            color = 'red' if obj.percentage_change > 0 else 'green'
            symbol = '+' if obj.percentage_change > 0 else ''
            return format_html(
                '<span style="color: {};">{}{:.1f}%</span>',
                color, symbol, obj.percentage_change
            )
        return "—"
    percentage_change_display.short_description = 'Change %'

    def has_add_permission(self, request):
        # These are auto-generated, so prevent manual addition
        return False


@admin.register(UserDashboardMetrics)
class UserDashboardMetricsAdmin(admin.ModelAdmin):
    """
    Admin for UserDashboardMetrics model
    """
    list_display = [
        'user', 'current_month_total', 'current_month_invoices',
        'ytd_total', 'total_lifetime_spent', 'ai_processing_accuracy', 'last_updated'
    ]
    list_filter = ['last_updated', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-last_updated']
    readonly_fields = ['last_updated', 'created_at']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Current Month Metrics', {
            'fields': (
                'current_month_total', 'current_month_invoices', 'current_month_pending'
            )
        }),
        ('Year-to-Date Metrics', {
            'fields': ('ytd_total', 'ytd_invoices')
        }),
        ('Lifetime Metrics', {
            'fields': ('total_lifetime_spent', 'total_lifetime_invoices')
        }),
        ('AI Processing Stats', {
            'fields': ('ai_processed_count', 'ai_processing_accuracy')
        }),
        ('Favorites', {
            'fields': (
                'favorite_vendor', 'avg_monthly_spending'
            )
        }),
        ('Metadata', {
            'fields': ('last_updated', 'created_at')
        }),
    )

    def has_add_permission(self, request):
        # These are auto-generated, so prevent manual addition
        return False

    actions = ['refresh_metrics']

    def refresh_metrics(self, request, queryset):
        """Refresh selected metrics"""
        from django.utils import timezone
        updated = queryset.update(last_updated=timezone.now())
        self.message_user(request, f'{updated} metrics refreshed.')
    refresh_metrics.short_description = "Refresh selected metrics"
