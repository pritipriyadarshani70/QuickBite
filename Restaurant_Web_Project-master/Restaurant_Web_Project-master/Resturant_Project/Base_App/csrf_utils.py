from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# Apply csrf_exempt to all views that handle POST requests
def csrf_exempt_all(view_func):
    """Decorator to exempt all views from CSRF protection"""
    return csrf_exempt(view_func)
