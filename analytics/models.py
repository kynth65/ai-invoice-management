from django.db import models
from django.conf import settings
from decimal import Decimal


class ExpenseSummary(models.Model):
    """
    Pre-calculated expense summaries for analytics
    """
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='expense_summaries')
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES)

    # Time period
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField(null=True, blank=True)  # 1-12
    week = models.PositiveIntegerField(null=True, blank=True)   # 1-53
    day = models.PositiveIntegerField(null=True, blank=True)    # 1-31
    quarter = models.PositiveIntegerField(null=True, blank=True)  # 1-4

    # Summary data
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_invoices = models.PositiveIntegerField(default=0)
    avg_invoice_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Vendor breakdown (JSON field)
    vendor_breakdown = models.JSONField(default=dict)    # {vendor_id: amount}

    # Metadata
    last_calculated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'expense_summaries'
        verbose_name = 'Expense Summary'
        verbose_name_plural = 'Expense Summaries'
        unique_together = ['user', 'period_type', 'year', 'month', 'week', 'day', 'quarter']
        indexes = [
            models.Index(fields=['user', 'period_type', 'year']),
            models.Index(fields=['user', 'year', 'month']),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.period_type} - {self.year}"


class BudgetAlert(models.Model):
    """
    Budget tracking and alerts
    """
    ALERT_TYPES = [
        ('monthly_limit', 'Monthly Spending Limit'),
        ('vendor_limit', 'Vendor Spending Limit'),
        ('unusual_expense', 'Unusual Expense Pattern'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('triggered', 'Triggered'),
        ('dismissed', 'Dismissed'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='budget_alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Alert configuration
    threshold_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Optional filters
    vendor = models.ForeignKey('invoices.Vendor', on_delete=models.CASCADE, null=True, blank=True)

    # Time period for the alert
    period_start = models.DateField()
    period_end = models.DateField()

    # Alert details
    message = models.TextField(blank=True)
    is_email_sent = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'budget_alerts'
        verbose_name = 'Budget Alert'
        verbose_name_plural = 'Budget Alerts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name} - {self.get_alert_type_display()} - {self.status}"


class SpendingTrend(models.Model):
    """
    Tracks spending trends and patterns for insights
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='spending_trends')

    # Trend period
    month = models.PositiveIntegerField()  # 1-12
    year = models.PositiveIntegerField()

    # Trend data
    total_spent = models.DecimalField(max_digits=15, decimal_places=2)
    previous_month_spent = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    percentage_change = models.FloatField(default=0.0)  # % change from previous month

    # Vendor trends
    top_vendor = models.ForeignKey('invoices.Vendor', on_delete=models.SET_NULL, null=True, blank=True)
    top_vendor_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Insights
    insights = models.JSONField(default=list)  # AI-generated insights

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'spending_trends'
        verbose_name = 'Spending Trend'
        verbose_name_plural = 'Spending Trends'
        unique_together = ['user', 'year', 'month']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.user.full_name} - {self.year}/{self.month:02d}"


class UserDashboardMetrics(models.Model):
    """
    Cached dashboard metrics for quick loading
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_metrics')

    # Current month metrics
    current_month_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    current_month_invoices = models.PositiveIntegerField(default=0)
    current_month_pending = models.PositiveIntegerField(default=0)

    # Year-to-date metrics
    ytd_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    ytd_invoices = models.PositiveIntegerField(default=0)

    # All-time metrics
    total_lifetime_spent = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    total_lifetime_invoices = models.PositiveIntegerField(default=0)

    # Processing statistics
    ai_processed_count = models.PositiveIntegerField(default=0)
    ai_processing_accuracy = models.FloatField(default=0.0)  # Average confidence score

    # Quick stats
    favorite_vendor = models.ForeignKey('invoices.Vendor', on_delete=models.SET_NULL, null=True, blank=True)
    avg_monthly_spending = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Cache metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_dashboard_metrics'
        verbose_name = 'User Dashboard Metrics'
        verbose_name_plural = 'User Dashboard Metrics'

    def __str__(self):
        return f"Dashboard metrics for {self.user.full_name}"
