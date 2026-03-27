from django import template

register = template.Library()


@register.filter
def usd(value):
    """Format a number as USD with commas."""
    try:
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return value


@register.filter
def percentage(value, total):
    """Calculate percentage of value relative to total."""
    try:
        if total == 0:
            return "0%"
        return f"{(value / total) * 100:.1f}%"
    except (ValueError, TypeError, ZeroDivisionError):
        return "0%"
