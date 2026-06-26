from .models import SiteVisitor

_SKIP = ("/admin/", "/static/", "/media/", "/favicon")

_BOT_KEYWORDS = (
    "bot", "crawler", "spider", "slurp", "curl", "wget",
    "python-requests", "scrapy", "headless", "phantom",
)


def _is_bot(request):
    ua = request.META.get("HTTP_USER_AGENT", "").lower()
    return not ua or any(kw in ua for kw in _BOT_KEYWORDS)


class VisitorCounterMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not any(request.path.startswith(p) for p in _SKIP) and not _is_bot(request):
            SiteVisitor.record(request)
        return self.get_response(request)