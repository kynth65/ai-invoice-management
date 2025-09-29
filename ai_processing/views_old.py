from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta

from .models import AIProcessingTask
from .serializers import (
    AIProcessingTaskSerializer, AIProcessingTaskCreateSerializer,
    AIProcessingTaskListSerializer, AIProcessingStatsSerializer,
    AIProcessingResultSerializer
)
from invoices.models import Invoice


class AIProcessingTaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AIProcessingTask operations
    """
    queryset = AIProcessingTask.objects.all()
    serializer_class = AIProcessingTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    filterset_fields = ['status', 'task_type', 'invoice']
    ordering_fields = ['created_at', 'started_at', 'completed_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return AIProcessingTask.objects.filter(invoice__user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return AIProcessingTaskListSerializer
        elif self.action == 'create':
            return AIProcessingTaskCreateSerializer
        return AIProcessingTaskSerializer

    @action(detail=False, methods=['get'])
    def pending_tasks(self, request):
        """
        Get pending AI processing tasks
        """
        tasks = self.get_queryset().filter(status='pending')
        serializer = AIProcessingTaskListSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def processing_tasks(self, request):
        """
        Get currently processing AI tasks
        """
        tasks = self.get_queryset().filter(status='processing')
        serializer = AIProcessingTaskListSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def failed_tasks(self, request):
        """
        Get failed AI processing tasks
        """
        tasks = self.get_queryset().filter(status='failed')
        serializer = AIProcessingTaskListSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def retry_task(self, request, pk=None):
        """
        Retry a failed AI processing task
        """
        task = self.get_object()

        if task.status != 'failed':
            return Response(
                {'error': 'Only failed tasks can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if task.retry_count >= task.max_retries:
            return Response(
                {'error': 'Maximum retry limit reached'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task.status = 'pending'
        task.retry_count += 1
        task.error_message = ''
        task.save()

        return Response({'message': 'Task queued for retry'})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get AI processing statistics
        """
        queryset = self.get_queryset()

        # Basic counts
        total_tasks = queryset.count()
        completed_tasks = queryset.filter(status='completed').count()
        failed_tasks = queryset.filter(status='failed').count()
        pending_tasks = queryset.filter(status='pending').count()
        processing_tasks = queryset.filter(status='processing').count()

        # Averages
        completed_queryset = queryset.filter(status='completed')
        avg_confidence = completed_queryset.aggregate(
            avg=Avg('confidence_score')
        )['avg'] or 0.0

        avg_processing_time = completed_queryset.aggregate(
            avg=Avg('processing_duration_ms')
        )['avg'] or 0.0

        # Success rate
        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0

        # Task type breakdown
        task_type_breakdown = dict(
            queryset.values('task_type').annotate(
                count=Count('id')
            ).values_list('task_type', 'count')
        )

        # Recent tasks
        recent_tasks = list(
            queryset.order_by('-created_at')[:10].values(
                'id', 'task_type', 'status', 'confidence_score', 'created_at'
            )
        )

        stats_data = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'pending_tasks': pending_tasks,
            'processing_tasks': processing_tasks,
            'avg_confidence_score': avg_confidence,
            'avg_processing_time_ms': avg_processing_time,
            'success_rate': success_rate,
            'task_type_breakdown': task_type_breakdown,
            'recent_tasks': recent_tasks
        }

        serializer = AIProcessingStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent_results(self, request):
        """
        Get recent AI processing results
        """
        days = int(request.query_params.get('days', 7))
        since_date = timezone.now() - timedelta(days=days)

        recent_tasks = self.get_queryset().filter(
            completed_at__gte=since_date,
            status='completed'
        ).order_by('-completed_at')

        serializer = AIProcessingTaskListSerializer(recent_tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_create_tasks(self, request):
        """
        Create multiple AI processing tasks for invoices
        """
        invoice_ids = request.data.get('invoice_ids', [])
        task_types = request.data.get('task_types', ['data_extraction'])

        if not invoice_ids:
            return Response(
                {'error': 'invoice_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify invoices belong to the user
        invoices = Invoice.objects.filter(
            id__in=invoice_ids,
            user=request.user
        )

        if len(invoices) != len(invoice_ids):
            return Response(
                {'error': 'Some invoices not found or not accessible'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_tasks = []
        for invoice in invoices:
            for task_type in task_types:
                # Check if task already exists
                existing_task = AIProcessingTask.objects.filter(
                    invoice=invoice,
                    task_type=task_type,
                    status__in=['pending', 'processing', 'completed']
                ).first()

                if not existing_task:
                    task = AIProcessingTask.objects.create(
                        invoice=invoice,
                        task_type=task_type,
                        status='pending'
                    )
                    created_tasks.append(task)

        serializer = AIProcessingTaskListSerializer(created_tasks, many=True)
        return Response({
            'message': f'Created {len(created_tasks)} AI processing tasks',
            'tasks': serializer.data
        }, status=status.HTTP_201_CREATED)


class AIProcessingViewSet(viewsets.ViewSet):
    """
    Custom ViewSet for AI processing operations
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def process_invoice(self, request):
        """
        Process a single invoice with all AI tasks
        """
        invoice_id = request.data.get('invoice_id')
        task_types = request.data.get('task_types', [
            'data_extraction', 'duplicate_detection'
        ])

        if not invoice_id:
            return Response(
                {'error': 'invoice_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'Invoice not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        created_tasks = []
        for task_type in task_types:
            # Check if task already exists
            existing_task = AIProcessingTask.objects.filter(
                invoice=invoice,
                task_type=task_type,
                status__in=['pending', 'processing', 'completed']
            ).first()

            if not existing_task:
                task = AIProcessingTask.objects.create(
                    invoice=invoice,
                    task_type=task_type,
                    status='pending'
                )
                created_tasks.append(task)

        serializer = AIProcessingTaskListSerializer(created_tasks, many=True)
        return Response({
            'message': f'Created {len(created_tasks)} AI processing tasks for invoice {invoice_id}',
            'tasks': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def processing_queue(self, request):
        """
        Get the current AI processing queue status
        """
        user_tasks = AIProcessingTask.objects.filter(invoice__user=request.user)

        queue_status = {
            'pending_count': user_tasks.filter(status='pending').count(),
            'processing_count': user_tasks.filter(status='processing').count(),
            'queue_position': {},
            'estimated_wait_time': 0  # Could be calculated based on current processing times
        }

        # Calculate queue position for each task type
        for task_type_choice in AIProcessingTask.TASK_TYPES:
            task_type = task_type_choice[0]
            pending_tasks = user_tasks.filter(
                status='pending',
                task_type=task_type
            ).order_by('created_at')

            if pending_tasks.exists():
                # Position of first pending task for this type
                first_task = pending_tasks.first()
                position = AIProcessingTask.objects.filter(
                    status='pending',
                    task_type=task_type,
                    created_at__lt=first_task.created_at
                ).count() + 1

                queue_status['queue_position'][task_type] = position

        return Response(queue_status)

    @action(detail=False, methods=['post'])
    def categorize_invoice(self, request):
        """
        Categorize a single invoice using AI content analysis
        """
        invoice_id = request.data.get('invoice_id')
        min_confidence = request.data.get('min_confidence', 0.3)

        if not invoice_id:
            return Response(
                {'error': 'invoice_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invoice = Invoice.objects.get(id=invoice_id, user=request.user)
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'Invoice not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        categorizer = InvoiceAICategorizer()
        category, confidence = categorizer.categorize_invoice(invoice)

        result = {
            'invoice_id': invoice_id,
            'suggested_category': category.name if category else None,
            'confidence_score': confidence,
            'current_category': invoice.category.name if invoice.category else None,
            'applied': False
        }

        # Apply categorization if confidence is above threshold
        if category and confidence >= min_confidence:
            original_category = invoice.category
            invoice.category = category
            invoice.ai_confidence_score = confidence
            invoice.save(update_fields=['category', 'ai_confidence_score'])
            result['applied'] = True
            result['previous_category'] = original_category.name if original_category else None

        return Response(result)

    @action(detail=False, methods=['post'])
    def categorize_multiple(self, request):
        """
        Categorize multiple invoices using AI content analysis
        """
        invoice_ids = request.data.get('invoice_ids', [])
        min_confidence = request.data.get('min_confidence', 0.3)

        if not invoice_ids:
            return Response(
                {'error': 'invoice_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify invoices belong to the user
        invoices = Invoice.objects.filter(
            id__in=invoice_ids,
            user=request.user
        )

        if len(invoices) != len(invoice_ids):
            return Response(
                {'error': 'Some invoices not found or not accessible'},
                status=status.HTTP_400_BAD_REQUEST
            )

        categorizer = InvoiceAICategorizer()
        results = []

        for invoice in invoices:
            category, confidence = categorizer.categorize_invoice(invoice)

            result = {
                'invoice_id': invoice.id,
                'suggested_category': category.name if category else None,
                'confidence_score': confidence,
                'current_category': invoice.category.name if invoice.category else None,
                'applied': False
            }

            # Apply categorization if confidence is above threshold
            if category and confidence >= min_confidence:
                original_category = invoice.category
                invoice.category = category
                invoice.ai_confidence_score = confidence
                invoice.save(update_fields=['category', 'ai_confidence_score'])
                result['applied'] = True
                result['previous_category'] = original_category.name if original_category else None

            results.append(result)

        categorized_count = sum(1 for r in results if r['applied'])

        return Response({
            'message': f'Processed {len(results)} invoices, categorized {categorized_count}',
            'results': results,
            'stats': {
                'total_processed': len(results),
                'successfully_categorized': categorized_count,
                'low_confidence': len(results) - categorized_count
            }
        })

    @action(detail=False, methods=['post'])
    def auto_categorize_all(self, request):
        """
        Auto-categorize all uncategorized invoices for the current user
        """
        min_confidence = request.data.get('min_confidence', 0.3)

        # Get user's uncategorized invoices
        uncategorized_invoices = Invoice.objects.filter(
            user=request.user,
            category__isnull=True
        )

        if not uncategorized_invoices.exists():
            return Response({
                'message': 'No uncategorized invoices found',
                'stats': {
                    'total_processed': 0,
                    'successfully_categorized': 0,
                    'low_confidence': 0
                }
            })

        categorizer = InvoiceAICategorizer()
        stats = {
            'total_processed': 0,
            'successfully_categorized': 0,
            'low_confidence': 0
        }

        for invoice in uncategorized_invoices:
            stats['total_processed'] += 1

            if categorizer.auto_categorize_invoice(invoice, min_confidence):
                stats['successfully_categorized'] += 1
            else:
                stats['low_confidence'] += 1

        success_rate = (stats['successfully_categorized'] / stats['total_processed'] * 100) if stats['total_processed'] > 0 else 0

        return Response({
            'message': f'Auto-categorization completed for {stats["total_processed"]} invoices',
            'stats': {
                **stats,
                'success_rate': round(success_rate, 1)
            }
        })
