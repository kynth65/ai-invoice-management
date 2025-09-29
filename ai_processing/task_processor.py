"""
AI Task Processor
Handles processing of AI tasks using OpenAI service
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

from django.utils import timezone
from django.conf import settings

from .models import AIProcessingTask
from .openai_service import OpenAIService
from invoices.models import Invoice

logger = logging.getLogger(__name__)


class AITaskProcessor:
    """
    Processes AI tasks using OpenAI service
    """

    def __init__(self):
        """Initialize the task processor"""
        self.openai_service = OpenAIService()

    def process_task(self, task: AIProcessingTask) -> bool:
        """
        Process a single AI task

        Args:
            task (AIProcessingTask): The task to process

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Processing task {task.id}: {task.task_type} for invoice {task.invoice.id}")

        # Update task status
        task.status = 'processing'
        task.started_at = timezone.now()
        task.ai_model_version = settings.OPENAI_MODEL
        task.save()

        start_time = time.time()

        try:
            # Process based on task type
            if task.task_type == 'data_extraction':
                success = self._process_data_extraction(task)
            elif task.task_type == 'duplicate_detection':
                success = self._process_duplicate_detection(task)
            else:
                logger.error(f"Unknown task type: {task.task_type}")
                success = False

            # Calculate processing duration
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)

            # Update task completion
            task.completed_at = timezone.now()
            task.processing_duration_ms = duration_ms

            if success:
                task.status = 'completed'
                logger.info(f"Task {task.id} completed successfully in {duration_ms}ms")
            else:
                task.status = 'failed'
                logger.error(f"Task {task.id} failed after {duration_ms}ms")

            task.save()
            return success

        except Exception as e:
            logger.error(f"Error processing task {task.id}: {e}")
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = timezone.now()
            task.save()
            return False

    def _process_data_extraction(self, task: AIProcessingTask) -> bool:
        """Process data extraction task"""
        try:
            invoice = task.invoice

            # Get text content from invoice file
            text_content = self._extract_text_from_invoice(invoice)

            if not text_content:
                task.error_message = "No text content found in invoice file"
                return False

            # Get existing vendors for better matching
            from invoices.models import Vendor
            existing_vendors = list(Vendor.objects.values_list('name', flat=True))

            # Extract data using OpenAI with vendor context
            extracted_data = self.openai_service.extract_invoice_data(
                text_content, existing_vendors=existing_vendors
            )

            # Update task output
            task.output_data = extracted_data
            task.confidence_score = extracted_data.get('confidence_score', 0.0)

            # Update invoice with extracted data and handle vendor creation
            self._update_invoice_with_extracted_data(invoice, extracted_data)

            return True

        except Exception as e:
            task.error_message = f"Data extraction failed: {e}"
            return False


    def _process_duplicate_detection(self, task: AIProcessingTask) -> bool:
        """Process duplicate detection task"""
        try:
            invoice = task.invoice

            # Get recent invoices for comparison
            recent_invoices = self._get_recent_invoices_for_comparison(invoice)

            # Prepare invoice data for comparison
            invoice_data = {
                'vendor_name': getattr(invoice.vendor, 'name', '') if invoice.vendor else '',
                'total_amount': float(invoice.total_amount) if invoice.total_amount else 0,
                'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                'invoice_number': invoice.invoice_number or ''
            }

            # Detect duplicates using OpenAI
            duplicate_result = self.openai_service.detect_duplicates(
                new_invoice_data=invoice_data,
                existing_invoices=recent_invoices
            )

            # Update task output
            task.output_data = duplicate_result
            task.confidence_score = duplicate_result.get('confidence', 0.0)

            # Log potential duplicates
            if duplicate_result.get('is_duplicate'):
                logger.warning(f"Potential duplicate detected for invoice {invoice.id}: {duplicate_result['reason']}")

            return True

        except Exception as e:
            task.error_message = f"Duplicate detection failed: {e}"
            return False

    def _extract_text_from_invoice(self, invoice: Invoice) -> str:
        """
        Extract text content from invoice file using the file processor
        """
        try:
            if invoice.original_file and invoice.original_file.path:
                # Use our file processor to extract text
                from invoices.file_processors import extract_text_from_file

                result = extract_text_from_file(invoice.original_file.path)

                if result.get('success'):
                    return result.get('text', '')
                else:
                    logger.error(f"Text extraction failed for invoice {invoice.id}: {result.get('error')}")

            # Fallback: return basic info if no file or extraction failed
            return f"""
            Invoice file: {invoice.original_file.name if invoice.original_file else 'No file'}
            File type: {invoice.file_type or 'Unknown'}
            Invoice number: {invoice.invoice_number or 'Unknown'}
            Total amount: {invoice.total_amount or 'Unknown'}
            Date: {invoice.invoice_date or 'Unknown'}
            Notes: {invoice.notes or 'No notes'}
            """

        except Exception as e:
            logger.error(f"Error extracting text from invoice {invoice.id}: {e}")
            return f"Error extracting text: {str(e)}"

    def _update_invoice_with_extracted_data(self, invoice: Invoice, data: Dict[str, Any]) -> None:
        """Update invoice with extracted data"""
        try:
            from invoices.models import Vendor

            logger.info(f"Updating invoice {invoice.id} with extracted data")
            logger.debug(f"Extracted data keys: {list(data.keys())}")
            logger.debug(f"Vendor name from data: '{data.get('vendor_name')}'")
            logger.debug(f"Current invoice vendor: {invoice.vendor}")

            # Handle vendor creation/assignment
            if data.get('vendor_name') and not invoice.vendor:
                vendor_name = data['vendor_name'].strip()
                logger.info(f"Processing vendor assignment for: '{vendor_name}'")
                if vendor_name:
                    # Try to find existing vendor first
                    vendor = self._find_or_create_vendor(vendor_name, data)
                    invoice.vendor = vendor
                    logger.info(f"Successfully assigned vendor '{vendor.name}' (ID: {vendor.id}) to invoice {invoice.id}")
                else:
                    logger.warning(f"Vendor name is empty after stripping for invoice {invoice.id}")
            elif not data.get('vendor_name'):
                logger.warning(f"No vendor_name found in extracted data for invoice {invoice.id}")
            elif invoice.vendor:
                logger.info(f"Invoice {invoice.id} already has vendor '{invoice.vendor.name}', skipping assignment")

            # Update basic fields
            if data.get('invoice_number') and not invoice.invoice_number:
                invoice.invoice_number = data['invoice_number']

            if data.get('invoice_date') and not invoice.invoice_date:
                try:
                    invoice.invoice_date = datetime.strptime(data['invoice_date'], '%Y-%m-%d').date()
                except ValueError:
                    pass

            if data.get('due_date') and not invoice.due_date:
                try:
                    invoice.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
                except ValueError:
                    pass

            if data.get('total_amount') and not invoice.total_amount:
                invoice.total_amount = data['total_amount']

            if data.get('subtotal') and not invoice.subtotal:
                invoice.subtotal = data['subtotal']

            if data.get('tax_amount') and not invoice.tax_amount:
                invoice.tax_amount = data['tax_amount']

            if data.get('currency'):
                invoice.currency = data['currency']

            if data.get('description') and not invoice.notes:
                invoice.notes = data['description']

            # Update AI extracted data field
            invoice.extracted_data = data

            # Update AI processing status fields
            invoice.ai_confidence_score = data.get('confidence_score', 0.0)
            invoice.is_ai_processed = True
            invoice.ai_processing_status = 'completed'
            invoice.status = 'processed'  # Move from pending to processed

            invoice.save()

            # Create invoice items if they don't exist
            self._create_invoice_items(invoice, data.get('items', []))

            logger.info(f"Updated invoice {invoice.id} with extracted data")

        except Exception as e:
            logger.error(f"Failed to update invoice {invoice.id}: {e}")

    def _find_or_create_vendor(self, vendor_name: str, extracted_data: Dict[str, Any]) -> 'Vendor':
        """Find existing vendor or create new one"""
        from invoices.models import Vendor

        logger.info(f"Finding or creating vendor: '{vendor_name}'")

        # Try exact match first
        try:
            vendor = Vendor.objects.get(name__iexact=vendor_name)
            logger.info(f"Found exact match for vendor: '{vendor.name}' (ID: {vendor.id})")
            return vendor
        except Vendor.DoesNotExist:
            logger.debug(f"No exact match found for: '{vendor_name}'")

        # Try partial match
        partial_vendors = Vendor.objects.filter(name__icontains=vendor_name)
        logger.debug(f"Partial match search for '{vendor_name}' returned {partial_vendors.count()} results")

        if partial_vendors.exists():
            vendor = partial_vendors.first()
            logger.info(f"Found partial match for vendor: '{vendor.name}' (ID: {vendor.id}) for search '{vendor_name}'")
            return vendor

        # Try reverse partial match (existing vendor name in search term)
        all_vendors = Vendor.objects.values_list('name', flat=True)
        for existing_vendor_name in all_vendors:
            if existing_vendor_name.lower() in vendor_name.lower() and len(existing_vendor_name) > 3:
                vendor = Vendor.objects.get(name=existing_vendor_name)
                logger.info(f"Found reverse partial match: '{vendor.name}' (ID: {vendor.id}) for search '{vendor_name}'")
                return vendor

        logger.info(f"No existing vendor found for '{vendor_name}', creating new vendor")

        # Create new vendor
        vendor_data = {
            'name': vendor_name,
            'email': extracted_data.get('vendor_email'),
            'phone': extracted_data.get('vendor_phone'),
            'address_line_1': extracted_data.get('vendor_address'),
            'is_ai_verified': True,
            'confidence_score': extracted_data.get('confidence_score', 0.0)
        }

        # Clean None values
        vendor_data = {k: v for k, v in vendor_data.items() if v is not None}

        vendor = Vendor.objects.create(**vendor_data)
        logger.info(f"Created new vendor: '{vendor.name}' (ID: {vendor.id})")
        return vendor

    def _create_invoice_items(self, invoice: Invoice, items_data: list) -> None:
        """Create invoice items from extracted data"""
        if not items_data or invoice.items.exists():
            return

        from invoices.models import InvoiceItem

        for item_data in items_data:
            if isinstance(item_data, dict) and item_data.get('description'):
                try:
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        description=item_data.get('description', 'Item'),
                        quantity=float(item_data.get('quantity', 1)),
                        unit_price=float(item_data.get('unit_price', 0)),
                        total_price=float(item_data.get('total', 0)),
                        ai_confidence=invoice.ai_confidence_score
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to create invoice item: {e}")
                    continue

        logger.info(f"Created {len(items_data)} items for invoice {invoice.id}")

    def _get_recent_invoices_for_comparison(self, invoice: Invoice) -> list:
        """Get recent invoices for duplicate comparison"""
        try:
            # Get recent invoices from the same user (last 30 days)
            from datetime import timedelta
            cutoff_date = timezone.now().date() - timedelta(days=30)

            recent_invoices = Invoice.objects.filter(
                user=invoice.user,
                created_at__date__gte=cutoff_date
            ).exclude(id=invoice.id)[:10]

            # Convert to list of dicts for comparison
            comparison_data = []
            for inv in recent_invoices:
                comparison_data.append({
                    'id': inv.id,
                    'vendor_name': getattr(inv.vendor, 'name', '') if inv.vendor else '',
                    'total_amount': float(inv.total_amount) if inv.total_amount else 0,
                    'invoice_date': inv.invoice_date.isoformat() if inv.invoice_date else None,
                    'invoice_number': inv.invoice_number or ''
                })

            return comparison_data

        except Exception as e:
            logger.error(f"Failed to get recent invoices: {e}")
            return []


def create_ai_task(invoice: Invoice, task_type: str, input_data: Optional[Dict] = None) -> AIProcessingTask:
    """
    Create a new AI processing task

    Args:
        invoice (Invoice): The invoice to process
        task_type (str): Type of AI task
        input_data (Dict, optional): Additional input data

    Returns:
        AIProcessingTask: Created task
    """
    task = AIProcessingTask.objects.create(
        invoice=invoice,
        task_type=task_type,
        input_data=input_data or {},
        status='pending'
    )

    logger.info(f"Created AI task {task.id}: {task_type} for invoice {invoice.id}")
    return task


def process_pending_tasks(max_tasks: int = 10) -> int:
    """
    Process pending AI tasks

    Args:
        max_tasks (int): Maximum number of tasks to process

    Returns:
        int: Number of tasks processed
    """
    processor = AITaskProcessor()
    pending_tasks = AIProcessingTask.objects.filter(status='pending')[:max_tasks]

    processed_count = 0
    for task in pending_tasks:
        try:
            processor.process_task(task)
            processed_count += 1
        except Exception as e:
            logger.error(f"Failed to process task {task.id}: {e}")

    logger.info(f"Processed {processed_count} AI tasks")
    return processed_count