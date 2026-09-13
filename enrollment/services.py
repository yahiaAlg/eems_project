"""Business logic triggered off Enrollment state transitions (Phase 10).

Mirrors `accounts/services.py::activate_client_and_send_credentials`'s
contract exactly: never raises, returns a `(ok, message)` tuple meant for
admin messages only, mail-server errors are reported as a failed result
instead of blowing up whatever save triggered the call.
"""

from django.conf import settings
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


def notify_new_enquiry(enquiry):
    """Alert the admin inbox and auto-reply to the visitor for a new
    `Enquiry` — offering-specific ("عندك سؤال حول هذا التخصص؟") or general
    ("تحدث مع مستشار"). Mirrors `pages/views.py::contact`'s own
    admin+user pair (the contact form already does both; this closes the
    same gap for enquiries, which previously sent nothing). Never raises,
    fire-and-forget like every other notifier in this module — no return
    value needed since neither view branch surfaces per-recipient status
    to the visitor.
    """
    context = {
        "name": enquiry.name,
        "phone": enquiry.phone,
        "email": enquiry.email,
        "question": enquiry.question,
        "offering_title": enquiry.offering.title if enquiry.offering else "",
        "offering_code": enquiry.offering.code if enquiry.offering else "",
    }

    admin_emails = [addr for _name, addr in getattr(settings, "ADMINS", [])]
    if admin_emails:
        subject = (
            f"استفسار جديد: {enquiry.offering.title}"
            if enquiry.offering
            else f"استفسار عام جديد من {enquiry.name}"
        )
        send_branded_mail(
            template="emails/enquiry_admin_notification.html",
            subject=subject,
            to=admin_emails,
            reply_to=enquiry.email or None,
            context=context,
        )

    if enquiry.email:
        send_branded_mail(
            template="emails/enquiry_user_confirmation.html",
            subject="استلمنا استفسارك — إيمس",
            to=[enquiry.email],
            context=context,
        )


def notify_admin_of_session_change_request(change_request):
    """Alert the admin inbox once a client proposes a new session date
    (TODO: client-side reschedule request). Mirrors the other
    `send_branded_mail`-based notifiers in this module: never raises,
    returns a `(ok, message)` tuple meant for admin/flash messages only.
    """
    enrollment = change_request.enrollment
    client = enrollment.client
    admin_emails = [addr for _name, addr in getattr(settings, "ADMINS", [])]
    if not admin_emails:
        return False, "لا يوجد بريد إداري مضبوط — لم يُرسل إشعار طلب تغيير الموعد."

    session = enrollment.offering.session
    sent = send_branded_mail(
        template="emails/session_change_request_admin_notification.html",
        subject=f"طلب تغيير موعد الدورة — {client.display_name}",
        to=admin_emails,
        context={
            "client_name": client.display_name,
            "client_type": client.get_client_type_display(),
            "participant_name": enrollment.participant.full_name,
            "offering_title": enrollment.offering.title,
            "offering_code": enrollment.offering.code,
            "session_name": session.name,
            "current_date": session.start_date,
            "proposed_date": change_request.proposed_date,
            "reason": change_request.reason,
        },
    )
    if not sent:
        return False, f"تعذر إرسال إشعار طلب تغيير الموعد ({client.display_name})."
    return True, f"تم إرسال إشعار طلب تغيير الموعد ({client.display_name})."


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
