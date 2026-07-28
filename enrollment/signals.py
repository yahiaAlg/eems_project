from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Enrollment


@receiver(post_save, sender=Enrollment)
def notify_staff_on_new_enrollment(sender, instance, created, **kwargs):
    if not created:
        return

    from django.conf import settings
    from pages.emails import send_branded_mail

    client = instance.client
    context = {
        "client_name": client.display_name,
        "client_type": client.get_client_type_display(),
        "participant_name": instance.participant.full_name,
        "phone": client.phone,
        "offering_title": instance.offering.title,
        "offering_code": instance.offering.code,
        "session_name": instance.offering.session.name,
    }

    # Notify admins/support inbox with the branded HTML template.
    admin_emails = [addr for _name, addr in getattr(settings, "ADMINS", [])]
    if admin_emails:
        send_branded_mail(
            template="emails/enrollment_admin_notification.html",
            subject=f"تسجيل جديد: {client.display_name} — {instance.offering.code}",
            to=admin_emails,
            context=context,
        )

    # Confirm receipt to the client, if they provided an email address.
    if client.email:
        send_branded_mail(
            template="emails/enrollment_client_confirmation.html",
            subject="تم استلام طلب تسجيلك — إيمس",
            to=[client.email],
            context=context,
        )
