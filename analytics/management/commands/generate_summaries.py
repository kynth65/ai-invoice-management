from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from users.models import User
from invoices.models import Invoice
from analytics.models import ExpenseSummary, SpendingTrend, UserDashboardMetrics


class Command(BaseCommand):
    help = 'Generate analytics summaries for users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Generate summaries for specific user ID'
        )
        parser.add_argument(
            '--period',
            type=str,
            choices=['monthly', 'quarterly', 'yearly'],
            default='monthly',
            help='Period type for summaries (default: monthly)'
        )
        parser.add_argument(
            '--year',
            type=int,
            default=timezone.now().year,
            help='Year to generate summaries for (default: current year)'
        )
        parser.add_argument(
            '--month',
            type=int,
            help='Specific month to generate (1-12)'
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        period = options['period']
        year = options['year']
        month = options['month']

        # Get users to process
        if user_id:
            users = User.objects.filter(id=user_id)
        else:
            users = User.objects.filter(is_active=True)

        if not users:
            self.stdout.write(
                self.style.WARNING('No users found')
            )
            return

        self.stdout.write(
            f'Generating {period} summaries for {len(users)} users'
        )

        total_summaries = 0
        total_trends = 0
        total_metrics = 0

        for user in users:
            self.stdout.write(f'Processing user: {user.email}')

            # Generate expense summaries
            summaries_created = self.generate_expense_summaries(user, period, year, month)
            total_summaries += summaries_created

            # Generate spending trends (monthly only)
            if period == 'monthly':
                trends_created = self.generate_spending_trends(user, year, month)
                total_trends += trends_created

            # Update dashboard metrics
            metrics_updated = self.update_dashboard_metrics(user)
            total_metrics += metrics_updated

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated {total_summaries} summaries, '
                f'{total_trends} trends, and updated {total_metrics} metrics'
            )
        )

    def generate_expense_summaries(self, user, period, year, month):
        """Generate expense summaries for a user"""
        created = 0

        if period == 'monthly':
            months = [month] if month else range(1, 13)
            for m in months:
                created += self.create_monthly_summary(user, year, m)

        elif period == 'quarterly':
            quarters = range(1, 5)
            for q in quarters:
                created += self.create_quarterly_summary(user, year, q)

        elif period == 'yearly':
            created += self.create_yearly_summary(user, year)

        return created

    def create_monthly_summary(self, user, year, month):
        """Create monthly expense summary"""
        # Check if summary already exists
        summary, created = ExpenseSummary.objects.get_or_create(
            user=user,
            period_type='monthly',
            year=year,
            month=month,
            defaults={
                'total_amount': Decimal('0.00'),
                'total_invoices': 0,
                'avg_invoice_amount': Decimal('0.00'),
                'category_breakdown': {},
                'vendor_breakdown': {}
            }
        )

        if not created:
            self.stdout.write(f'  - Monthly summary for {year}-{month:02d} already exists')
            return 0

        # Calculate summary data
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        invoices = Invoice.objects.filter(
            user=user,
            created_at__gte=start_date,
            created_at__lt=end_date
        )

        # Calculate totals
        totals = invoices.aggregate(
            total_amount=Sum('total_amount'),
            total_invoices=Count('id'),
            avg_amount=Avg('total_amount')
        )

        summary.total_amount = totals['total_amount'] or Decimal('0.00')
        summary.total_invoices = totals['total_invoices']
        summary.avg_invoice_amount = totals['avg_amount'] or Decimal('0.00')

        # Category breakdown
        category_breakdown = dict(
            invoices.values('category__name').annotate(
                total=Sum('total_amount')
            ).values_list('category__name', 'total')
        )
        summary.category_breakdown = {k: float(v) for k, v in category_breakdown.items() if k}

        # Vendor breakdown
        vendor_breakdown = dict(
            invoices.values('vendor__name').annotate(
                total=Sum('total_amount')
            ).values_list('vendor__name', 'total')
        )
        summary.vendor_breakdown = {k: float(v) for k, v in vendor_breakdown.items() if k}

        summary.save()
        self.stdout.write(f'  - Created monthly summary for {year}-{month:02d}')
        return 1

    def create_quarterly_summary(self, user, year, quarter):
        """Create quarterly expense summary"""
        # Determine months for quarter
        quarter_months = {
            1: [1, 2, 3],
            2: [4, 5, 6],
            3: [7, 8, 9],
            4: [10, 11, 12]
        }
        months = quarter_months[quarter]

        # Check if summary already exists
        summary, created = ExpenseSummary.objects.get_or_create(
            user=user,
            period_type='quarterly',
            year=year,
            quarter=quarter,
            defaults={
                'total_amount': Decimal('0.00'),
                'total_invoices': 0,
                'avg_invoice_amount': Decimal('0.00'),
                'category_breakdown': {},
                'vendor_breakdown': {}
            }
        )

        if not created:
            self.stdout.write(f'  - Quarterly summary for {year} Q{quarter} already exists')
            return 0

        # Aggregate monthly summaries
        monthly_summaries = ExpenseSummary.objects.filter(
            user=user,
            period_type='monthly',
            year=year,
            month__in=months
        )

        total_amount = monthly_summaries.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        total_invoices = monthly_summaries.aggregate(
            total=Sum('total_invoices')
        )['total'] or 0

        summary.total_amount = total_amount
        summary.total_invoices = total_invoices
        summary.avg_invoice_amount = total_amount / total_invoices if total_invoices > 0 else Decimal('0.00')

        # Combine category and vendor breakdowns
        # This is simplified - in a real implementation you'd properly aggregate
        summary.category_breakdown = {}
        summary.vendor_breakdown = {}

        summary.save()
        self.stdout.write(f'  - Created quarterly summary for {year} Q{quarter}')
        return 1

    def create_yearly_summary(self, user, year):
        """Create yearly expense summary"""
        # Check if summary already exists
        summary, created = ExpenseSummary.objects.get_or_create(
            user=user,
            period_type='yearly',
            year=year,
            defaults={
                'total_amount': Decimal('0.00'),
                'total_invoices': 0,
                'avg_invoice_amount': Decimal('0.00'),
                'category_breakdown': {},
                'vendor_breakdown': {}
            }
        )

        if not created:
            self.stdout.write(f'  - Yearly summary for {year} already exists')
            return 0

        # Aggregate monthly summaries
        monthly_summaries = ExpenseSummary.objects.filter(
            user=user,
            period_type='monthly',
            year=year
        )

        total_amount = monthly_summaries.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        total_invoices = monthly_summaries.aggregate(
            total=Sum('total_invoices')
        )['total'] or 0

        summary.total_amount = total_amount
        summary.total_invoices = total_invoices
        summary.avg_invoice_amount = total_amount / total_invoices if total_invoices > 0 else Decimal('0.00')

        summary.save()
        self.stdout.write(f'  - Created yearly summary for {year}')
        return 1

    def generate_spending_trends(self, user, year, month):
        """Generate spending trends for a user"""
        months = [month] if month else range(1, 13)
        created = 0

        for m in months:
            trend, was_created = SpendingTrend.objects.get_or_create(
                user=user,
                year=year,
                month=m,
                defaults={
                    'total_spent': Decimal('0.00'),
                    'previous_month_spent': Decimal('0.00'),
                    'percentage_change': 0.0,
                    'insights': []
                }
            )

            if not was_created:
                continue

            # Get current month summary
            current_summary = ExpenseSummary.objects.filter(
                user=user,
                period_type='monthly',
                year=year,
                month=m
            ).first()

            if current_summary:
                trend.total_spent = current_summary.total_amount

                # Get previous month summary
                prev_year = year
                prev_month = m - 1
                if prev_month == 0:
                    prev_month = 12
                    prev_year = year - 1

                prev_summary = ExpenseSummary.objects.filter(
                    user=user,
                    period_type='monthly',
                    year=prev_year,
                    month=prev_month
                ).first()

                if prev_summary:
                    trend.previous_month_spent = prev_summary.total_amount
                    if prev_summary.total_amount > 0:
                        trend.percentage_change = float(
                            ((current_summary.total_amount - prev_summary.total_amount) / prev_summary.total_amount) * 100
                        )

            trend.save()
            created += 1
            self.stdout.write(f'  - Created spending trend for {year}-{m:02d}')

        return created

    def update_dashboard_metrics(self, user):
        """Update dashboard metrics for a user"""
        metrics, created = UserDashboardMetrics.objects.get_or_create(
            user=user,
            defaults={
                'current_month_total': Decimal('0.00'),
                'current_month_invoices': 0,
                'current_month_pending': 0,
                'ytd_total': Decimal('0.00'),
                'ytd_invoices': 0,
                'total_lifetime_spent': Decimal('0.00'),
                'total_lifetime_invoices': 0,
                'ai_processed_count': 0,
                'ai_processing_accuracy': 0.0,
                'avg_monthly_spending': Decimal('0.00')
            }
        )

        now = timezone.now()
        current_month = now.replace(day=1)
        current_year = now.replace(month=1, day=1)

        # Current month stats
        current_month_invoices = Invoice.objects.filter(
            user=user,
            created_at__gte=current_month
        )
        metrics.current_month_total = current_month_invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        metrics.current_month_invoices = current_month_invoices.count()
        metrics.current_month_pending = current_month_invoices.filter(status='pending').count()

        # Year-to-date stats
        ytd_invoices = Invoice.objects.filter(
            user=user,
            created_at__gte=current_year
        )
        metrics.ytd_total = ytd_invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        metrics.ytd_invoices = ytd_invoices.count()

        # Lifetime stats
        all_invoices = Invoice.objects.filter(user=user)
        metrics.total_lifetime_spent = all_invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        metrics.total_lifetime_invoices = all_invoices.count()

        metrics.save()
        self.stdout.write(f'  - Updated dashboard metrics')
        return 1