from .models import SiteVisitor

_SKIP = ("/admin/", "/static/", "/media/", "/favicon")


class VisitorCounterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not any(request.path.startswith(p) for p in _SKIP):
            SiteVisitor.record(request)
        return self.get_response(request)
