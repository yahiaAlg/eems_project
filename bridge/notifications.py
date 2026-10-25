"""Staff alerts for what the ISI bridge does on its own.

A formation created in ISI arrives on the website HIDDEN (so nobody publishes a
half-reviewed fiche by accident). Without an alert nobody would know it is waiting,
so staff get an email at the project's ADMINS address (support@…) — the same
channel the website already uses for other admin notifications. Never raises:
`send_branded_mail` swallows SMTP errors, and the DB work is already committed.
"""

from django.conf import settings

from pages.emails import send_branded_mail

TEMPLATE = "emails/isi_offering_notification.html"


def _recipients():
    return [addr for _name, addr in getattr(settings, "ADMINS", []) if addr]


def _context(offering, title_fr, **extra):
    ctx = {
        "offering_id": offering.pk,
        "code": offering.code,
        "title": offering.title,
        "title_fr": title_fr or "",
        "duration_days": offering.duration_days,
        "is_active": offering.is_active,
    }
    ctx.update(extra)
    return ctx


def notify_offering_created(offering, title_fr=""):
    to = _recipients()
    if not to:
        return False
    hidden = not offering.is_active
    return send_branded_mail(
        template=TEMPLATE,
        subject=f"تكوين جديد من ISI {'بانتظار المراجعة' if hidden else 'تم نشره'} — {offering.code}",
        to=to,
        context=_context(
            offering, title_fr,
            heading="تكوين جديد من تطبيق ISI",
            intro=(
                "أُنشئ هذا التكوين في التطبيق البيداغوجي وتمت مزامنته مع الموقع. بطاقته التقنية مُولَّدة تلقائيا "
                "(قاعدية وعامة): راجعها وحسّنها ثم انشر العرض من لوحة التحكم، فهو مخفي عن الزوار إلى حين نشره."
                if hidden else
                "أُنشئ هذا التكوين في التطبيق البيداغوجي وتمت مزامنته مع الموقع وهو منشور الآن. بطاقته التقنية "
                "مُولَّدة تلقائيا — راجعها وحسّنها عند الحاجة."
            ),
            button="مراجعة العرض ونشره" if hidden else "مراجعة العرض",
        ),
    )


def notify_offering_hidden(offering, title_fr=""):
    to = _recipients()
    if not to:
        return False
    return send_branded_mail(
        template=TEMPLATE,
        subject=f"تكوين محذوف في ISI — أُخفي العرض {offering.code}",
        to=to,
        context=_context(
            offering, title_fr,
            heading="تكوين محذوف في تطبيق ISI",
            intro=(
                "حُذف هذا التكوين من التطبيق البيداغوجي، لذلك أُخفي عرضه من الموقع (دون حذفه، حفاظا على "
                "التسجيلات المرتبطة به). يمكنك إعادة نشره من لوحة التحكم إذا لزم الأمر."
            ),
            button="فتح العرض",
        ),
    )
