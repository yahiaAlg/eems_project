"""Record 'client X changed' whenever a client, a subscriber/participant, an
enrollment or a company-roster line is saved or deleted, so ISI's next pull
picks the client up. Public API sign-ups use ``bulk_create`` (no signals) but
always create/save the Client in the same transaction, which is enough: the
snapshot is read after commit and contains the bulk-created rows."""

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from enrollment.models import Client, Enrollment, EnrollmentParticipant, Participant

from .models import SyncEvent


def record_client_changed(client_id):
    if not client_id:
        return

    def _write():
        with transaction.atomic():
            # one row per client; re-created so its id (the feed cursor) moves forward
            SyncEvent.objects.filter(client_id=client_id).delete()
            SyncEvent.objects.create(client_id=client_id)

    transaction.on_commit(_write)


def record_clients_changed(client_ids):
    """For code paths that bypass signals (queryset.update)."""
    for cid in set(client_ids):
        record_client_changed(cid)


@receiver([post_save, post_delete], sender=Client)
def _client_changed(sender, instance, **kw):
    record_client_changed(instance.pk)


@receiver([post_save, post_delete], sender=Participant)
@receiver([post_save, post_delete], sender=Enrollment)
def _child_changed(sender, instance, **kw):
    record_client_changed(instance.client_id)


@receiver([post_save, post_delete], sender=EnrollmentParticipant)
def _roster_changed(sender, instance, **kw):
    cid = (
        Enrollment.objects.filter(pk=instance.enrollment_id)
        .values_list("client_id", flat=True)
        .first()
    )
    record_client_changed(cid)
