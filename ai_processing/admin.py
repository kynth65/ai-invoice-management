from django.contrib import admin
from django.utils.html import format_html
from .models import AIProcessingTask


@admin.register(AIProcessingTask)
class AIProcessingTaskAdmin(admin.ModelAdmin):
    """
    Admin for AIProcessingTask model
    """
    list_display = [
        'id', 'invoice_link', 'task_type', 'status', 'confidence_score',
        'retry_count', 'duration_display', 'created_at'
    ]
    list_filter = [
        'task_type', 'status', 'ai_model_version', 'processing_node',
        'created_at', 'started_at', 'completed_at'
    ]
    search_fields = [
        'invoice__invoice_number', 'invoice__user__email',
        'task_type', 'error_message', 'ai_model_version'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'created_at', 'updated_at', 'processing_duration_ms',
        'duration_display'
    ]

    fieldsets = (
        ('Task Information', {
            'fields': ('invoice', 'task_type', 'status')
        }),
        ('Processing Data', {
            'fields': ('input_data', 'output_data', 'confidence_score')
        }),
        ('Error Handling', {
            'fields': ('error_message', 'retry_count', 'max_retries')
        }),
        ('Timing', {
            'fields': (
                'started_at', 'completed_at', 'processing_duration_ms', 'duration_display'
            )
        }),
        ('Metadata', {
            'fields': ('ai_model_version', 'processing_node')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def invoice_link(self, obj):
        """Create a link to the invoice"""
        if obj.invoice:
            from django.urls import reverse
            url = reverse('admin:invoices_invoice_change', args=[obj.invoice.pk])
            return format_html('<a href="{}">{}</a>', url, obj.invoice)
        return "—"
    invoice_link.short_description = 'Invoice'

    def duration_display(self, obj):
        """Display processing duration in a readable format"""
        if obj.processing_duration_ms:
            if obj.processing_duration_ms < 1000:
                return f"{obj.processing_duration_ms}ms"
            elif obj.processing_duration_ms < 60000:
                return f"{obj.processing_duration_ms / 1000:.2f}s"
            else:
                minutes = obj.processing_duration_ms // 60000
                seconds = (obj.processing_duration_ms % 60000) / 1000
                return f"{minutes}m {seconds:.1f}s"
        return "—"
    duration_display.short_description = 'Duration'

    def get_queryset(self, request):
        """Filter queryset based on user permissions"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Regular users can only see tasks for their invoices
            qs = qs.filter(invoice__user=request.user)
        return qs

    actions = ['retry_failed_tasks', 'mark_as_completed', 'mark_as_failed']

    def retry_failed_tasks(self, request, queryset):
        """Retry selected failed tasks"""
        failed_tasks = queryset.filter(status='failed')
        retryable_tasks = failed_tasks.filter(retry_count__lt=3)

        updated = 0
        for task in retryable_tasks:
            task.status = 'pending'
            task.retry_count += 1
            task.error_message = ''
            task.save()
            updated += 1

        self.message_user(request, f'{updated} tasks queued for retry.')
    retry_failed_tasks.short_description = "Retry selected failed tasks"

    def mark_as_completed(self, request, queryset):
        """Mark selected tasks as completed"""
        updated = queryset.filter(status__in=['pending', 'processing']).update(status='completed')
        self.message_user(request, f'{updated} tasks marked as completed.')
    mark_as_completed.short_description = "Mark selected tasks as completed"

    def mark_as_failed(self, request, queryset):
        """Mark selected tasks as failed"""
        updated = queryset.filter(status__in=['pending', 'processing']).update(status='failed')
        self.message_user(request, f'{updated} tasks marked as failed.')
    mark_as_failed.short_description = "Mark selected tasks as failed"

    def has_add_permission(self, request):
        """Only allow superusers to manually create tasks"""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Allow editing with some restrictions"""
        if request.user.is_superuser:
            return True
        if obj and obj.invoice.user == request.user:
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        """Only allow superusers to delete tasks"""
        return request.user.is_superuser
