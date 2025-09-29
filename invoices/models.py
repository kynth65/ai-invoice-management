from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal



class Vendor(models.Model):
    """
    Vendor/Supplier information
    """
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    # Address information
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Business information
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    business_registration = models.CharField(max_length=100, blank=True, null=True)

    # AI-extracted information
    is_ai_verified = models.BooleanField(default=False)
    confidence_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vendors'
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def full_address(self):
        address_parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ', '.join([part for part in address_parts if part])


class Invoice(models.Model):
    """
    Main invoice model
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
        ('duplicate', 'Duplicate'),
    ]

    # Basic information
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoices')
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')

    # Invoice details
    invoice_number = models.CharField(max_length=100, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    # Financial information
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='USD')

    # File information
    original_file = models.FileField(upload_to='invoices/originals/%Y/%m/')
    file_type = models.CharField(max_length=10)  # pdf, jpg, png, etc.
    file_size = models.PositiveIntegerField(default=0)  # in bytes

    # AI processing information
    extracted_data = models.JSONField(default=dict, blank=True)
    ai_confidence_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])
    is_ai_processed = models.BooleanField(default=False)
    ai_processing_status = models.CharField(max_length=20, default='pending')  # pending, processing, completed, failed

    # Status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='duplicates')

    # Notes and metadata
    notes = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True)  # Comma-separated tags
    ai_summary = models.TextField(blank=True)  # AI-generated summary

    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'invoices'
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['vendor', 'invoice_date']),
            models.Index(fields=['invoice_date']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number or self.id} - {self.vendor or 'Unknown Vendor'}"

    @property
    def is_overdue(self):
        if self.due_date and self.status not in ['paid', 'rejected']:
            from django.utils import timezone
            return timezone.now().date() > self.due_date
        return False


class InvoiceItem(models.Model):
    """
    Individual line items within an invoice
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')

    # Item details
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Additional information
    product_code = models.CharField(max_length=100, blank=True)
    unit_of_measure = models.CharField(max_length=20, blank=True)  # pcs, kg, hours, etc.

    # AI extraction confidence
    ai_confidence = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoice_items'
        verbose_name = 'Invoice Item'
        verbose_name_plural = 'Invoice Items'
        ordering = ['id']

    def __str__(self):
        return f"{self.description} ({self.quantity} x {self.unit_price})"

    def save(self, *args, **kwargs):
        # Auto-calculate total price
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class InvoiceProcessingLog(models.Model):
    """
    Log of AI processing attempts and results
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='processing_logs')

    # Processing details
    processing_step = models.CharField(max_length=50)  # extraction, categorization, duplicate_check, etc.
    status = models.CharField(max_length=20)  # success, failed, warning
    message = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)  # Additional processing data

    # Timing
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invoice_processing_logs'
        verbose_name = 'Processing Log'
        verbose_name_plural = 'Processing Logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice} - {self.processing_step} ({self.status})"
