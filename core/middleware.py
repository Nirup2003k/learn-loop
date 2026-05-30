import zoneinfo
from django.utils import timezone

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            tzname = request.user.profile.timezone
            if tzname:
                try:
                    timezone.activate(zoneinfo.ZoneInfo(tzname))
                except Exception:
                    timezone.deactivate()
            else:
                timezone.deactivate()
        else:
            timezone.deactivate()
            
        return self.get_response(request)
