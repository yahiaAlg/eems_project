import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import signing
from .formation_sync import CatalogueMissing, upsert_offering


@csrf_exempt
@require_POST
def formation_upsert(request):
    if not signing.verify(request):
        return JsonResponse({"error": "forbidden"}, status=403)
    try:
        payload = json.loads(request.body.decode("utf-8"))
        result = upsert_offering(payload)
    except CatalogueMissing as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    except (ValueError, KeyError, TypeError) as exc:
        return JsonResponse({"error": f"bad payload: {exc}"}, status=400)
    return JsonResponse({"ok": True, **result})


@csrf_exempt
@require_POST
def ping(request):
    """Lets ISI check connectivity + secret without side effects."""
    if not signing.verify(request):
        return JsonResponse({"error": "forbidden"}, status=403)
    return JsonResponse({"ok": True})
