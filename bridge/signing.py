"""HMAC-SHA256 request signing shared with the ISI pedagogical server.

signature = HMAC_SHA256(secret, f"{timestamp}.{raw_body}")
Headers:  X-Sync-Timestamp (unix seconds), X-Sync-Signature (hex digest).
"""

import hashlib
import hmac
import time

from django.conf import settings

MAX_SKEW_SECONDS = 300


def get_secret():
    return getattr(settings, "SYNC_SHARED_SECRET", "") or getattr(
        settings, "INSTITUTE_PING_SECRET", ""
    )


def sign(secret, timestamp, body):
    msg = str(timestamp).encode() + b"." + body
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def verify(request):
    """True when the request carries a fresh, valid signature."""
    secret = get_secret()
    if not secret:
        return False
    ts = request.headers.get("X-Sync-Timestamp", "")
    sig = request.headers.get("X-Sync-Signature", "")
    try:
        ts_int = int(ts)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - ts_int) > MAX_SKEW_SECONDS:
        return False
    expected = sign(secret, ts_int, request.body)
    return hmac.compare_digest(expected.encode(), sig.encode())
