from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return value * arg
    except (TypeError, ValueError):
        return 0

@register.filter
def divide(value, arg):
    """Divide the value by the argument"""
    try:
        return value / arg
    except (TypeError, ValueError, ZeroDivisionError):
        return 0

@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return value - arg
    except (TypeError, ValueError):
        return value
