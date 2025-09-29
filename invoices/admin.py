from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Vendor, Invoice, InvoiceItem, InvoiceProcessingLog




@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    """
    Admin for Vendor model
    """
    list_display = [
        'name', 'email', 'city', 'country', 'is_ai_verified',
        'confidence_score', 'invoice_count', 'created_at'
    ]
    list_filter = ['is_ai_verified', 'country', 'city', 'created_at']
    search_fields = ['name', 'email', 'city', 'country', 'tax_id']
    ordering = ['name']
    readonly_fields = ['is_ai_verified', 'confidence_score', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'phone', 'website')
        }),
        ('Address', {
            'fields': (
                'address_line_1', 'address_line_2', 'city',
                'state', 'postal_code', 'country'
            )
        }),
        ('Business Information', {
            'fields': ('tax_id', 'business_registration')
        }),
        ('AI Processing', {
            'fields': ('is_ai_verified', 'confidence_score')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def invoice_count(self, obj):
        """Count of invoices from this vendor"""
        return obj.invoices.count()
    invoice_count.short_description = 'Invoices'


class InvoiceItemInline(admin.TabularInline):
    """
    Inline admin for InvoiceItem
    """
    model = InvoiceItem
    extra = 0
    readonly_fields = ['total_price', 'ai_confidence']
    fields = [
        'description', 'quantity', 'unit_price', 'total_price',
        'product_code', 'unit_of_measure', 'ai_confidence'
    ]


class InvoiceProcessingLogInline(admin.TabularInline):
    """
    Inline admin for InvoiceProcessingLog
    """
    model = InvoiceProcessingLog
    extra = 0
    readonly_fields = ['processing_step', 'status', 'message', 'started_at', 'completed_at', 'duration_ms']
    fields = ['processing_step', 'status', 'message', 'started_at', 'completed_at', 'duration_ms']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """
    Admin for Invoice model
    """
    list_display = [
        'invoice_number', 'user', 'vendor', 'total_amount', 'currency',
        'status', 'is_duplicate', 'is_overdue_display', 'created_at'
    ]
    list_filter = [
        'status', 'is_duplicate', 'currency', 'is_ai_processed',
        'ai_processing_status', 'created_at', 'invoice_date'
    ]
    search_fields = [
        'invoice_number', 'user__email', 'vendor__name', 'notes'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'file_size', 'extracted_data', 'ai_confidence_score',
        'is_ai_processed', 'ai_processing_status', 'ai_summary',
        'created_at', 'updated_at', 'processed_at', 'file_preview'
    ]
    inlines = [InvoiceItemInline, InvoiceProcessingLogInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'vendor', 'invoice_number')
        }),
        ('Dates', {
            'fields': ('invoice_date', 'due_date')
        }),
        ('Financial Information', {
            'fields': ('subtotal', 'tax_amount', 'total_amount', 'currency')
        }),
        ('File Information', {
            'fields': ('original_file', 'file_preview', 'file_type', 'file_size')
        }),
        ('AI Processing', {
            'fields': (
                'extracted_data', 'ai_confidence_score', 'is_ai_processed',
                'ai_processing_status', 'ai_summary'
            )
        }),
        ('Status & Workflow', {
            'fields': ('status', 'is_duplicate', 'duplicate_of')
        }),
        ('Notes & Tags', {
            'fields': ('notes', 'tags')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at')
        }),
    )

    def is_overdue_display(self, obj):
        """Display overdue status with color"""
        if obj.is_overdue:
            return format_html('<span style="color: red;">Yes</span>')
        return format_html('<span style="color: green;">No</span>')
    is_overdue_display.short_description = 'Overdue'

    def file_preview(self, obj):
        """Display file download link"""
        if obj.original_file:
            return format_html(
                '<a href="{}" target="_blank">View File</a>',
                obj.original_file.url
            )
        return "No file"
    file_preview.short_description = 'File Preview'

    actions = ['mark_as_paid', 'mark_as_approved', 'mark_as_duplicate']

    def mark_as_paid(self, request, queryset):
        """Mark selected invoices as paid"""
        updated = queryset.update(status='paid')
        self.message_user(request, f'{updated} invoices marked as paid.')
    mark_as_paid.short_description = "Mark selected invoices as paid"

    def mark_as_approved(self, request, queryset):
        """Mark selected invoices as approved"""
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} invoices marked as approved.')
    mark_as_approved.short_description = "Mark selected invoices as approved"

    def mark_as_duplicate(self, request, queryset):
        """Mark selected invoices as duplicate"""
        updated = queryset.update(is_duplicate=True, status='duplicate')
        self.message_user(request, f'{updated} invoices marked as duplicate.')
    mark_as_duplicate.short_description = "Mark selected invoices as duplicate"


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    """
    Admin for InvoiceItem model
    """
    list_display = [
        'invoice', 'description', 'quantity', 'unit_price',
        'total_price', 'ai_confidence', 'created_at'
    ]
    list_filter = ['unit_of_measure', 'created_at']
    search_fields = ['description', 'product_code', 'invoice__invoice_number']
    ordering = ['-created_at']
    readonly_fields = ['total_price', 'ai_confidence', 'created_at', 'updated_at']

    fieldsets = (
        ('Invoice', {
            'fields': ('invoice',)
        }),
        ('Item Details', {
            'fields': ('description', 'quantity', 'unit_price', 'total_price')
        }),
        ('Additional Information', {
            'fields': ('product_code', 'unit_of_measure')
        }),
        ('AI Processing', {
            'fields': ('ai_confidence',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(InvoiceProcessingLog)
class InvoiceProcessingLogAdmin(admin.ModelAdmin):
    """
    Admin for InvoiceProcessingLog model
    """
    list_display = [
        'invoice', 'processing_step', 'status', 'started_at',
        'completed_at', 'duration_display', 'created_at'
    ]
    list_filter = ['processing_step', 'status', 'created_at']
    search_fields = ['invoice__invoice_number', 'processing_step', 'message']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Invoice', {
            'fields': ('invoice',)
        }),
        ('Processing Details', {
            'fields': ('processing_step', 'status', 'message')
        }),
        ('Data', {
            'fields': ('data',)
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration_ms')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    def duration_display(self, obj):
        """Display duration in a readable format"""
        if obj.duration_ms:
            if obj.duration_ms < 1000:
                return f"{obj.duration_ms}ms"
            else:
                return f"{obj.duration_ms / 1000:.2f}s"
        return "—"
    duration_display.short_description = 'Duration'
