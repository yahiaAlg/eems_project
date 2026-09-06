"""
Seed sample VIP/Normal client accounts and an Accountant staff account for
local dev/demo data (TODO 9.2).

This gives anyone setting up the project locally a ready-made account for
every role exercised by the manual test matrix in
`docs/TESTING_ACCOUNTS_AND_CHECKOUT.md`, without hand-registering through
`/account/register/` and hand-activating from the admin each time:

    - a VIP individual client (base prices visible, no trainer/legal gate)
    - a VIP enterprise client, with every Phase 2.1 legal field filled in,
      so the Phase 2.3 proforma gate is already satisfied — ready to walk
      straight into the Phase 5.1 "Request Proforma" flow
    - a Normal (non-VIP) individual client
    - a Normal (non-VIP) enterprise client, legal fields left mostly blank
      on purpose (Phase 2.3's gate only ever applies to VIP enterprises, so
      this doubles as a check that a non-VIP checkout never demands them)
    - an "Accountant" staff account (TODO 6.1 group, no superuser rights)

Runs `seed_account_groups` and `seed_accountant_group` first so the "VIP" /
"Normal" groups exist before any `Client` is saved (`accounts.signals`
syncs group membership from `Client.is_vip` on save, silently no-oping if
the groups are missing) and so the "Accountant" group already carries its
scoped permissions when the accountant account is attached to it.

Idempotent: safe to run multiple times. Existing accounts are left as-is
(profile fields refreshed, password never reset — same convention as
`seed_data.seed_admin_user`) so re-running never clobbers demo data
someone has since edited by hand while testing.

Override the shared demo password via the `EEMS_DEMO_PASSWORD` env var
before running if you don't want the default.

Usage:
    python manage.py seed_demo_users
"""

import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.management.commands.seed_accountant_group import (
    ACCOUNTANT_GROUP_NAME,
)
from enrollment.models import Client

DEMO_PASSWORD_ENV = "EEMS_DEMO_PASSWORD"
DEFAULT_DEMO_PASSWORD = "Demo2026*"

# (username, email, password_env_default_key unused — single shared password)
DEMO_CLIENTS = [
    {
        "username": "vip_individuel",
        "email": "vip.individuel@demo.eems.dz",
        "client_type": "individual",
        "is_vip": True,
        "client_fields": {
            "phone": "0555010101",
            "full_name": "زهية بلقاسمي",
            "wilaya": "سطيف",
            "address": "حي 08 ماي 1945، سطيف",
            "gender": "f",
            "education_level": "ليسانس",
        },
    },
    {
        "username": "vip_entreprise",
        "email": "vip.entreprise@demo.eems.dz",
        "client_type": "enterprise",
        "is_vip": True,
        "client_fields": {
            "phone": "0555020202",
            "company_name": "شركة الأطلس للأشغال العمومية",
            "wilaya": "سطيف",
            "address": "المنطقة الصناعية، سطيف",
            "sector": "الأشغال العمومية والبناء",
            "responsible_name": "عبد الحق مرابط",
            "responsible_position": "مدير الموارد البشرية",
            # Phase 2.1 legal/accounting fields — filled in on purpose so
            # this account already clears the Phase 2.3 proforma gate.
            "forme_juridique": "SARL",
            "trade_register_number": "19/00-1234567 B 20",
            "nif": "000119012345678",
            "nis": "001119012345",
            "article_imposition": "19012345678",
            "rib": "00799999123456789012",
            "tva_exempt": False,
            "postal_code": "19000",
            "city": "سطيف",
            "website": "https://atlas-tp-demo.example",
            "main_contact_name": "سميرة بوعزيز",
            "main_contact_phone": "0661020304",
            "main_contact_email": "facturation@atlas-tp-demo.example",
        },
    },
    {
        "username": "client_normal",
        "email": "client.normal@demo.eems.dz",
        "client_type": "individual",
        "is_vip": False,
        "client_fields": {
            "phone": "0555030303",
            "full_name": "كريم حمداني",
            "wilaya": "سطيف",
            "address": "حي العالية، سطيف",
            "gender": "m",
            "education_level": "تقني سامي",
        },
    },
    {
        "username": "entreprise_normale",
        "email": "entreprise.normale@demo.eems.dz",
        "client_type": "enterprise",
        "is_vip": False,
        "client_fields": {
            "phone": "0555040404",
            "company_name": "مؤسسة النور للنقل",
            "wilaya": "سطيف",
            "sector": "النقل واللوجستيك",
            "responsible_name": "ياسين شريط",
            "responsible_position": "مسؤول التكوين",
            # Left mostly blank on purpose — Phase 2.3's legal-info gate
            # only ever applies to VIP enterprises (Client.is_vip=False
            # here), so this account also demonstrates that the non-VIP
            # "Request Quote" checkout never demands these fields.
        },
    },
]


class Command(BaseCommand):
    help = (
        "Seed demo VIP/Normal individual+enterprise client accounts and an "
        "Accountant staff account for local dev/demo data (TODO 9.2)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        # Groups must exist before any Client is saved below, so
        # `accounts.signals.sync_vip_group_membership` has something to
        # sync into, and before the accountant account is attached to
        # "Accountant" so it already carries its scoped permissions.
        call_command("seed_account_groups")
        call_command("seed_accountant_group")

        password = os.environ.get(DEMO_PASSWORD_ENV, DEFAULT_DEMO_PASSWORD)
        User = get_user_model()

        for spec in DEMO_CLIENTS:
            self._seed_demo_client(User, spec, password)

        self._seed_accountant_user(User, password)

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ حسابات تجريبية جاهزة (كلمة المرور الافتراضية لكل الحسابات "
                f"الجديدة: {password} — عدّلها عبر متغير البيئة "
                f"{DEMO_PASSWORD_ENV} قبل التشغيل إن أردت غير ذلك)."
            )
        )

    def _seed_demo_client(self, User, spec, password):
        username = spec["username"]
        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={"email": spec["email"], "is_active": True},
        )
        if user_created:
            user.set_password(password)
            user.save()
        elif not user.is_active:
            # A demo account should always be usable to log in, even if
            # someone previously deactivated it while testing Phase 1.
            user.is_active = True
            user.save(update_fields=["is_active"])

        defaults = {
            "client_type": spec["client_type"],
            "is_vip": spec["is_vip"],
            "account_status": "active",
            "user": user,
            **spec["client_fields"],
        }
        client, client_created = Client.objects.get_or_create(
            user=user, defaults=defaults
        )
        if not client_created:
            # Idempotent refresh: keep demo data matching this command's
            # spec (e.g. re-running after the VIP enterprise's legal
            # fields were extended) without touching anything the tester
            # may have changed on *other* clients.
            changed = False
            for field, value in defaults.items():
                if field == "user":
                    continue
                if getattr(client, field) != value:
                    setattr(client, field, value)
                    changed = True
            if changed:
                client.save()

        label = client.display_name
        role = "VIP" if spec["is_vip"] else "عادي"
        kind = "مؤسسة" if spec["client_type"] == "enterprise" else "فرد"
        self.stdout.write(
            self.style.SUCCESS(
                f"✔ زبون تجريبي {role} ({kind}): {username} — {label} "
                + ("[جديد]" if user_created else "[موجود مسبقا]")
            )
        )

    def _seed_accountant_user(self, User, password):
        username = "comptable"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": "comptable@demo.eems.dz",
                "is_active": True,
                "is_staff": True,
            },
        )
        if created:
            user.set_password(password)
            user.save()
        elif not user.is_staff:
            # An Accountant must be able to reach /admin/ at all — see
            # seed_accountant_group's docstring on is_staff being separate
            # from the group's scoped model permissions.
            user.is_staff = True
            user.save(update_fields=["is_staff"])

        from django.contrib.auth.models import Group

        accountant_group = Group.objects.get(name=ACCOUNTANT_GROUP_NAME)
        user.groups.add(accountant_group)

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ حساب محاسب تجريبي: {username} — عضو في مجموعة "
                f"«{ACCOUNTANT_GROUP_NAME}» "
                + ("[جديد]" if created else "[موجود مسبقا]")
            )
        )
