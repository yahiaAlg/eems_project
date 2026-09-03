"""
Seed the "VIP" and "Normal" Django Groups (TODO 1.7).

`Client.is_vip` remains the single field the rest of this project checks
for VIP status/pricing visibility (see TODO 3.2, 4.1, ...) — it's only
ever editable by staff, from `enrollment.admin.ClientAdmin`, never from
any client-facing form. These two Groups exist alongside it for staff who
work from Users/Groups in the Django admin instead; the
`accounts.signals.sync_vip_group_membership` signal keeps every linked
user's group membership in sync with `is_vip` automatically on every
`Client.save()` from here on.

This command creates the groups (if missing) and does a one-time backfill
of existing clients' group membership, for data that predates the signal.

Idempotent: safe to run multiple times.

Usage:
    python manage.py seed_account_groups
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.signals import NORMAL_GROUP_NAME, VIP_GROUP_NAME
from enrollment.models import Client


class Command(BaseCommand):
    help = (
        "Seed the 'VIP' and 'Normal' Django Groups and sync existing "
        "clients' group membership from Client.is_vip."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        vip_group, vip_created = Group.objects.get_or_create(name=VIP_GROUP_NAME)
        normal_group, normal_created = Group.objects.get_or_create(
            name=NORMAL_GROUP_NAME
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ مجموعة «{VIP_GROUP_NAME}» "
                + ("أُنشئت." if vip_created else "موجودة مسبقا.")
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"✔ مجموعة «{NORMAL_GROUP_NAME}» "
                + ("أُنشئت." if normal_created else "موجودة مسبقا.")
            )
        )

        clients = Client.objects.select_related("user").exclude(user__isnull=True)
        synced = 0
        for client in clients:
            if client.is_vip:
                client.user.groups.add(vip_group)
                client.user.groups.remove(normal_group)
            else:
                client.user.groups.add(normal_group)
                client.user.groups.remove(vip_group)
            synced += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ تمت مزامنة عضوية المجموعة لـ {synced} زبون/زبائن (من أصل "
                f"{Client.objects.count()}؛ الباقي بلا حساب دخول مرتبط)."
            )
        )
