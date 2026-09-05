"""
Seed the "Accountant" Django Group (TODO 6.1).

Unlike "VIP"/"Normal" (TODO 1.7, `seed_account_groups.py`), this group
doesn't mirror a field on `Client` — it's a real *staff* permission group
for the Django admin, for the small team who reviews VIP proforma
requests and non-VIP quote requests and (from TODO 6.2 on) sets the
per-line custom tariff on a `QuoteRequest`. Deliberately scoped to just
that: view/change on `ProformaInvoice`/`ProformaInvoiceItem` and
`QuoteRequest`/`QuoteRequestItem` only — no "add"/"delete" (these records
are only ever created by the client-facing checkout flow, TODO 5.2/5.3,
never typed in from scratch by staff) and no permissions at all on any
other app/model (`Client`, `Offering`, `Formateur`, `User`, ...). That is
what keeps this a scoped "Accountant" role rather than a second admin
account — full admin access stays with `is_superuser`/`is_staff` +
default admin group membership, not this Group.

A user still needs `is_staff=True` (set from the Django admin, same as
any staff account) to log into `/admin/` at all; this command only
creates the Group and attaches the scoped permissions to it. Adding
specific users to the group is a normal admin "Users" action.

Idempotent: safe to run multiple times.

Usage:
    python manage.py seed_accountant_group
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

ACCOUNTANT_GROUP_NAME = "Accountant"

# (app_label, model_name, [codename_prefixes]) — kept explicit rather than
# "every permission on these models" so it's obvious at a glance that
# "add"/"delete" are intentionally left out (see docstring above).
SCOPED_PERMISSIONS = [
    ("enrollment", "proformainvoice", ["view", "change"]),
    ("enrollment", "proformainvoiceitem", ["view"]),
    ("enrollment", "quoterequest", ["view", "change"]),
    ("enrollment", "quoterequestitem", ["view", "change"]),
]


class Command(BaseCommand):
    help = (
        "Seed the 'Accountant' Django Group, scoped to viewing/reviewing "
        "ProformaInvoice/QuoteRequest and setting custom tariffs — not "
        "full admin access."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name=ACCOUNTANT_GROUP_NAME)
        self.stdout.write(
            self.style.SUCCESS(
                f"✔ مجموعة «{ACCOUNTANT_GROUP_NAME}» "
                + ("أُنشئت." if created else "موجودة مسبقا.")
            )
        )

        wanted = []
        missing = []
        for app_label, model_name, actions in SCOPED_PERMISSIONS:
            for action in actions:
                codename = f"{action}_{model_name}"
                try:
                    wanted.append(
                        Permission.objects.get(
                            content_type__app_label=app_label,
                            codename=codename,
                        )
                    )
                except Permission.DoesNotExist:
                    missing.append(f"{app_label}.{codename}")

        group.permissions.set(wanted)

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ تم ضبط {len(wanted)} صلاحية لمجموعة «{ACCOUNTANT_GROUP_NAME}»: "
                + ", ".join(sorted(p.codename for p in wanted))
            )
        )
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    "⚠ صلاحيات غير موجودة (تحقق من الهجرات/أسماء النماذج): "
                    + ", ".join(missing)
                )
            )
