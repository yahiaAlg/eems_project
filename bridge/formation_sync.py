"""Upsert of an Offering from an ISI formation payload."""

from django.conf import settings
from django.db import transaction

from enrollment.models import FormationSession, Offering

from .models import FormationLink

# payload["fields"] key -> Offering attribute (same name)
SCALAR_FIELDS = ("title", "branch_label", "duration_days", "seats_available", "is_active")
FICHE_FIELDS = ("description", "objectives", "program_outline", "main_tasks", "prerequisites")


class CatalogueMissing(Exception):
    pass


def _catalogue_session():
    slug = getattr(settings, "BRIDGE_CATALOGUE_SLUG", "catalogue-eems")
    try:
        return FormationSession.objects.get(slug=slug)
    except FormationSession.DoesNotExist:
        raise CatalogueMissing(f"Catalogue session '{slug}' does not exist.")


def _norm(s):
    return " ".join((s or "").casefold().split())


def _find_existing(session, code, title):
    """Adopt an Offering imported earlier from the CSVs instead of duplicating."""
    same_code = list(Offering.objects.filter(session=session, code=code))
    if not same_code:
        return None
    for o in same_code:
        if _norm(o.title) == _norm(title):
            return o
    return same_code[0] if len(same_code) == 1 else None


def _find_specialty(code):
    from pages.models import Specialty

    return Specialty.objects.filter(code=code).first() if code else None


def _clean(field, value):
    if field == "title":
        return (value or "").strip()[:150]
    if field == "branch_label":
        return (value or "").strip()[:100]
    return value


@transaction.atomic
def upsert_offering(payload):
    """Create or update the Offering for `payload`. Returns a result dict."""
    isi_id = int(payload["isi_id"])
    code = (payload.get("code") or "").strip()[:20]
    fields = {k: _clean(k, v) for k, v in (payload.get("fields") or {}).items()}
    fiche = {k: (v or "").strip() for k, v in (payload.get("fiche") or {}).items()}
    if not code or not fields.get("title"):
        raise ValueError("code and title are required")

    link = FormationLink.objects.select_related("offering").filter(
        isi_formation_id=isi_id
    ).first()
    created = False
    if link:
        offering = link.offering
    else:
        session = _catalogue_session()
        offering = _find_existing(session, code, fields["title"])
        if offering is None:
            created = True
            offering = Offering(
                session=session,
                code=code,
                fiche_technique_mode="auto",
                is_active=bool(fields.get("is_active", True)),
            )
        link = FormationLink(
            isi_formation_id=isi_id, offering=offering, created_by_sync=created
        )

    incoming = {**{f: fields.get(f) for f in SCALAR_FIELDS if f in fields}, **fiche}
    last = dict(link.last_synced or {})
    written, skipped = [], []
    # Fiche text is only touched while the offering uses the auto fiche.
    protected_by_mode = offering.pk and offering.fiche_technique_mode != "auto"

    for field, new in incoming.items():
        if field in FICHE_FIELDS and protected_by_mode:
            skipped.append(field)
            continue
        if not created and field in last and last[field] == new:
            continue  # ISI value unchanged since last push
        current = getattr(offering, field, None)
        empty = current in (None, "")
        if created:
            can_write = True
        elif field in last:
            # ISI changed it; overwrite only if staff did not edit it since.
            can_write = empty or current == last[field]
        else:
            # Adopted offering: only fill what is still empty.
            can_write = empty
        if can_write:
            setattr(offering, field, new)
            last[field] = new
            written.append(field)
        else:
            skipped.append(field)  # staff-edited on the website: keep theirs

    if created:
        offering.order = offering.order or 0
        offering.title = fields["title"]
    if offering.specialty_id is None:
        spec = _find_specialty(payload.get("specialty_code"))
        if spec:
            offering.specialty = spec
    offering.save()
    link.offering = offering
    link.last_synced = last
    link.save()
    return {
        "created": created,
        "offering_id": offering.pk,
        "slug": offering.slug,
        "url": offering.get_absolute_url() if hasattr(offering, "get_absolute_url") else "",
        "written": written,
        "skipped": skipped,
    }
