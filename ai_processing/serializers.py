from rest_framework import serializers
from .models import AIProcessingTask


class AIProcessingTaskSerializer(serializers.ModelSerializer):
    """
    Serializer for AIProcessingTask model
    """
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    processing_duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = AIProcessingTask
        fields = [
            'id', 'invoice', 'invoice_number', 'task_type', 'task_type_display',
            'status', 'status_display', 'input_data', 'output_data', 'confidence_score',
            'error_message', 'retry_count', 'max_retries', 'started_at', 'completed_at',
            'processing_duration_ms', 'processing_duration_seconds', 'ai_model_version',
            'processing_node', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'processing_duration_ms', 'processing_duration_seconds',
            'created_at', 'updated_at'
        ]

    def get_processing_duration_seconds(self, obj):
        """
        Convert processing duration from milliseconds to seconds
        """
        if obj.processing_duration_ms:
            return round(obj.processing_duration_ms / 1000, 2)
        return None


class AIProcessingTaskCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating AI processing tasks
    """
    class Meta:
        model = AIProcessingTask
        fields = [
            'invoice', 'task_type', 'input_data', 'max_retries', 'ai_model_version'
        ]

    def create(self, validated_data):
        validated_data['status'] = 'pending'
        return super().create(validated_data)


class AIProcessingTaskListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for AI processing task list views
    """
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model = AIProcessingTask
        fields = [
            'id', 'invoice', 'invoice_number', 'task_type', 'task_type_display',
            'status', 'status_display', 'confidence_score', 'retry_count',
            'started_at', 'completed_at', 'created_at'
        ]


class AIProcessingStatsSerializer(serializers.Serializer):
    """
    Serializer for AI processing statistics
    """
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    failed_tasks = serializers.IntegerField()
    pending_tasks = serializers.IntegerField()
    processing_tasks = serializers.IntegerField()
    avg_confidence_score = serializers.FloatField()
    avg_processing_time_ms = serializers.FloatField()
    success_rate = serializers.FloatField()
    task_type_breakdown = serializers.DictField()
    recent_tasks = serializers.ListField()


class AIProcessingResultSerializer(serializers.Serializer):
    """
    Serializer for AI processing results
    """
    task_id = serializers.IntegerField()
    status = serializers.CharField()
    confidence_score = serializers.FloatField()
    extracted_data = serializers.DictField()
    processing_time_ms = serializers.IntegerField()
    error_message = serializers.CharField(required=False)
    suggestions = serializers.ListField(required=False)