"""
OpenAI Service for Invoice Processing
Handles AI-powered invoice data extraction and analysis
"""

import json
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

import openai
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class OpenAIService:
    """
    Service class for OpenAI API integration
    """

    def __init__(self):
        """Initialize OpenAI client with API key from settings"""
        if not settings.OPENAI_API_KEY:
            raise ImproperlyConfigured(
                "OPENAI_API_KEY is required. Please set it in your .env file."
            )

        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE

    def extract_invoice_data(self, text_content: str, existing_vendors: list = None) -> Dict[str, Any]:
        """
        Extract structured data from invoice text using OpenAI

        Args:
            text_content (str): Raw text extracted from invoice PDF
            existing_vendors (list): List of existing vendor names for reference

        Returns:
            Dict[str, Any]: Structured invoice data
        """
        try:
            prompt = self._create_extraction_prompt(text_content, existing_vendors)

            logger.info(f"Starting OpenAI extraction for text length: {len(text_content)} chars")
            logger.debug(f"Text content preview: {text_content[:200]}...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert invoice data extraction assistant. Extract accurate financial data from invoices and return valid JSON. ALWAYS extract the vendor/company name from the invoice header - this is critical."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )

            # Log the raw response for debugging
            raw_response = response.choices[0].message.content
            logger.debug(f"OpenAI raw response: {raw_response}")

            # Parse the response
            result = json.loads(raw_response)
            logger.info(f"Successfully parsed OpenAI response. Vendor extracted: {result.get('vendor_name')}")

            # Validate and clean the extracted data
            cleaned_data = self._validate_and_clean_data(result)

            # Normalize vendor name if existing vendors provided
            if existing_vendors and cleaned_data.get('vendor_name'):
                original_vendor = cleaned_data['vendor_name']
                cleaned_data['vendor_name'] = self._normalize_vendor_name(
                    cleaned_data['vendor_name'], existing_vendors
                )
                logger.info(f"Vendor normalized: '{original_vendor}' -> '{cleaned_data['vendor_name']}'")

            logger.info(f"Successfully extracted invoice data using {self.model}. Final vendor: {cleaned_data.get('vendor_name')}")
            return cleaned_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            logger.error(f"Raw response was: {response.choices[0].message.content if 'response' in locals() else 'No response'}")
            return self._get_default_response()

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return self._get_default_response()


    def detect_duplicates(self, new_invoice_data: Dict[str, Any], existing_invoices: list) -> Dict[str, Any]:
        """
        Detect potential duplicate invoices

        Args:
            new_invoice_data (Dict): New invoice data
            existing_invoices (list): List of existing invoice data

        Returns:
            Dict[str, Any]: Duplicate detection results
        """
        try:
            prompt = f"""
            Analyze if this new invoice is a duplicate of any existing invoices.

            New Invoice:
            - Vendor: {new_invoice_data.get('vendor_name', 'N/A')}
            - Amount: {new_invoice_data.get('total_amount', 'N/A')}
            - Date: {new_invoice_data.get('invoice_date', 'N/A')}
            - Invoice Number: {new_invoice_data.get('invoice_number', 'N/A')}

            Existing Invoices:
            {json.dumps(existing_invoices, indent=2)}

            Return JSON with:
            {{
                "is_duplicate": boolean,
                "confidence": float (0.0 to 1.0),
                "matching_invoice_id": int or null,
                "reason": "explanation of why it's considered duplicate or not"
            }}
            """

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at detecting duplicate invoices. Return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=200,
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            logger.info(f"Duplicate detection completed with confidence: {result.get('confidence', 0)}")
            return result

        except Exception as e:
            logger.error(f"Failed to detect duplicates: {e}")
            return {
                "is_duplicate": False,
                "confidence": 0.0,
                "matching_invoice_id": None,
                "reason": "Analysis failed"
            }

    def _create_extraction_prompt(self, text_content: str, existing_vendors: list = None) -> str:
        """Create a structured prompt for invoice data extraction"""
        vendor_guidance = ""
        if existing_vendors:
            vendor_guidance = f"""

        EXISTING VENDORS (use exact match if possible):
        {chr(10).join([f'- {vendor}' for vendor in existing_vendors[:20]])}

        For vendor_name, try to match one of the existing vendors above if the invoice is from them.
        """

        return f"""
        Extract the following information from this invoice text and return it as valid JSON:

        {{
            "invoice_number": "string or null",
            "invoice_date": "YYYY-MM-DD format or null",
            "due_date": "YYYY-MM-DD format or null",
            "vendor_name": "string or null",
            "vendor_address": "string or null",
            "vendor_email": "string or null",
            "vendor_phone": "string or null",
            "total_amount": "decimal number or null",
            "subtotal": "decimal number or null",
            "tax_amount": "decimal number or null",
            "currency": "string (default USD)",
            "description": "string or null",
            "items": [
                {{
                    "description": "string",
                    "quantity": "number",
                    "unit_price": "decimal",
                    "total": "decimal"
                }}
            ],
            "confidence_score": "float between 0.0 and 1.0"
        }}
        {vendor_guidance}

        Invoice Text:
        {text_content}

        CRITICAL EXTRACTION RULES:
        - ALWAYS extract the vendor_name from the invoice header/top of the document
        - The vendor_name is typically the first company name, business name, or organization name that appears
        - Look for company names in the letterhead, header, or first few lines
        - Common patterns: "COMPANY NAME", "Company Name", "Company Name Inc.", etc.
        - If multiple company names appear, the vendor is usually the one issuing the invoice (at the top)
        - Return valid JSON only
        - Use null for missing information
        - Ensure dates are in YYYY-MM-DD format
        - Ensure amounts are decimal numbers
        - Include confidence score based on text clarity
        - For vendor_name, use the full official company name (e.g., "Microsoft Corporation" not "Microsoft")

        Examples of vendor extraction:
        - If text starts with "GARCIA & ASSOCIATES LAW FIRM", vendor_name should be "GARCIA & ASSOCIATES LAW FIRM"
        - If text starts with "Microsoft Corporation", vendor_name should be "Microsoft Corporation"
        - If text starts with "MERALCO", vendor_name should be "MERALCO"
        """

    def _validate_and_clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean extracted data"""
        cleaned = {}

        # String fields
        string_fields = ['invoice_number', 'vendor_name', 'vendor_address',
                        'vendor_email', 'vendor_phone', 'description', 'currency']
        for field in string_fields:
            value = data.get(field)
            cleaned[field] = str(value).strip() if value and str(value).strip() else None

        # Date fields
        date_fields = ['invoice_date', 'due_date']
        for field in date_fields:
            value = data.get(field)
            if value:
                try:
                    # Validate date format
                    datetime.strptime(value, '%Y-%m-%d')
                    cleaned[field] = value
                except ValueError:
                    cleaned[field] = None
            else:
                cleaned[field] = None

        # Decimal fields
        decimal_fields = ['total_amount', 'subtotal', 'tax_amount']
        for field in decimal_fields:
            value = data.get(field)
            if value is not None:
                try:
                    cleaned[field] = float(value)
                except (ValueError, TypeError):
                    cleaned[field] = None
            else:
                cleaned[field] = None

        # Currency default
        cleaned['currency'] = cleaned.get('currency') or 'USD'

        # Items array
        items = data.get('items', [])
        cleaned_items = []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    cleaned_item = {
                        'description': str(item.get('description', '')).strip() or 'Item',
                        'quantity': float(item.get('quantity', 1)) if item.get('quantity') else 1,
                        'unit_price': float(item.get('unit_price', 0)) if item.get('unit_price') else 0,
                        'total': float(item.get('total', 0)) if item.get('total') else 0
                    }
                    cleaned_items.append(cleaned_item)
        cleaned['items'] = cleaned_items

        # Confidence score
        confidence = data.get('confidence_score', 0.5)
        try:
            cleaned['confidence_score'] = max(0.0, min(1.0, float(confidence)))
        except (ValueError, TypeError):
            cleaned['confidence_score'] = 0.5

        return cleaned

    def _normalize_vendor_name(self, extracted_vendor: str, existing_vendors: list) -> str:
        """
        Normalize vendor name by finding the best match from existing vendors

        Args:
            extracted_vendor (str): Vendor name extracted from invoice
            existing_vendors (list): List of existing vendor names

        Returns:
            str: Normalized vendor name
        """
        if not extracted_vendor or not existing_vendors:
            return extracted_vendor

        extracted_lower = extracted_vendor.lower().strip()

        # Exact match first
        for vendor in existing_vendors:
            if vendor.lower() == extracted_lower:
                return vendor

        # Partial match - check if extracted name is contained in existing or vice versa
        for vendor in existing_vendors:
            vendor_lower = vendor.lower()
            # Check if the extracted name contains the existing vendor name or vice versa
            if (extracted_lower in vendor_lower and len(extracted_lower) > 3) or \
               (vendor_lower in extracted_lower and len(vendor_lower) > 3):
                return vendor

        # Check for common company suffixes and abbreviations
        extracted_clean = self._clean_company_name(extracted_lower)
        for vendor in existing_vendors:
            vendor_clean = self._clean_company_name(vendor.lower())
            if extracted_clean == vendor_clean:
                return vendor

        # No match found, return original
        return extracted_vendor

    def _clean_company_name(self, name: str) -> str:
        """Clean company name by removing common suffixes and normalizing"""
        suffixes = [
            'inc', 'inc.', 'corporation', 'corp', 'corp.', 'llc', 'ltd', 'ltd.',
            'limited', 'co', 'co.', 'company', 'technologies', 'tech', 'systems'
        ]

        name = name.strip().lower()
        for suffix in suffixes:
            if name.endswith(f' {suffix}'):
                name = name[:-len(suffix)-1].strip()
                break

        return name

    def _get_default_response(self) -> Dict[str, Any]:
        """Return default response when extraction fails"""
        return {
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "vendor_name": None,
            "vendor_address": None,
            "vendor_email": None,
            "vendor_phone": None,
            "total_amount": None,
            "subtotal": None,
            "tax_amount": None,
            "currency": "USD",
            "description": None,
            "items": [],
            "confidence_score": 0.0
        }