"""Keeps a `Client`'s linked login's Django Group membership ("VIP" /
"Normal") in sync with `Client.is_vip` (TODO 1.7).

Per the TODO note — "pick one and use it consistently everywhere else in
this TODO" — `Client.is_vip` stays the single field the rest of the
project checks (see TODO 3.2's `request.user.client.is_vip`, TODO 4.1's
VIP-only trainer selection, etc.). It's only ever editable from the Django
admin (`enrollment.admin.ClientAdmin`'s "الحساب" fieldset), never from any
client-facing form — so "toggled by admin/accountant only, never by the
client" already holds for it.

This signal mirrors that single source of truth onto the "VIP"/"Normal"
Groups seeded by the `seed_account_groups` management command, so staff who
prefer working from Users/Groups in the admin always see a membership that
matches `is_vip`, without a second, independently-editable toggle existing
anywhere.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from enrollment.models import Client

VIP_GROUP_NAME = "VIP"
NORMAL_GROUP_NAME = "Normal"


@receiver(post_save, sender=Client)
def sync_vip_group_membership(sender, instance, **kwargs):
    user = instance.user
    if user is None:
        return

    from django.contrib.auth.models import Group

    try:
        vip_group = Group.objects.get(name=VIP_GROUP_NAME)
        normal_group = Group.objects.get(name=NORMAL_GROUP_NAME)
    except Group.DoesNotExist:
        # Not seeded yet — run `python manage.py seed_account_groups` once;
        # nothing to sync until the groups exist.
        return

    if instance.is_vip:
        user.groups.add(vip_group)
        user.groups.remove(normal_group)
    else:
        user.groups.add(normal_group)
        user.groups.remove(vip_group)
