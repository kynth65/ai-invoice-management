#!/usr/bin/env python
"""
Simple test script to verify OpenAI integration
Run this after setting your OPENAI_API_KEY in .env file
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'invoice_management_system.settings')
django.setup()

from ai_processing.openai_service import OpenAIService


def test_openai_service():
    """Test OpenAI service with sample invoice data"""

    # Check if API key is configured
    from django.conf import settings
    if not settings.OPENAI_API_KEY:
        print("X OPENAI_API_KEY not found in .env file")
        print("* Please add your OpenAI API key to the .env file:")
        print("   OPENAI_API_KEY=sk-your-api-key-here")
        return False

    print("+ OpenAI API key found")

    # Sample invoice text for testing
    sample_invoice_text = """
    INVOICE #INV-2024-001

    From: TechCorp Solutions
    123 Business Ave
    San Francisco, CA 94105
    Email: billing@techcorp.com
    Phone: (555) 123-4567

    To: ABC Company

    Date: 2024-03-15
    Due Date: 2024-04-15

    Description: Monthly Software License

    Items:
    1. Professional Software License    1    $299.00    $299.00
    2. Technical Support Package       1    $99.00     $99.00

    Subtotal: $398.00
    Tax (8.5%): $33.83
    Total: $431.83

    Payment Terms: Net 30
    """

    try:
        # Initialize the service
        print(">> Initializing OpenAI service...")
        service = OpenAIService()

        # Test invoice data extraction
        print(">> Testing invoice data extraction...")
        result = service.extract_invoice_data(sample_invoice_text)

        print("+ Extraction successful!")
        print("+ Extracted data:")
        for key, value in result.items():
            print(f"   {key}: {value}")

        # Test categorization
        print("\n>> Testing invoice categorization...")
        category = service.categorize_invoice(
            vendor_name="TechCorp Solutions",
            description="Monthly Software License",
            items=result.get('items', [])
        )
        print(f"+ Category: {category}")

        print("\n+ All tests passed! OpenAI integration is working correctly.")
        return True

    except Exception as e:
        print(f"X Test failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing OpenAI Integration")
    print("=" * 50)

    success = test_openai_service()

    if success:
        print("\n+ OpenAI integration is ready to use!")
        print("* You can now upload invoices and use AI-powered data extraction.")
    else:
        print("\nX OpenAI integration needs configuration.")
        print("* Check the setup instructions above.")