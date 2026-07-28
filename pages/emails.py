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
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_branded_mail(template, subject, to, context=None, reply_to=None):
    """Render `template` with `context` and send it as an HTML email.

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
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
            to=to if isinstance(to, (list, tuple)) else [to],
            reply_to=reply_to if isinstance(reply_to, (list, tuple)) else (
                [reply_to] if reply_to else None
            ),
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=True)
        return True
    except Exception:
        return False
