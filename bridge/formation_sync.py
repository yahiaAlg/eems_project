"""ISI Formation  ->  website Offering (+ its auto-generated fiche technique).

ISI sends the formation's data together with the fiche content it generated
(description / objectives / program / tasks / prerequisites). We only ever
write what ISI *changed since the last sync*, and never overwrite fiche text
that staff hand-edited on the website (see FormationLink docstring).
"""

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify

from enrollment.models import FormationSession, Offering
from pages.models import Branch, Specialty

from .models import FormationLink
from .notify import notify_new_offering

FICHE_FIELDS = (
    "description",
    "objectives",
    "program_outline",
    "main_tasks",
    "prerequisites",
)
SCALAR_FIELDS = (
    "code",
    "title",
    "branch_label",
    "duration_days",
    "seats_available",
    "is_active",
    "specialty_code",
)


def default_session():
    slug = getattr(settings, "SYNC_DEFAULT_SESSION_SLUG", "catalogue-eems")
    session, _ = FormationSession.objects.get_or_create(
        slug=slug,
        defaults={"name": "الكتالوج العام لتكوينات إيمس", "is_active": True, "order": 0},
    )
    return session


def map_payload(p):
    """ISI payload -> the website values we manage (JSON-serialisable)."""
    spec = p.get("specialty") or {}
    fiche = p.get("fiche") or {}
    code = ((p.get("website_code") or p.get("code") or "").strip())[:20]
    mapped = {
        "code": code,
        "title": ((p.get("title_ar") or "").strip() or (p.get("title") or "").strip())[:150],
        "branch_label": (
            (spec.get("branch_name_ar") or "").strip()
            or (p.get("category") or "").strip()
            or "تكوين عام"
        )[:100],
        "duration_days": p.get("duration_days") or None,
        "seats_available": p.get("max_participants") or 20,
        "is_active": bool(p.get("is_active", True)),
        "specialty_code": (
            f"{spec.get('branch_abbr', '')}{spec.get('code', '')}" if spec else ""
        ),
    }
    for f in FICHE_FIELDS:
        v = (fiche.get(f) or "").strip()
        mapped[f] = " ".join(v.split()) if f == "description" else v
    return mapped


def _resolve_specialty(p, code):
    """Specialty from the ISI catalogue (branch + specialty created if new)."""
    spec = p.get("specialty") or {}
    if not code or not spec:
        return Specialty.objects.filter(code=code).first() if code else None
    branch, _ = Branch.objects.get_or_create(
        code=(spec.get("branch_abbr") or "")[:10],
        defaults={
            "name_ar": spec.get("branch_name_ar") or spec.get("branch_name") or spec["branch_abbr"],
            "name_fr": spec.get("branch_name") or "",
        },
    )
    specialty, _ = Specialty.objects.get_or_create(
        code=code[:12],
        defaults={
            "name": spec.get("title_ar") or spec.get("title") or code,
            "branch": branch,
        },
    )
    return specialty


def _unique_slug(session, base_title, code, exclude_pk=None):
    # Built from the FRENCH title so it equals ISI's Formation.title_slug
    # (the URL ISI already shows staff as "voir sur le site").
    base = (slugify(base_title or "") or slugify(code or "") or "formation")[:160]
    slug, i = base, 2
    qs = Offering.objects.filter(session=session)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


def _adopt_candidate(session, p, new):
    """An offering imported earlier from the CSV exports (no link yet) with the
    same code+title is adopted instead of duplicated."""
    titles = {t for t in (new["title"], p.get("title"), p.get("title_ar")) if t}
    qs = Offering.objects.filter(session=session, code=new["code"]).filter(
        Q(isi_link__isnull=True) | Q(isi_link__deleted_in_isi=True)
    )
    return qs.filter(title__in=titles).first()


@transaction.atomic
def upsert_offering(p):
    """Create / adopt / update the Offering for one ISI formation payload.
    Returns a small JSON-able result dict."""
    isi_id = int(p["isi_formation_id"])
    session = default_session()
    new = map_payload(p)
    if not new["code"] or not new["title"]:
        raise ValueError("code and title are required")

    link = FormationLink.objects.select_related("offering").filter(isi_formation_id=isi_id).first()
    result = {"isi_formation_id": isi_id, "created": False, "adopted": False, "updated": []}

    if link is None:
        offering = _adopt_candidate(session, p, new)
        specialty = _resolve_specialty(p, new["specialty_code"])
        if offering is not None:
            # Fill blanks only — never touch what the website already has.
            changed = []
            if offering.specialty_id is None and specialty:
                offering.specialty = specialty
                changed.append("specialty")
            for f in FICHE_FIELDS:
                if new[f] and not (getattr(offering, f) or "").strip():
                    setattr(offering, f, new[f])
                    changed.append(f)
            if changed:
                offering.save()
            old_link = getattr(offering, "isi_link", None)
            if old_link is not None:   # re-created in ISI after a deletion: re-point, stay hidden
                old_link.isi_formation_id, old_link.deleted_in_isi = isi_id, False
                old_link.last_payload = new
                old_link.save()
            else:
                FormationLink.objects.create(
                    isi_formation_id=isi_id, offering=offering,
                    last_payload=new, created_from_isi=False,
                )
            result.update(adopted=True, updated=changed)
        else:
            offering = Offering(
                session=session, specialty=specialty, code=new["code"],
                title=new["title"], branch_label=new["branch_label"],
                duration_days=new["duration_days"], seats_available=new["seats_available"],
                # new offerings stay hidden until staff review the generated fiche
                # and publish them (SYNC_NEW_OFFERINGS_ACTIVE=1 publishes at once)
                is_active=new["is_active"] and getattr(settings, "SYNC_NEW_OFFERINGS_ACTIVE", False),
                fiche_technique_mode="auto",
                order=isi_id,
                **{f: new[f] for f in FICHE_FIELDS},
            )
            offering.slug = _unique_slug(session, p.get("title"), new["code"])
            offering.save()
            FormationLink.objects.create(
                isi_formation_id=isi_id, offering=offering,
                last_payload=new, created_from_isi=True,
            )
            result["created"] = True
            notify_new_offering(offering)
    else:
        offering, old = link.offering, link.last_payload or {}
        changed = []
        for field in SCALAR_FIELDS:
            if field == "specialty_code":
                continue
            if old.get(field) == new[field]:
                continue  # ISI did not touch it -> leave website value alone
            setattr(offering, field, new[field])
            changed.append(field)
        if old.get("specialty_code") != new["specialty_code"] and new["specialty_code"]:
            offering.specialty = _resolve_specialty(p, new["specialty_code"])
            changed.append("specialty")
        for f in FICHE_FIELDS:
            if old.get(f) == new[f]:
                continue
            current = (getattr(offering, f) or "").strip()
            if current and current != (old.get(f) or "").strip():
                continue  # hand-edited on the website -> keep staff's text
            setattr(offering, f, new[f])
            changed.append(f)
        if changed:
            offering.save()
        link.last_payload = new
        link.save()
        result["updated"] = changed

    result.update(
        is_active=offering.is_active,
        offering_id=offering.pk,
        path=offering.get_absolute_url(),
        fiche_status=offering.fiche_technique_status,
    )
    return result


@transaction.atomic
def deactivate_offerings(isi_ids):
    """A formation was deleted in ISI: hide its offering (never delete it —
    enrollments may reference it). Returns the ids actually deactivated."""
    done = []
    for link in FormationLink.objects.select_related("offering").filter(isi_formation_id__in=isi_ids):
        if link.offering.is_active:
            link.offering.is_active = False
            link.offering.save()
        # last_payload is left as ISI last sent it, so an unrelated later ISI edit
        # (is_active unchanged on ISI's side) will not silently re-publish it.
        link.deleted_in_isi = True
        link.save()
        done.append(link.isi_formation_id)
    return done
