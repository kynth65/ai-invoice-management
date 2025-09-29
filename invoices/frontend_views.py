from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import Invoice, Vendor, InvoiceItem
from .serializers import InvoiceCreateSerializer
from .file_processors import validate_uploaded_file, extract_text_from_file
from analytics.models import UserDashboardMetrics
from ai_processing.models import AIProcessingTask


def login_view(request):
    """
    Custom login view
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                # Redirect to next parameter or home
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AuthenticationForm()

    return render(request, 'invoices/login.html', {'form': form})


def logout_view(request):
    """
    Logout view
    """
    if request.user.is_authenticated:
        username = request.user.first_name or request.user.username
        logout(request)
        messages.info(request, f'You have been logged out successfully. Goodbye, {username}!')
    return redirect('login')


@login_required
def home_view(request):
    """
    Main dashboard view
    """
    context = {
        'page_title': 'Invoice Management Dashboard',
        'show_upload': True
    }

    if request.user.is_authenticated:
        # Get user's recent invoices
        recent_invoices = Invoice.objects.filter(user=request.user).order_by('-created_at')[:5]

        # Get dashboard stats
        total_invoices = Invoice.objects.filter(user=request.user).count()
        total_amount = Invoice.objects.filter(user=request.user).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')

        pending_invoices = Invoice.objects.filter(user=request.user, status='pending').count()

        # Current month stats
        now = timezone.now()
        current_month = now.replace(day=1)
        current_month_total = Invoice.objects.filter(
            user=request.user,
            created_at__gte=current_month
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        context.update({
            'recent_invoices': recent_invoices,
            'total_invoices': total_invoices,
            'total_amount': total_amount,
            'pending_invoices': pending_invoices,
            'current_month_total': current_month_total,
            'user_authenticated': True
        })

    return render(request, 'invoices/dashboard.html', context)


@login_required
def upload_view(request):
    """
    Invoice upload view
    """
    if request.method == 'GET':
        return render(request, 'invoices/upload.html', {
            'page_title': 'Upload Invoice'
        })

    # Handle file upload
    if request.method == 'POST':
        uploaded_file = request.FILES.get('invoice_file')

        if not uploaded_file:
            messages.error(request, 'Please select a file to upload.')
            return render(request, 'invoices/upload.html')

        # Validate file type
        validation_result = validate_uploaded_file(uploaded_file.name)
        if not validation_result['valid']:
            messages.error(request, validation_result['error'])
            return render(request, 'invoices/upload.html')

        # Get file extension and type
        import os
        _, file_ext = os.path.splitext(uploaded_file.name.lower())
        file_type_map = {'.pdf': 'pdf', '.docx': 'docx', '.txt': 'txt'}
        file_type = file_type_map.get(file_ext, 'unknown')

        # Create invoice
        try:
            invoice = Invoice.objects.create(
                user=request.user,
                original_file=uploaded_file,
                file_type=file_type,
                file_size=uploaded_file.size,
                status='pending'
            )

            # Create AI processing task
            AIProcessingTask.objects.create(
                invoice=invoice,
                task_type='data_extraction',
                status='pending'
            )

            # Trigger immediate processing (optional - comment out for manual processing)
            try:
                from ai_processing.task_processor import process_pending_tasks
                process_pending_tasks(max_tasks=1)
                messages.success(request, f'Invoice uploaded and processed successfully!')
            except Exception as e:
                messages.success(request, f'Invoice uploaded successfully! Processing queued.')

            return redirect('invoice_detail', pk=invoice.pk)

        except Exception as e:
            messages.error(request, f'Error uploading invoice: {str(e)}')
            return render(request, 'invoices/upload.html')


@login_required
def invoice_list_view(request):
    """
    List all invoices for the user
    """
    invoices = Invoice.objects.filter(user=request.user).order_by('-created_at')

    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        invoices = invoices.filter(status=status_filter)

    # Filter by period if provided
    period_filter = request.GET.get('period')
    if period_filter:
        now = timezone.now()
        if period_filter == 'today':
            # Start of today
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            # End of today
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            invoices = invoices.filter(created_at__gte=start_date, created_at__lte=end_date)
        elif period_filter == 'week':
            # Get start of current week (Monday)
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            # End of current week (Sunday)
            end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
            invoices = invoices.filter(created_at__gte=start_date, created_at__lte=end_date)
        elif period_filter == 'month':
            # Start of current month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # End of current month
            if now.month == 12:
                end_date = now.replace(year=now.year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
            else:
                end_date = now.replace(month=now.month+1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
            invoices = invoices.filter(created_at__gte=start_date, created_at__lte=end_date)
        elif period_filter == 'quarter':
            # Get start of current quarter
            quarter = (now.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            start_date = now.replace(month=start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            # End of current quarter
            end_month = start_month + 2
            if end_month > 12:
                end_date = now.replace(year=now.year+1, month=end_month-12, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
            else:
                if end_month == 12:
                    end_date = now.replace(year=now.year+1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
                else:
                    end_date = now.replace(month=end_month+1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
            invoices = invoices.filter(created_at__gte=start_date, created_at__lte=end_date)

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(vendor__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    # Calculate summary statistics for displayed invoices
    displayed_total = invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    pending_count = invoices.filter(status='pending').count()
    paid_count = invoices.filter(status='paid').count()

    context = {
        'invoices': invoices,
        'page_title': 'All Invoices',
        'status_filter': status_filter,
        'period_filter': period_filter,
        'search_query': search_query,
        'status_choices': Invoice.STATUS_CHOICES,
        'displayed_total': displayed_total,
        'pending_count': pending_count,
        'paid_count': paid_count,
    }

    return render(request, 'invoices/invoice_list.html', context)


@login_required
def invoice_detail_view(request, pk):
    """
    View individual invoice details
    """
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)

    context = {
        'invoice': invoice,
        'page_title': f'Invoice {invoice.invoice_number or invoice.id}',
        'items': invoice.items.all(),
        'processing_logs': invoice.processing_logs.all().order_by('-created_at')
    }

    return render(request, 'invoices/invoice_detail.html', context)


@login_required
def analytics_view(request):
    """
    Analytics dashboard view
    """
    # Get time period from query params
    period = request.GET.get('period', 'monthly')
    user = request.user

    # Basic stats
    total_invoices = Invoice.objects.filter(user=user).count()
    total_amount = Invoice.objects.filter(user=user).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')

    # Monthly data for charts
    now = timezone.now()
    months_data = []

    for i in range(6):  # Last 6 months
        month_start = (now.replace(day=1) - timedelta(days=32*i)).replace(day=1)
        month_end = (month_start.replace(month=month_start.month+1) if month_start.month < 12
                    else month_start.replace(year=month_start.year+1, month=1))

        month_invoices = Invoice.objects.filter(
            user=user,
            created_at__gte=month_start,
            created_at__lt=month_end
        )

        month_total = month_invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        month_count = month_invoices.count()

        months_data.append({
            'month': month_start.strftime('%b %Y'),
            'total': float(month_total),
            'count': month_count
        })

    months_data.reverse()  # Show chronological order

    # Vendor breakdown
    vendor_data = list(Invoice.objects.filter(user=user).values(
        'vendor__name'
    ).annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total')[:5])

    context = {
        'page_title': 'Analytics Dashboard',
        'total_invoices': total_invoices,
        'total_amount': total_amount,
        'months_data': json.dumps(months_data),
        'vendor_data': vendor_data,
        'period': period,
        'user_authenticated': True
    }

    return render(request, 'invoices/analytics.html', context)


@method_decorator([csrf_exempt, login_required], name='dispatch')
class QuickUploadView(View):
    """
    AJAX file upload view
    """
    def post(self, request):
        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            return JsonResponse({'error': 'No file provided'}, status=400)

        if not uploaded_file.name.lower().endswith('.pdf'):
            return JsonResponse({'error': 'Only PDF files are allowed'}, status=400)

        try:
            invoice = Invoice.objects.create(
                user=request.user,
                original_file=uploaded_file,
                file_type='pdf',
                file_size=uploaded_file.size,
                status='pending'
            )

            # Create AI processing task
            AIProcessingTask.objects.create(
                invoice=invoice,
                task_type='data_extraction',
                status='pending'
            )

            return JsonResponse({
                'success': True,
                'invoice_id': invoice.id,
                'message': 'Invoice uploaded successfully!'
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)