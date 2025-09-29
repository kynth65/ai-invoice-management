from rest_framework import serializers
from .models import Vendor, Invoice, InvoiceItem, InvoiceProcessingLog
from .file_processors import validate_uploaded_file




class VendorSerializer(serializers.ModelSerializer):
    """
    Serializer for Vendor model
    """
    full_address = serializers.ReadOnlyField()

    class Meta:
        model = Vendor
        fields = [
            'id', 'name', 'email', 'phone', 'website', 'address_line_1',
            'address_line_2', 'city', 'state', 'postal_code', 'country',
            'tax_id', 'business_registration', 'is_ai_verified', 'confidence_score',
            'full_address', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_ai_verified', 'confidence_score', 'created_at', 'updated_at']


class InvoiceItemSerializer(serializers.ModelSerializer):
    """
    Serializer for InvoiceItem model
    """
    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'description', 'quantity', 'unit_price', 'total_price',
            'product_code', 'unit_of_measure', 'ai_confidence',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_price', 'ai_confidence', 'created_at', 'updated_at']


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for Invoice model
    """
    vendor_details = VendorSerializer(source='vendor', read_only=True)
    items = InvoiceItemSerializer(many=True, read_only=True)
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'user', 'vendor', 'vendor_details',
            'invoice_number', 'invoice_date', 'due_date', 'subtotal', 'tax_amount',
            'total_amount', 'currency', 'original_file', 'file_type', 'file_size',
            'extracted_data', 'ai_confidence_score', 'is_ai_processed',
            'ai_processing_status', 'status', 'is_duplicate', 'duplicate_of',
            'notes', 'tags', 'ai_summary', 'items', 'is_overdue',
            'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'user', 'file_size', 'extracted_data', 'ai_confidence_score',
            'is_ai_processed', 'ai_processing_status', 'is_duplicate', 'duplicate_of',
            'ai_summary', 'created_at', 'updated_at', 'processed_at'
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating invoices with file upload
    """
    items = InvoiceItemSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        fields = [
            'vendor', 'invoice_number', 'invoice_date', 'due_date',
            'subtotal', 'tax_amount', 'total_amount', 'currency', 'original_file',
            'notes', 'tags', 'items'
        ]

    def validate_original_file(self, value):
        """
        Validate uploaded file format and size
        """
        if not value:
            return value

        # Validate file format
        validation_result = validate_uploaded_file(value.name)
        if not validation_result['valid']:
            raise serializers.ValidationError(validation_result['error'])

        # Validate file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size ({value.size} bytes) exceeds maximum allowed size ({max_size} bytes)"
            )

        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        validated_data['user'] = self.context['request'].user

        # Set file type and size
        if 'original_file' in validated_data:
            file = validated_data['original_file']
            validated_data['file_type'] = file.name.split('.')[-1].lower()
            validated_data['file_size'] = file.size

        invoice = Invoice.objects.create(**validated_data)

        # Create invoice items
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)

        return invoice


class InvoiceListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for invoice list views
    """
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'vendor_name', 'invoice_date',
            'due_date', 'total_amount', 'currency', 'status', 'is_duplicate',
            'is_overdue', 'created_at'
        ]


class InvoiceProcessingLogSerializer(serializers.ModelSerializer):
    """
    Serializer for InvoiceProcessingLog model
    """
    class Meta:
        model = InvoiceProcessingLog
        fields = [
            'id', 'processing_step', 'status', 'message', 'data',
            'started_at', 'completed_at', 'duration_ms', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class InvoiceStatsSerializer(serializers.Serializer):
    """
    Serializer for invoice statistics
    """
    total_invoices = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    pending_invoices = serializers.IntegerField()
    processed_invoices = serializers.IntegerField()
    this_month_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    this_month_count = serializers.IntegerField()
    avg_processing_time = serializers.FloatField()
    top_vendors = serializers.ListField()