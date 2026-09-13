"""Business logic triggered off Enrollment state transitions (Phase 10).

Mirrors `accounts/services.py::activate_client_and_send_credentials`'s
contract exactly: never raises, returns a `(ok, message)` tuple meant for
admin messages only, mail-server errors are reported as a failed result
instead of blowing up whatever save triggered the call.
"""

from django.template.loader import render_to_string
from django.utils import timezone

from pages.emails import send_branded_mail


def notify_enrollment_accepted(enrollment):
    """Email the client once their Enrollment transitions into "accepted".

    Called from `enrollment/signals.py::notify_on_accepted_transition`,
    which fires exactly once per transition into "accepted" regardless of
    whether it came from the admin change form or a bulk action (TODO
    10.1.1) — this function itself doesn't care how it got called.
    """
    client = enrollment.client
    recipient = client.email
    if not recipient:
        return False, f"{client.display_name}: لا يوجد بريد إلكتروني — لم يُرسل إشعار القبول."

    session = enrollment.offering.session  # start_date may be None — template is None-safe
    is_enterprise = client.is_enterprise
    sent = send_branded_mail(
        template="emails/enrollment_accepted.html",
        subject=f"تم قبول تسجيلك — {enrollment.offering.title}",
        to=[recipient],
        context={
            "client_name": client.display_name,
            "offering_title": enrollment.offering.title,
            "session_date": session.start_date,
            "is_enterprise": is_enterprise,
            # Relative paths — combined with the `site_url` context default
            # (see pages/emails.py) in the template itself. The roster page
            # itself ships in TODO 10.2; the link is safe to send ahead of
            # that (no reverse() involved), matching this phase's own
            # incremental build order.
            "roster_path": (
                f"/mon-espace/inscriptions/{enrollment.pk}/participants/"
                if is_enterprise else None
            ),
            "dashboard_path": "/mon-espace/",
        },
    )
    if not sent:
        return False, f"{client.display_name}: تعذر إرسال إشعار القبول إلى {recipient}."
    return True, f"تم إرسال إشعار القبول إلى {recipient}."


def schedule_session(enrollment, start_date, registration_deadline=None):
    """Set a firm date on the `FormationSession` shared by every enrollment
    on this offering, lock *this* enrollment's own roster, and email the
    client (TODO 10.7.1).

    Called from `enrollment/admin.py`'s dedicated schedule-session view
    (one date field, not a bulk admin action — see that module for why).
    Deliberately does not touch other enrollments' `roster_locked_at` on
    the same offering (10.7.1: "each company's admin locks independently,
    only the shared date is, well, shared") and does not require the
    roster to be non-empty first (10.7.2).

    Never raises, mirrors `notify_enrollment_accepted`'s `(ok, message)`
    contract for admin messages — a failed notification email still
    leaves the date set and the roster locked, it's just reported back as
    a partial success.
    """
    session = enrollment.offering.session
    session.start_date = start_date
    update_fields = ["start_date"]
    if registration_deadline:
        session.registration_deadline = registration_deadline
        update_fields.append("registration_deadline")
    session.save(update_fields=update_fields)

    enrollment.roster_locked_at = timezone.now()
    enrollment.save(update_fields=["roster_locked_at"])

    client = enrollment.client
    date_display = start_date.strftime("%d/%m/%Y")
    if not client.email:
        return (
            True,
            f"{client.display_name}: تم تحديد تاريخ الدورة ({date_display}) "
            "وإغلاق القائمة — لا يوجد بريد إلكتروني لإرسال إشعار.",
        )

    sent = send_branded_mail(
        template="emails/session_scheduled.html",
        subject=f"تم تحديد تاريخ الدورة — {enrollment.offering.title}",
        to=[client.email],
        context={
            "client_name": client.display_name,
            "offering_title": enrollment.offering.title,
            "session_date": start_date,
        },
    )
    if not sent:
        return (
            False,
            f"{client.display_name}: تم تحديد تاريخ الدورة ({date_display}) "
            f"وإغلاق القائمة، لكن تعذر إرسال الإشعار إلى {client.email}.",
        )
    return (
        True,
        f"{client.display_name}: تم تحديد تاريخ الدورة ({date_display})، "
        f"إغلاق القائمة، وإرسال الإشعار إلى {client.email}.",
    )


def build_session_brief(enrollment):
    """Render `session_brief_<enrollment_id>.txt` (TODO 10.7.3) — the
    plain-text companion bundled with the roster CSV export (TODO 10.2.6)
    for the staff member creating the matching `isi_pedagogical_webapp`
    Session by hand. Gives them everything needed to match an existing
    `clients.Client` (by nif/nis/name) or create a new one; no code on
    that side is touched by this phase (file-based hand-off only).
    """
    return render_to_string(
        "enrollment/session_brief.txt",
        {
            "enrollment": enrollment,
            "offering": enrollment.offering,
            "client": enrollment.client,
            "session": enrollment.offering.session,
            "participant_count": enrollment.roster.count(),
        },
    )
