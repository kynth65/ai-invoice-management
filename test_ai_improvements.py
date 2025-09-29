#!/usr/bin/env python
"""
Test script to demonstrate AI processing improvements for vendor and category recognition
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invoice_management_system.settings')
django.setup()

from ai_processing.openai_service import OpenAIService
from invoices.models import Vendor, Category


def test_vendor_normalization():
    """Test vendor name normalization"""
    print("Testing Vendor Normalization...")

    service = OpenAIService()
    existing_vendors = ['Microsoft Corporation', 'Adobe Inc.', 'Google LLC', 'Amazon Web Services']

    test_cases = [
        'Microsoft Corp',
        'microsoft corporation',
        'Adobe',
        'Google',
        'Amazon AWS',
        'Apple Inc.',  # New vendor
        'MSFT'  # No match
    ]

    for test_vendor in test_cases:
        normalized = service._normalize_vendor_name(test_vendor, existing_vendors)
        print(f"  '{test_vendor}' -> '{normalized}'")

    print()


def test_category_optimization():
    """Test improved categorization"""
    print("Testing Category Optimization...")

    service = OpenAIService()
    existing_categories = [
        'Office Supplies', 'Software & Subscriptions', 'Marketing & Advertising',
        'Travel & Transportation', 'Utilities', 'Professional Services',
        'Equipment & Hardware', 'Maintenance & Repairs'
    ]

    test_cases = [
        {
            'vendor': 'Microsoft Corporation',
            'description': 'Office 365 subscription',
            'items': ['Office 365 Business Premium - Monthly']
        },
        {
            'vendor': 'Office Depot Inc.',
            'description': 'Office supplies purchase',
            'items': ['Paper', 'Pens', 'Staplers']
        },
        {
            'vendor': 'Delta Airlines',
            'description': 'Business travel',
            'items': ['Flight ticket NYC to LAX']
        },
        {
            'vendor': 'Unknown Vendor',
            'description': 'Computer repair service',
            'items': ['Laptop screen replacement']
        }
    ]

    for test_case in test_cases:
        category = service.categorize_invoice(
            vendor_name=test_case['vendor'],
            description=test_case['description'],
            items=test_case['items'],
            existing_categories=existing_categories
        )
        print(f"  {test_case['vendor']}: '{test_case['description']}' -> {category}")

    print()


def test_extraction_with_context():
    """Test data extraction with vendor context"""
    print("Testing Enhanced Data Extraction...")

    service = OpenAIService()
    existing_vendors = list(Vendor.objects.values_list('name', flat=True))

    # Mock invoice text
    sample_text = """
    INVOICE

    Microsoft Corporation
    One Microsoft Way
    Redmond, WA 98052

    Invoice #: INV-2024-001
    Date: 2024-01-15
    Due: 2024-02-14

    Bill To:
    Your Company
    123 Business St

    Description: Office 365 Business Premium - Monthly Subscription
    Quantity: 10
    Rate: $22.00
    Total: $220.00

    Subtotal: $220.00
    Tax: $22.00
    Total: $242.00
    """

    print(f"  Available vendors: {len(existing_vendors)}")
    print(f"  Sample vendors: {existing_vendors[:3]}...")

    # Test without vendor context
    print("\n  Without vendor context:")
    result_without = service.extract_invoice_data(sample_text)
    print(f"    Extracted vendor: '{result_without.get('vendor_name')}'")

    # Test with vendor context
    print("\n  With vendor context:")
    result_with = service.extract_invoice_data(sample_text, existing_vendors)
    print(f"    Extracted vendor: '{result_with.get('vendor_name')}'")
    print(f"    Confidence: {result_with.get('confidence_score', 0):.2f}")

    print()


def demonstrate_improvements():
    """Demonstrate all improvements"""
    print("AI Processing Optimization Demonstration")
    print("=" * 50)

    # Show current database state
    print("Current Database State:")
    print(f"  Vendors: {Vendor.objects.count()}")
    print(f"  Categories: {Category.objects.count()}")
    print()

    # Test individual components
    test_vendor_normalization()
    test_category_optimization()
    test_extraction_with_context()

    print("Key Improvements Made:")
    print("  1. Enhanced vendor name normalization with fuzzy matching")
    print("  2. Improved categorization using existing categories as context")
    print("  3. Automatic vendor creation with extracted details")
    print("  4. Category assignment to invoices (not just text)")
    print("  5. Better extraction prompts with vendor context")
    print("  6. Invoice item creation from extracted data")
    print()

    print("Benefits:")
    print("  * Better vendor recognition and deduplication")
    print("  * More accurate categorization using existing taxonomy")
    print("  * Automatic creation of missing vendors and categories")
    print("  * Improved data consistency and quality")
    print("  * Enhanced AI confidence through better context")


if __name__ == '__main__':
    try:
        demonstrate_improvements()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()