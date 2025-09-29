from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def sum_amounts(invoices):
    """Calculate the sum of total_amount for a list of invoices"""
    total = Decimal('0.00')
    for invoice in invoices:
        if invoice.total_amount:
            total += invoice.total_amount
    return total

@register.filter
def format_currency(amount):
    """Format a currency amount for display with proper precision"""
    if not amount:
        return '0'

    amount = float(amount)

    # Always show the actual amount with commas for readability
    if amount >= 1000:
        return f"{amount:,.2f}".rstrip('0').rstrip('.')
    else:
        return f"{amount:.2f}".rstrip('0').rstrip('.')

@register.filter
def length_by_status(invoices, status):
    """Count invoices by status"""
    count = 0
    for invoice in invoices:
        if invoice.status == status:
            count += 1
    return count