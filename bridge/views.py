import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .formation_sync import deactivate_offerings, upsert_offering
from .models import SyncEvent
from .security import signed_endpoint
from .snapshot import snapshots_for
from enrollment.models import Client

MAX_PAGE = 100


@signed_endpoint
@require_POST
def formations_upsert(request):
    """ISI -> site. Body: one formation payload, or {"formations": [...]}."""
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"error": "invalid json"}, status=400)
    items = data.get("formations") if isinstance(data, dict) and "formations" in data else [data]
    results, errors = [], []
    for item in items:
        try:
            results.append(upsert_offering(item))
        except Exception as exc:  # report per item, keep the batch going
            errors.append({"isi_formation_id": (item or {}).get("isi_formation_id"), "error": str(exc)})
    return JsonResponse({"results": results, "errors": errors}, status=200 if not errors else 207)


@signed_endpoint
@require_POST
def formations_deactivate(request):
    """ISI -> site. Body: {"isi_formation_ids": [..]} — formations deleted in ISI."""
    try:
        ids = [int(i) for i in json.loads(request.body or b"{}").get("isi_formation_ids", [])]
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({"error": "invalid json"}, status=400)
    return JsonResponse({"deactivated": deactivate_offerings(ids)})


@signed_endpoint
@require_GET
def feed(request):
    """site -> ISI (pulled by ISI).

    ?mode=head                       -> {"cursor": <latest event id>}
    ?cursor=N&limit=50               -> clients changed after event N
    ?mode=full&after_id=N&limit=50   -> every client by id (initial/backfill/repair)
    """
    mode = request.GET.get("mode", "events")
    try:
        limit = max(1, min(int(request.GET.get("limit", 50)), MAX_PAGE))
        cursor = int(request.GET.get("cursor", 0))
        after_id = int(request.GET.get("after_id", 0))
    except ValueError:
        return JsonResponse({"error": "bad parameter"}, status=400)

    if mode == "head":
        last = SyncEvent.objects.order_by("-id").values_list("id", flat=True).first() or 0
        top = Client.objects.order_by("-pk").values_list("pk", flat=True).first() or 0
        return JsonResponse({"cursor": last, "max_client_id": top})

    if mode == "full":
        ids = list(
            Client.objects.filter(pk__gt=after_id).order_by("pk").values_list("pk", flat=True)[: limit + 1]
        )
        has_more = len(ids) > limit
        ids = ids[:limit]
        return JsonResponse({
            "mode": "full", "has_more": has_more,
            "after_id": ids[-1] if ids else after_id,
            "clients": snapshots_for(ids),
        })

    seen, last_id = [], cursor
    for ev in SyncEvent.objects.filter(id__gt=cursor).order_by("id")[: limit * 5]:
        if ev.client_id not in seen:
            if len(seen) >= limit:
                break
            seen.append(ev.client_id)
        last_id = ev.id
    return JsonResponse({
        "mode": "events",
        "cursor": last_id,
        "has_more": SyncEvent.objects.filter(id__gt=last_id).exists(),
        "clients": snapshots_for(seen),
    })
