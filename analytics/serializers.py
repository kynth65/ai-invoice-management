from rest_framework import serializers
from .models import ExpenseSummary, BudgetAlert, SpendingTrend, UserDashboardMetrics


class ExpenseSummarySerializer(serializers.ModelSerializer):
    """
    Serializer for ExpenseSummary model
    """
    class Meta:
        model = ExpenseSummary
        fields = [
            'id', 'user', 'period_type', 'year', 'month', 'week', 'day', 'quarter',
            'total_amount', 'total_invoices', 'avg_invoice_amount',
            'vendor_breakdown', 'last_calculated', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'last_calculated', 'created_at']


class BudgetAlertSerializer(serializers.ModelSerializer):
    """
    Serializer for BudgetAlert model
    """
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)

    class Meta:
        model = BudgetAlert
        fields = [
            'id', 'user', 'alert_type', 'alert_type_display', 'status', 'status_display',
            'threshold_amount', 'current_amount',
            'vendor', 'vendor_name', 'period_start', 'period_end', 'message',
            'is_email_sent', 'triggered_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'current_amount', 'is_email_sent', 'triggered_at', 'created_at', 'updated_at']


class SpendingTrendSerializer(serializers.ModelSerializer):
    """
    Serializer for SpendingTrend model
    """
    top_vendor_name = serializers.CharField(source='top_vendor.name', read_only=True)

    class Meta:
        model = SpendingTrend
        fields = [
            'id', 'user', 'month', 'year', 'total_spent', 'previous_month_spent',
            'percentage_change',
            'top_vendor', 'top_vendor_name', 'top_vendor_amount', 'insights',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class UserDashboardMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer for UserDashboardMetrics model
    """
    favorite_vendor_name = serializers.CharField(source='favorite_vendor.name', read_only=True)

    class Meta:
        model = UserDashboardMetrics
        fields = [
            'id', 'user', 'current_month_total', 'current_month_invoices',
            'current_month_pending', 'ytd_total', 'ytd_invoices', 'total_lifetime_spent',
            'total_lifetime_invoices', 'ai_processed_count', 'ai_processing_accuracy',
            'favorite_vendor',
            'favorite_vendor_name', 'avg_monthly_spending', 'last_updated', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'last_updated', 'created_at']


class DashboardStatsSerializer(serializers.Serializer):
    """
    Serializer for dashboard statistics summary
    """
    current_month_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    current_month_invoices = serializers.IntegerField()
    ytd_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    ytd_invoices = serializers.IntegerField()
    pending_invoices = serializers.IntegerField()
    recent_trends = serializers.ListField()
    active_alerts = serializers.IntegerField()
    top_vendors = serializers.ListField()


class MonthlyAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for monthly analytics data
    """
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    invoice_count = serializers.IntegerField()
    vendor_breakdown = serializers.DictField()
    daily_breakdown = serializers.ListField()