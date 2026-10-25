"""HMAC request signing shared with the ISI app (see ISI ``sync/transport.py``).

signature = HMAC-SHA256(secret, f"{timestamp}\\n{METHOD}\\n{path_with_query}\\n" + body)
headers   = X-Sync-Timestamp (unix seconds), X-Sync-Signature (hex)
"""

import hashlib
import hmac
import time
from functools import wraps

from django.conf import settings
from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt

MAX_SKEW_SECONDS = 300


def secret() -> str:
    return getattr(settings, "SYNC_SHARED_SECRET", "") or ""


def sign(key: str, timestamp: str, method: str, path: str, body: bytes) -> str:
    msg = f"{timestamp}\n{method.upper()}\n{path}\n".encode() + (body or b"")
    return hmac.new(key.encode(), msg, hashlib.sha256).hexdigest()


def signed_endpoint(view):
    """Only accept requests correctly signed with SYNC_SHARED_SECRET.
    An unset secret disables the whole bridge (404, like a missing route)."""

    @csrf_exempt
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        key = secret()
        if not key:
            raise Http404()
        ts = request.headers.get("X-Sync-Timestamp", "")
        sig = request.headers.get("X-Sync-Signature", "")
        try:
            fresh = abs(time.time() - int(ts)) <= MAX_SKEW_SECONDS
        except ValueError:
            fresh = False
        expected = sign(key, ts, request.method, request.get_full_path(), request.body)
        if not (fresh and sig and hmac.compare_digest(sig, expected)):
            return JsonResponse({"error": "invalid signature"}, status=403)
        return view(request, *args, **kwargs)

    return wrapper
