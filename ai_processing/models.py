from django.db import models
from django.conf import settings


class AIProcessingTask(models.Model):
    """
    Tracks AI processing tasks and their status
    """
    TASK_TYPES = [
        ('data_extraction', 'Data Extraction'),
        ('categorization', 'Invoice Categorization'),
        ('duplicate_detection', 'Duplicate Detection'),
        ('summary_generation', 'Summary Generation'),
        ('vendor_extraction', 'Vendor Information Extraction'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]

    # Task information
    invoice = models.ForeignKey('invoices.Invoice', on_delete=models.CASCADE, related_name='ai_tasks')
    task_type = models.CharField(max_length=30, choices=TASK_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Processing details
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    confidence_score = models.FloatField(default=0.0)

    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processing_duration_ms = models.PositiveIntegerField(null=True, blank=True)

    # Metadata
    ai_model_version = models.CharField(max_length=50, blank=True)
    processing_node = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_processing_tasks'
        verbose_name = 'AI Processing Task'
        verbose_name_plural = 'AI Processing Tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invoice', 'task_type']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.get_task_type_display()} for Invoice {self.invoice.id} - {self.status}"
