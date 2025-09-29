from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from .models import ExpenseSummary, BudgetAlert, SpendingTrend, UserDashboardMetrics
from .serializers import (
    ExpenseSummarySerializer, BudgetAlertSerializer, SpendingTrendSerializer,
    UserDashboardMetricsSerializer, DashboardStatsSerializer, MonthlyAnalyticsSerializer
)
from invoices.models import Invoice, Vendor


class ExpenseSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ExpenseSummary operations (read-only)
    """
    queryset = ExpenseSummary.objects.all()
    serializer_class = ExpenseSummarySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['year', 'month', 'total_amount']
    ordering = ['-year', '-month']

    def get_queryset(self):
        return ExpenseSummary.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def yearly_summary(self, request):
        """
        Get yearly expense summaries
        """
        year = request.query_params.get('year', timezone.now().year)
        summaries = self.get_queryset().filter(
            year=year,
            period_type='monthly'
        ).order_by('month')

        serializer = ExpenseSummarySerializer(summaries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def quarterly_summary(self, request):
        """
        Get quarterly expense summaries
        """
        year = request.query_params.get('year', timezone.now().year)
        summaries = self.get_queryset().filter(
            year=year,
            period_type='quarterly'
        ).order_by('quarter')

        serializer = ExpenseSummarySerializer(summaries, many=True)
        return Response(serializer.data)


class BudgetAlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for BudgetAlert operations
    """
    queryset = BudgetAlert.objects.all()
    serializer_class = BudgetAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    filterset_fields = ['status', 'alert_type']
    ordering_fields = ['created_at', 'triggered_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return BudgetAlert.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def active_alerts(self, request):
        """
        Get active budget alerts
        """
        alerts = self.get_queryset().filter(status='active')
        serializer = BudgetAlertSerializer(alerts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """
        Dismiss a budget alert
        """
        alert = self.get_object()
        alert.status = 'dismissed'
        alert.save()
        return Response({'message': 'Alert dismissed successfully'})


class SpendingTrendViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SpendingTrend operations (read-only)
    """
    queryset = SpendingTrend.objects.all()
    serializer_class = SpendingTrendSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['year', 'month', 'total_spent']
    ordering = ['-year', '-month']

    def get_queryset(self):
        return SpendingTrend.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def recent_trends(self, request):
        """
        Get recent spending trends (last 12 months)
        """
        trends = self.get_queryset()[:12]
        serializer = SpendingTrendSerializer(trends, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def yearly_trends(self, request):
        """
        Get spending trends for a specific year
        """
        year = request.query_params.get('year', timezone.now().year)
        trends = self.get_queryset().filter(year=year).order_by('month')
        serializer = SpendingTrendSerializer(trends, many=True)
        return Response(serializer.data)


class UserDashboardMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for UserDashboardMetrics operations (read-only)
    """
    queryset = UserDashboardMetrics.objects.all()
    serializer_class = UserDashboardMetricsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserDashboardMetrics.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_metrics(self, request):
        """
        Get current user's dashboard metrics
        """
        try:
            metrics = UserDashboardMetrics.objects.get(user=request.user)
            serializer = UserDashboardMetricsSerializer(metrics)
            return Response(serializer.data)
        except UserDashboardMetrics.DoesNotExist:
            # Create default metrics if none exist
            metrics = UserDashboardMetrics.objects.create(user=request.user)
            serializer = UserDashboardMetricsSerializer(metrics)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class AnalyticsViewSet(viewsets.ViewSet):
    """
    Custom ViewSet for analytics endpoints
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """
        Get comprehensive dashboard statistics
        """
        user = request.user
        now = timezone.now()
        current_month = now.replace(day=1)
        current_year = now.replace(month=1, day=1)

        # Get invoice queryset for user
        invoices = Invoice.objects.filter(user=user)

        # Current month stats
        current_month_invoices = invoices.filter(created_at__gte=current_month)
        current_month_total = current_month_invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        current_month_count = current_month_invoices.count()

        # Year-to-date stats
        ytd_invoices = invoices.filter(created_at__gte=current_year)
        ytd_total = ytd_invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        ytd_count = ytd_invoices.count()

        # Pending invoices
        pending_count = invoices.filter(status='pending').count()

        # Recent trends
        recent_trends = list(SpendingTrend.objects.filter(
            user=user
        ).order_by('-year', '-month')[:6].values(
            'month', 'year', 'total_spent', 'percentage_change'
        ))

        # Active alerts
        active_alerts_count = BudgetAlert.objects.filter(
            user=user, status='active'
        ).count()

        # Top vendors (current month)
        top_vendors = list(current_month_invoices.values(
            'vendor__name'
        ).annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('-total')[:5])

        stats_data = {
            'current_month_total': current_month_total,
            'current_month_invoices': current_month_count,
            'ytd_total': ytd_total,
            'ytd_invoices': ytd_count,
            'pending_invoices': pending_count,
            'recent_trends': recent_trends,
            'active_alerts': active_alerts_count,
            'top_vendors': top_vendors
        }

        serializer = DashboardStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def monthly_analytics(self, request):
        """
        Get detailed monthly analytics
        """
        user = request.user
        month = int(request.query_params.get('month', timezone.now().month))
        year = int(request.query_params.get('year', timezone.now().year))

        # Get invoices for the specified month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        monthly_invoices = Invoice.objects.filter(
            user=user,
            created_at__gte=start_date,
            created_at__lt=end_date
        )

        # Calculate totals
        total_amount = monthly_invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        invoice_count = monthly_invoices.count()

        # Vendor breakdown
        vendor_breakdown = dict(monthly_invoices.values(
            'vendor__name'
        ).annotate(
            total=Sum('total_amount')
        ).values_list('vendor__name', 'total'))

        # Daily breakdown
        daily_breakdown = list(monthly_invoices.extra(
            select={'day': 'DATE(created_at)'}
        ).values('day').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('day'))

        analytics_data = {
            'month': month,
            'year': year,
            'total_amount': total_amount,
            'invoice_count': invoice_count,
            'vendor_breakdown': vendor_breakdown,
            'daily_breakdown': daily_breakdown
        }

        serializer = MonthlyAnalyticsSerializer(analytics_data)
        return Response(serializer.data)
