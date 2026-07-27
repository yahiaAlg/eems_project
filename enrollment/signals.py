from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Enrollment


@receiver(post_save, sender=Enrollment)
def notify_staff_on_new_enrollment(sender, instance, created, **kwargs):
    if not created:
        return
    # Uses Django's ADMINS setting + configured EMAIL_BACKEND.
    # Silently no-ops if email isn't configured — never blocks the request.
    from django.core.mail import mail_admins

    client = instance.client
    try:
        mail_admins(
            subject=f"تسجيل جديد: {client.display_name} — {instance.offering.code}",
            message=(
                f"الزبون: {client.display_name} ({client.get_client_type_display()})\n"
                f"المشارك: {instance.participant.full_name}\n"
                f"الهاتف: {client.phone}\n"
                f"التخصص: {instance.offering.title} ({instance.offering.code})\n"
                f"الدورة: {instance.offering.session.name}\n"
            ),
            fail_silently=True,
        )
    except Exception:
        pass
