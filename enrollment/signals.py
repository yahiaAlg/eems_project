from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Enrollment


@receiver(pre_save, sender=Enrollment)
def _capture_previous_status(sender, instance, **kwargs):
    """Stash the pre-save status on the instance so the post_save receiver
    below can detect a transition rather than just a current value —
    needed because saving an already-"accepted" enrollment again (e.g.
    editing `motivation`) must NOT re-send the acceptance email (TODO
    10.1.1)."""
    if instance.pk:
        try:
            instance._previous_status = Enrollment.objects.only("status").get(
                pk=instance.pk
            ).status
        except Enrollment.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=Enrollment)
def notify_on_accepted_transition(sender, instance, created, **kwargs):
    """TODO 10.1.1 — fires exactly once per transition *into* "accepted",
    regardless of entry point (change form or bulk admin action — the
    latter must call `.save()` per object rather than `.update()` for this
    to fire; see `EnrollmentAdmin.mark_accepted`), and never re-fires on
    subsequent saves while status stays "accepted"."""
    if created:
        return
    previous = getattr(instance, "_previous_status", None)
    if previous != "accepted" and instance.status == "accepted":
        from .services import notify_enrollment_accepted

        notify_enrollment_accepted(instance)


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
