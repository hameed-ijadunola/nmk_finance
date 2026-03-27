from django.conf import settings


def site_context(request):
    """Inject site-wide variables into every template."""
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "NMK Community Finance"),
    }
