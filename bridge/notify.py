"""Staff alert when ISI pushes a NEW formation (it arrives hidden, waiting for review)."""

import logging

from django.conf import settings
from django.db import transaction

from pages.emails import send_branded_mail

log = logging.getLogger(__name__)


def notify_new_offering(offering):
    """E-mail the support inbox (settings.ADMINS) once the transaction commits.
    Never raises: a broken mail server must not make ISI's push fail."""
    recipients = [addr for _name, addr in getattr(settings, "ADMINS", []) if addr]
    if not recipients:
        return
    ctx = {
        "code": offering.code,
        "title": offering.title,
        "branch_label": offering.branch_label,
        "duration_days": offering.duration_days,
        "published": offering.is_active,
        "offering_id": offering.pk,
    }

    def _send():
        try:
            send_branded_mail(
                template="emails/formation_pending_admin_notification.html",
                account="support",
                subject=f"تكوين جديد من ISI بانتظار النشر: {offering.code} — {offering.title}",
                to=recipients,
                context=ctx,
            )
        except Exception:  # pragma: no cover
            log.exception("new-offering notification failed")

    transaction.on_commit(_send)
