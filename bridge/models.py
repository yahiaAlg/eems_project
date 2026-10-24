from django.db import models


class FormationLink(models.Model):
    """Maps an ISI `Formation` to its website `Offering`.

    `last_synced` stores the values ISI last pushed, field by field. It lets
    later pushes overwrite only what ISI changed AND what staff did not
    hand-edit on the website since.
    """

    isi_formation_id = models.PositiveIntegerField(unique=True)
    offering = models.OneToOneField(
        "enrollment.Offering",
        on_delete=models.CASCADE,
        related_name="isi_link",
    )
    last_synced = models.JSONField(default=dict, blank=True)
    created_by_sync = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lien formation ISI"
        verbose_name_plural = "Liens formations ISI"

    def __str__(self):
        return f"ISI #{self.isi_formation_id} → {self.offering_id}"
