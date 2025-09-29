from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from invoices.models import Invoice
from ai_processing.models import AIProcessingTask


class Command(BaseCommand):
    help = 'Process invoices with AI extraction and categorization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Process invoices for specific user ID'
        )
        parser.add_argument(
            '--status',
            type=str,
            default='pending',
            help='Process invoices with specific status (default: pending)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of invoices to process (default: 10)'
        )
        parser.add_argument(
            '--task-types',
            nargs='+',
            default=['data_extraction', 'categorization'],
            help='AI task types to create (default: data_extraction categorization)'
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        status = options['status']
        limit = options['limit']
        task_types = options['task_types']

        # Build query
        query = Q(status=status)
        if user_id:
            query &= Q(user_id=user_id)

        # Get invoices to process
        invoices = Invoice.objects.filter(query)[:limit]

        if not invoices:
            self.stdout.write(
                self.style.WARNING('No invoices found matching criteria')
            )
            return

        self.stdout.write(
            f'Processing {len(invoices)} invoices with task types: {", ".join(task_types)}'
        )

        created_tasks = 0
        for invoice in invoices:
            self.stdout.write(f'Processing invoice {invoice.id}: {invoice}')

            for task_type in task_types:
                # Check if task already exists
                existing_task = AIProcessingTask.objects.filter(
                    invoice=invoice,
                    task_type=task_type,
                    status__in=['pending', 'processing', 'completed']
                ).first()

                if existing_task:
                    self.stdout.write(
                        f'  - Task {task_type} already exists (status: {existing_task.status})'
                    )
                    continue

                # Create new task
                task = AIProcessingTask.objects.create(
                    invoice=invoice,
                    task_type=task_type,
                    status='pending'
                )
                created_tasks += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  - Created {task_type} task (ID: {task.id})')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_tasks} AI processing tasks'
            )
        )