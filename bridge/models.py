"""Bridge between this website and the institute's pedagogical app (ISI).

The pedagogical server lives on the institute's LAN and cannot be reached from
this (shared-hosting) site, so every exchange is initiated by ISI:

* ISI PUSHES new/updated formations to ``formations/`` (-> ``Offering``).
* ISI PULLS client/participant changes from ``feed/`` (a cursor over
  ``SyncEvent``), so nothing here ever needs to call the LAN.
"""

from django.db import models


class FormationLink(models.Model):
    """Maps an ISI ``Formation`` to the website ``Offering`` it created/adopted.

    ``last_payload`` is the set of mapped values applied on the previous sync.
    On the next sync only the values ISI changed since then are written, so
    anything staff customised on the website (price, images, hand-edited fiche
    technique…) is never overwritten by an unrelated ISI edit.
    """

    isi_formation_id = models.PositiveIntegerField(unique=True)
    offering = models.OneToOneField(
        "enrollment.Offering", on_delete=models.CASCADE, related_name="isi_link"
    )
    last_payload = models.JSONField(default=dict, blank=True)
    created_from_isi = models.BooleanField(default=True)
    deleted_in_isi = models.BooleanField(
        default=False,
        help_text="La formation a été supprimée dans ISI : l'offre est masquée, jamais supprimée. "
        "Si ISI recrée la même formation (même code + titre), l'offre est ré-adoptée.",
    )
    last_synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "lien formation ISI"
        verbose_name_plural = "liens formations ISI"

    def __str__(self):
        return f"ISI#{self.isi_formation_id} -> {self.offering_id}"


class ContactPlaceholder(models.Model):
    """Marks the Participant that the web sign-up form creates for an
    ENTERPRISE only to stand in as the contact person of the enrollment (its
    real trainees come later through the company roster). Such a participant is
    never sent to ISI as a trainee. Set explicitly at creation time (see
    enrollment.views) instead of guessed from names; rows that existed before
    the bridge was installed were marked once by migration 0002."""

    participant = models.OneToOneField(
        "enrollment.Participant", on_delete=models.CASCADE, related_name="contact_placeholder"
    )

    def __str__(self):
        return f"placeholder {self.participant_id}"


class SyncEvent(models.Model):
    """'Client X changed' marker. The feed re-reads the client's CURRENT state
    when ISI asks, so events are tiny and idempotent (a deletion is simply a
    client that no longer exists)."""

    client_id = models.PositiveIntegerField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"#{self.pk} client {self.client_id}"
