from django.conf import settings


def settings_context(request):
    """
    Add selected settings to template context
    """
    return {
        'settings': {
            'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
            'DEFAULT_MAP_CENTER_LAT': settings.DEFAULT_MAP_CENTER_LAT,
            'DEFAULT_MAP_CENTER_LNG': settings.DEFAULT_MAP_CENTER_LNG,
            'DEFAULT_MAP_ZOOM': settings.DEFAULT_MAP_ZOOM,
        },
        'FIREBASE_CONFIG': settings.FIREBASE_CONFIG,
        'VAPID_KEY': settings.VAPID_KEY,
    }