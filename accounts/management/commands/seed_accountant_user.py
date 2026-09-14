"""
Seed a single "Accountant" staff account, deliberately separate and
minimal compared to `seed_demo_users`.

`seed_accountant_group` stops at the Group + permissions on purpose (see
its own docstring: "Adding specific users to the group is a normal admin
action"). That's fine for local dev, where `seed_demo_users` already
creates a `comptable` account alongside four demo clients. But now that a
confirmed Enrollment/purchase emails every Accountant-group member with
an address (`enrollment/services.py::notify_accountants_of_confirmed_purchase`),
a staging/production environment that never runs the full demo seed
still needs *someone* in that group with a real email — this command is
the minimal way to get there without pulling in the VIP/Normal demo
clients too.

`seed_demo_users` now delegates its own accountant-account step to this
command rather than duplicating the logic.

Idempotent: safe to run multiple times. An existing account's
email/staff flag/group membership is refreshed on re-run; the password
is only set the first time the account is created (never reset).

Configure via env vars (all optional):
    EEMS_ACCOUNTANT_USERNAME  (default "comptable")
    EEMS_ACCOUNTANT_EMAIL     (default "comptable@eems.dz")
    EEMS_ACCOUNTANT_PASSWORD  (default "Demo2026*" — same default as
                               `seed_demo_users`' EEMS_DEMO_PASSWORD)

Usage:
    python manage.py seed_accountant_user
"""

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.management.commands.seed_accountant_group import (
    ACCOUNTANT_GROUP_NAME,
)

USERNAME_ENV = "EEMS_ACCOUNTANT_USERNAME"
EMAIL_ENV = "EEMS_ACCOUNTANT_EMAIL"
PASSWORD_ENV = "EEMS_ACCOUNTANT_PASSWORD"

DEFAULT_USERNAME = "comptable"
DEFAULT_EMAIL = "comptable@eems.dz"
DEFAULT_PASSWORD = "Demo2026*"


class Command(BaseCommand):
    help = (
        "Seed a single Accountant staff account attached to the "
        "'Accountant' group — minimal, no demo clients (see "
        "seed_demo_users for the full local-dev fixture set)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        # The group (and its scoped permissions) must exist before this
        # account is attached to it.
        call_command("seed_accountant_group")

        username = os.environ.get(USERNAME_ENV, DEFAULT_USERNAME)
        email = os.environ.get(EMAIL_ENV, DEFAULT_EMAIL)
        password = os.environ.get(PASSWORD_ENV, DEFAULT_PASSWORD)

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_active": True, "is_staff": True},
        )

        if created:
            user.set_password(password)
            user.save()
            state = "جديد"
        else:
            # Idempotent refresh — an Accountant account must always be
            # active, staff (to reach /admin/ at all, see
            # seed_accountant_group's docstring), and carry the
            # currently-configured email, without ever touching its
            # password once it exists.
            changed_fields = []
            if user.email != email:
                user.email = email
                changed_fields.append("email")
            if not user.is_staff:
                user.is_staff = True
                changed_fields.append("is_staff")
            if not user.is_active:
                user.is_active = True
                changed_fields.append("is_active")
            if changed_fields:
                user.save(update_fields=changed_fields)
            state = "محدَّث" if changed_fields else "موجود مسبقا"

        group = Group.objects.get(name=ACCOUNTANT_GROUP_NAME)
        user.groups.add(group)

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ حساب محاسب: {username} <{email}> — عضو في مجموعة "
                f"«{ACCOUNTANT_GROUP_NAME}» [{state}]"
            )
        )
