"""
Shared helper for sending branded HTML emails (contact form, newsletter,
enrollment notifications, ...). Every call renders an HTML template from
`templates/emails/`, builds a plain-text fallback automatically, and sends
through the SMTP backend configured in settings.py (support@excellance-ms.dz).

Usage:
    from pages.emails import send_branded_mail
    send_branded_mail(
        template="emails/contact_user_confirmation.html",
        subject="استلمنا رسالتك",
        to=["client@example.com"],
        context={"name": "..."},
    )

    # TODO 7.3 — with a file attached (e.g. the proforma bon-de-commande):
    send_branded_mail(
        ...,
        attachments=[("bon.pdf", file_bytes, "application/pdf")],
    )
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def _mailbox(account):
    """(connection, from_email) for the requested mailbox.

    "support" (default) -> the project-wide SMTP settings (support@...).
    "inscription"       -> inscription@... (registration-related mails).
    """
    if account == "inscription":
        connection = get_connection(
            username=settings.INSCRIPTION_EMAIL_HOST_USER,
            password=settings.INSCRIPTION_EMAIL_HOST_PASSWORD,
            fail_silently=True,
        )
        return connection, settings.INSCRIPTION_FROM_EMAIL
    return None, getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER)


def send_branded_mail(
    template, subject, to, context=None, reply_to=None, attachments=None, account="support"
):
    """Render `template` with `context` and send it as an HTML email.

    `attachments`, if given, is an iterable of `(filename, content, mimetype)`
    tuples — the same shape `EmailMessage.attach()` takes — attached
    directly to the outgoing message (TODO 7.3: e.g. a VIP proforma
    request's uploaded bon-de-commande, so the admin/accountant get the
    actual file with no separate link to secure).

    `account` picks the sending mailbox: "support" (default) or
    "inscription" (registration-related emails).

    Never raises: any SMTP/template error is swallowed so a broken mail
    server never breaks a contact/newsletter/enrollment submission.
    Returns True on success, False otherwise.
    """
    context = dict(context or {})
    context.setdefault("site_name", "إيمس — مؤسسة التميز للإدارة والأمن")
    context.setdefault("site_url", "https://excellance-ms.dz")

    try:
        html_body = render_to_string(template, context)
        text_body = strip_tags(html_body)
        connection, from_email = _mailbox(account)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            connection=connection,
            to=to if isinstance(to, (list, tuple)) else [to],
            reply_to=reply_to if isinstance(reply_to, (list, tuple)) else (
                [reply_to] if reply_to else None
            ),
        )
        msg.attach_alternative(html_body, "text/html")
        for filename, content, mimetype in attachments or []:
            msg.attach(filename, content, mimetype)
        msg.send(fail_silently=True)
        return True
    except Exception:
        return False
