"""
Django management command to process AI tasks
Usage: python manage.py process_ai_tasks
"""

from django.core.management.base import BaseCommand
from django.conf import settings

from ai_processing.task_processor import process_pending_tasks


class Command(BaseCommand):
    help = 'Process pending AI tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-tasks',
            type=int,
            default=10,
            help='Maximum number of tasks to process (default: 10)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing'
        )

    def handle(self, *args, **options):
        max_tasks = options['max_tasks']
        dry_run = options['dry_run']

        # Check if OpenAI API key is configured
        if not settings.OPENAI_API_KEY:
            self.stdout.write(
                self.style.ERROR(
                    'OPENAI_API_KEY not configured. Please set it in your .env file.'
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Processing up to {max_tasks} AI tasks...')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No tasks will be processed')
            )
            # Show pending tasks
            from ai_processing.models import AIProcessingTask
            pending_tasks = AIProcessingTask.objects.filter(status='pending')[:max_tasks]

            if pending_tasks:
                self.stdout.write(f'Would process {len(pending_tasks)} tasks:')
                for task in pending_tasks:
                    self.stdout.write(f'  - Task {task.id}: {task.task_type} for Invoice {task.invoice.id}')
            else:
                self.stdout.write('No pending tasks found.')
            return

        try:
            processed_count = process_pending_tasks(max_tasks=max_tasks)

            if processed_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully processed {processed_count} tasks.')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('No pending tasks found.')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing tasks: {e}')
            )