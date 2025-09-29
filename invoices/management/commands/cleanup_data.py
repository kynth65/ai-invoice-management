from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

from invoices.models import InvoiceProcessingLog
from ai_processing.models import AIProcessingTask


class Command(BaseCommand):
    help = 'Clean up old data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete data older than N days (default: 90)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--clean-logs',
            action='store_true',
            help='Clean old processing logs'
        )
        parser.add_argument(
            '--clean-failed-tasks',
            action='store_true',
            help='Clean old failed AI processing tasks'
        )
        parser.add_argument(
            '--clean-completed-tasks',
            action='store_true',
            help='Clean old completed AI processing tasks'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        clean_logs = options['clean_logs']
        clean_failed_tasks = options['clean_failed_tasks']
        clean_completed_tasks = options['clean_completed_tasks']

        cutoff_date = timezone.now() - timedelta(days=days)

        self.stdout.write(
            f'Cleaning up data older than {days} days (before {cutoff_date.date()})'
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No data will be deleted')
            )

        total_deleted = 0

        # Clean processing logs
        if clean_logs:
            deleted = self.clean_processing_logs(cutoff_date, dry_run)
            total_deleted += deleted

        # Clean failed AI tasks
        if clean_failed_tasks:
            deleted = self.clean_failed_ai_tasks(cutoff_date, dry_run)
            total_deleted += deleted

        # Clean completed AI tasks
        if clean_completed_tasks:
            deleted = self.clean_completed_ai_tasks(cutoff_date, dry_run)
            total_deleted += deleted

        if not any([clean_logs, clean_failed_tasks, clean_completed_tasks]):
            self.stdout.write(
                self.style.WARNING(
                    'No cleanup options specified. Use --clean-logs, '
                    '--clean-failed-tasks, or --clean-completed-tasks'
                )
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Would delete {total_deleted} records (DRY RUN)'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {total_deleted} records'
                )
            )

    def clean_processing_logs(self, cutoff_date, dry_run):
        """Clean old invoice processing logs"""
        old_logs = InvoiceProcessingLog.objects.filter(
            created_at__lt=cutoff_date
        )

        count = old_logs.count()
        self.stdout.write(f'Found {count} old processing logs')

        if not dry_run and count > 0:
            deleted, _ = old_logs.delete()
            self.stdout.write(f'  - Deleted {deleted} processing logs')
            return deleted

        return count

    def clean_failed_ai_tasks(self, cutoff_date, dry_run):
        """Clean old failed AI processing tasks"""
        failed_tasks = AIProcessingTask.objects.filter(
            status='failed',
            created_at__lt=cutoff_date,
            retry_count__gte=3  # Only delete tasks that have exhausted retries
        )

        count = failed_tasks.count()
        self.stdout.write(f'Found {count} old failed AI tasks')

        if not dry_run and count > 0:
            deleted, _ = failed_tasks.delete()
            self.stdout.write(f'  - Deleted {deleted} failed AI tasks')
            return deleted

        return count

    def clean_completed_ai_tasks(self, cutoff_date, dry_run):
        """Clean old completed AI processing tasks"""
        completed_tasks = AIProcessingTask.objects.filter(
            status='completed',
            completed_at__lt=cutoff_date
        )

        count = completed_tasks.count()
        self.stdout.write(f'Found {count} old completed AI tasks')

        if not dry_run and count > 0:
            deleted, _ = completed_tasks.delete()
            self.stdout.write(f'  - Deleted {deleted} completed AI tasks')
            return deleted

        return count