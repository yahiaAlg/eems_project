"""Full current state of one website client, as the ISI app consumes it."""

from enrollment.models import Client

# Enrollment states worth showing to the institute. Rejected / cancelled /
# waitlisted people simply disappear from the snapshot (= removed on ISI).
LIVE_STATUSES = ("pending", "contacted", "accepted", "confirmed")


def _gender(value):
    return {"m": "M", "f": "F", "M": "M", "F": "F"}.get(value or "", "")


def _iso(d):
    return d.isoformat() if d else None


def _offering_ref(offering):
    link = getattr(offering, "isi_link", None)
    return {
        "code": offering.code,
        "slug": offering.slug,
        "title": offering.title,
        "session_slug": offering.session.slug,
        "isi_formation_id": link.isi_formation_id if link else None,
    }


def _is_placeholder_participant(client, participant):
    """Web-form enterprise sign-ups store the *contact person* as the Enrollment
    participant (real trainees come later via the roster); the API sign-up stores
    real employees there. Only participants explicitly marked ContactPlaceholder
    are skipped."""
    return hasattr(participant, "contact_placeholder")


def _roster_lines(client):
    enrollments = (
        client.enrollments.filter(status__in=LIVE_STATUSES)
        .select_related(
            "participant", "participant__contact_placeholder",
            "offering", "offering__session", "offering__isi_link",
        )
        .prefetch_related("roster")
        .order_by("pk")
    )
    lines = []
    for e in enrollments:
        base = {
            "enrollment_id": e.pk,
            "enrollment_status": e.status,
            "offering": _offering_ref(e.offering),
        }
        roster = list(e.roster.all())
        if client.client_type == "enterprise" and roster:
            for r in roster:  # authoritative company roster (Phase 10)
                lines.append({
                    **base, "ext_id": f"ep:{r.pk}",
                    "first_name": r.first_name, "last_name": r.last_name,
                    "first_name_ar": r.first_name_ar, "last_name_ar": r.last_name_ar,
                    "gender": _gender(r.gender), "date_of_birth": _iso(r.date_of_birth),
                    "place_of_birth": r.place_of_birth, "place_of_birth_ar": r.place_of_birth_ar,
                    "job_title": r.job_title, "employer": r.employer or client.company_name,
                    "phone": r.phone, "email": r.email,
                })
            continue
        p = e.participant
        if client.client_type == "enterprise" and _is_placeholder_participant(client, p):
            continue
        lines.append({
            **base, "ext_id": f"en:{e.pk}", "full_name": p.full_name,
            "gender": _gender(p.gender), "date_of_birth": _iso(p.birth_date),
            "job_title": p.position if client.client_type == "enterprise" else "",
            "employer": client.company_name if client.client_type == "enterprise" else "",
            "education_level": p.education_level, "phone": p.phone, "email": p.email,
        })
    return lines


def client_snapshot(client):
    if client.account_status != "active":
        # pending (awaiting admin approval) / rejected: not the institute's business yet
        return {"ext_id": client.pk, "deleted": True, "reason": client.account_status}
    return {
        "ext_id": client.pk,
        "deleted": False,
        "type": client.client_type,
        "company_name": client.company_name,
        "trade_register_number": client.trade_register_number,
        "nif": client.nif, "nis": client.nis,
        "forme_juridique": client.forme_juridique,
        "sector": client.sector,
        "responsible_name": client.responsible_name,
        "responsible_position": client.responsible_position,
        "main_contact_name": client.main_contact_name,
        "full_name": client.full_name,
        "phone": client.phone, "email": client.email,
        "wilaya": client.wilaya, "city": client.city,
        "address": client.address, "postal_code": client.postal_code,
        "roster": _roster_lines(client),
    }


def snapshots_for(ids):
    found = {c.pk: c for c in Client.objects.filter(pk__in=ids)}
    return [
        client_snapshot(found[i]) if i in found else {"ext_id": i, "deleted": True, "reason": "removed"}
        for i in ids
    ]
