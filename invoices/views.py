from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Vendor, Invoice, InvoiceItem, InvoiceProcessingLog
from .serializers import (
    VendorSerializer, InvoiceSerializer, InvoiceCreateSerializer,
    InvoiceListSerializer, InvoiceItemSerializer, InvoiceProcessingLogSerializer,
    InvoiceStatsSerializer
)
from .file_processors import get_supported_file_types




class VendorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vendor operations
    """
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'email', 'city', 'country']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=False, methods=['get'])
    def top_vendors(self, request):
        """
        Get top vendors by invoice count and total amount
        """
        vendors = Vendor.objects.annotate(
            invoice_count=Count('invoices'),
            total_amount=Sum('invoices__total_amount')
        ).filter(invoice_count__gt=0).order_by('-total_amount')[:10]

        data = []
        for vendor in vendors:
            data.append({
                'id': vendor.id,
                'name': vendor.name,
                'invoice_count': vendor.invoice_count,
                'total_amount': vendor.total_amount or 0
            })

        return Response(data)


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Invoice operations
    """
    queryset = Invoice.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'vendor', 'is_duplicate']
    search_fields = ['invoice_number', 'vendor__name', 'notes']
    ordering_fields = ['created_at', 'invoice_date', 'total_amount']
    ordering = ['-created_at']

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        elif self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceSerializer

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get invoice statistics for the current user
        """
        queryset = self.get_queryset()
        now = timezone.now()
        current_month = now.replace(day=1)

        # Basic stats
        total_invoices = queryset.count()
        total_amount = queryset.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        pending_invoices = queryset.filter(status='pending').count()
        processed_invoices = queryset.filter(status__in=['processed', 'approved', 'paid']).count()

        # This month stats
        this_month_invoices = queryset.filter(created_at__gte=current_month)
        this_month_total = this_month_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        this_month_count = this_month_invoices.count()

        # Processing time
        processed_invoices_with_time = queryset.filter(
            processed_at__isnull=False
        ).annotate(
            processing_time=timezone.now() - timezone.now()  # This would need proper calculation
        )
        avg_processing_time = 0  # Placeholder

        # Top vendors
        top_vendors = list(queryset.values('vendor__name').annotate(
            total=Sum('total_amount'), count=Count('id')
        ).order_by('-total')[:5])

        stats_data = {
            'total_invoices': total_invoices,
            'total_amount': total_amount,
            'pending_invoices': pending_invoices,
            'processed_invoices': processed_invoices,
            'this_month_total': this_month_total,
            'this_month_count': this_month_count,
            'avg_processing_time': avg_processing_time,
            'top_vendors': top_vendors
        }

        serializer = InvoiceStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """
        Mark invoice as paid
        """
        invoice = self.get_object()
        invoice.status = 'paid'
        invoice.processed_at = timezone.now()
        invoice.save()
        return Response({'message': 'Invoice marked as paid'})

    @action(detail=True, methods=['post'])
    def mark_as_duplicate(self, request, pk=None):
        """
        Mark invoice as duplicate
        """
        invoice = self.get_object()
        duplicate_of_id = request.data.get('duplicate_of')

        if duplicate_of_id:
            try:
                duplicate_of = Invoice.objects.get(id=duplicate_of_id, user=request.user)
                invoice.duplicate_of = duplicate_of
            except Invoice.DoesNotExist:
                return Response(
                    {'error': 'Invalid duplicate_of invoice ID'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        invoice.is_duplicate = True
        invoice.status = 'duplicate'
        invoice.save()
        return Response({'message': 'Invoice marked as duplicate'})

    def destroy(self, request, *args, **kwargs):
        """
        Delete an invoice (override to add custom logic if needed)
        """
        try:
            invoice = self.get_object()
            invoice_id = invoice.id
            invoice_number = invoice.invoice_number or f"#{invoice_id}"

            # Check if user has permission to delete this invoice
            if invoice.user != request.user:
                return Response(
                    {'error': 'You do not have permission to delete this invoice'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Delete the invoice (this will also delete related items due to CASCADE)
            self.perform_destroy(invoice)

            return Response({
                'message': f'Invoice {invoice_number} has been successfully deleted',
                'deleted_id': invoice_id
            }, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response(
                {'error': f'Failed to delete invoice: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recent invoices (last 30 days)
        """
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_invoices = self.get_queryset().filter(created_at__gte=thirty_days_ago)
        serializer = InvoiceListSerializer(recent_invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Get pending invoices
        """
        pending_invoices = self.get_queryset().filter(status='pending')
        serializer = InvoiceListSerializer(pending_invoices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def supported_file_types(self, request):
        """
        Get list of supported file types for upload
        """
        supported_types = get_supported_file_types()

        # Format for frontend consumption
        formatted_types = []
        for extension, description in supported_types.items():
            formatted_types.append({
                'extension': extension,
                'description': description,
                'accept': extension  # For HTML input accept attribute
            })

        return Response({
            'supported_types': formatted_types,
            'accept_string': ','.join(supported_types.keys()),  # For HTML input accept
            'max_file_size_mb': 10  # 10MB limit
        })


class InvoiceItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for InvoiceItem operations
    """
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InvoiceItem.objects.filter(invoice__user=self.request.user)


class InvoiceProcessingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for InvoiceProcessingLog (read-only)
    """
    queryset = InvoiceProcessingLog.objects.all()
    serializer_class = InvoiceProcessingLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InvoiceProcessingLog.objects.filter(invoice__user=self.request.user)
