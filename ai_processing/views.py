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
    serializer_class = AIProcessingTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['task_type', 'status', 'invoice__invoice_number']
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
    def stats(self, request):
        """
        Get AI processing statistics for the current user
        """
        queryset = self.get_queryset()

        # Overall stats
        total_tasks = queryset.count()
        completed_tasks = queryset.filter(status='completed').count()
        failed_tasks = queryset.filter(status='failed').count()
        pending_tasks = queryset.filter(status='pending').count()
        processing_tasks = queryset.filter(status='processing').count()

        # Success rate
        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Average processing time for completed tasks
        completed_with_time = queryset.filter(
            status='completed',
            processing_duration_ms__isnull=False
        )
        avg_processing_time = completed_with_time.aggregate(
            avg_time=Avg('processing_duration_ms')
        )['avg_time'] or 0

        # Tasks by type
        task_type_breakdown = queryset.values('task_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_tasks = queryset.filter(created_at__gte=week_ago).count()

        stats_data = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'pending_tasks': pending_tasks,
            'processing_tasks': processing_tasks,
            'success_rate': round(success_rate, 2),
            'avg_processing_time_ms': round(avg_processing_time, 2),
            'task_type_breakdown': list(task_type_breakdown),
            'recent_activity': recent_tasks
        }

        serializer = AIProcessingStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recent AI processing tasks for the current user
        """
        limit = int(request.query_params.get('limit', 20))
        queryset = self.get_queryset()[:limit]

        serializer = AIProcessingTaskListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def result(self, request, pk=None):
        """
        Get detailed result for a specific AI processing task
        """
        task = self.get_object()

        if task.status != 'completed':
            return Response(
                {'error': 'Task is not completed yet'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AIProcessingResultSerializer(task)
        return Response(serializer.data)

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

        # Create AI processing tasks
        created_tasks = []
        for task_type in task_types:
            if task_type in ['data_extraction', 'duplicate_detection']:
                task = AIProcessingTask.objects.create(
                    invoice=invoice,
                    task_type=task_type,
                    status='pending'
                )
                created_tasks.append(task)

        return Response({
            'message': f'Created {len(created_tasks)} AI processing tasks',
            'tasks': [
                {
                    'id': task.id,
                    'task_type': task.task_type,
                    'status': task.status
                }
                for task in created_tasks
            ]
        })

    @action(detail=False, methods=['get'])
    def queue_status(self, request):
        """
        Get current processing queue status
        """
        pending_tasks = self.get_queryset().filter(status='pending')
        processing_tasks = self.get_queryset().filter(status='processing')

        queue_status = {
            'pending_count': pending_tasks.count(),
            'processing_count': processing_tasks.count(),
            'queue_position': {}
        }

        # Calculate queue position for each task type
        for task_type in ['data_extraction', 'duplicate_detection']:
            type_pending = pending_tasks.filter(task_type=task_type).order_by('created_at')
            if type_pending.exists():
                # Position in queue (1-indexed)
                position = 1
                for task in type_pending:
                    if task.invoice.user == request.user:
                        queue_status['queue_position'][task_type] = position
                        break
                    position += 1

        return Response(queue_status)


class AIProcessingTaskListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Simple read-only viewset for listing AI processing tasks
    """
    serializer_class = AIProcessingTaskListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AIProcessingTask.objects.filter(
            invoice__user=self.request.user
        ).select_related('invoice').order_by('-created_at')