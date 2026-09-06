from django.contrib.auth.models import Group, User
from django.core import mail
from django.test import TestCase

from enrollment.models import Client

from .services import activate_client_and_send_credentials


class RegistrationTestCase(TestCase):
    """TODO 1.3 — public registration creates an inactive User + a
    pending Client, and notifies the admin inbox. No usable password is
    ever set at this stage (TODO 1.4 does that later)."""

    def _valid_individual_data(self, **overrides):
        data = {
            "client_type": "individual",
            "phone": "0770123456",
            "email": "person@example.com",
            "wilaya": "سطيف",
            "full_name": "Ahmed Belaid",
            "agree_terms": True,
            "website": "",
        }
        data.update(overrides)
        return data

    def _valid_enterprise_data(self, **overrides):
        data = {
            "client_type": "enterprise",
            "phone": "0660123456",
            "email": "biz@example.com",
            "company_name": "Acme SARL",
            "agree_terms": True,
            "website": "",
        }
        data.update(overrides)
        return data

    def test_individual_registration_creates_inactive_user_and_pending_client(self):
        resp = self.client.post("/account/register/", self._valid_individual_data())
        self.assertRedirects(resp, "/account/register/merci/")

        user = User.objects.get(username="0770123456")
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())

        client = Client.objects.get(user=user)
        self.assertEqual(client.account_status, "pending")
        self.assertEqual(client.client_type, "individual")
        self.assertEqual(client.full_name, "Ahmed Belaid")

    def test_enterprise_registration_creates_enterprise_client(self):
        self.client.post("/account/register/", self._valid_enterprise_data())
        client = Client.objects.get(phone="0660123456")
        self.assertEqual(client.client_type, "enterprise")
        self.assertEqual(client.company_name, "Acme SARL")
        self.assertEqual(client.account_status, "pending")

    def test_registration_notifies_admin(self):
        mail.outbox = []
        self.client.post("/account/register/", self._valid_individual_data())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("support@excellance-ms.dz", mail.outbox[0].to)

    def test_duplicate_phone_rejected(self):
        self.client.post("/account/register/", self._valid_individual_data())
        resp = self.client.post("/account/register/", self._valid_individual_data(
            email="other@example.com"
        ))
        self.assertEqual(resp.status_code, 200)  # re-rendered with form error
        self.assertEqual(User.objects.filter(username="0770123456").count(), 1)

    def test_honeypot_rejects_bots(self):
        resp = self.client.post(
            "/account/register/", self._valid_individual_data(website="http://spam.com")
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Client.objects.filter(phone="0770123456").exists())

    def test_enterprise_requires_company_name(self):
        resp = self.client.post(
            "/account/register/", self._valid_enterprise_data(company_name="")
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Client.objects.filter(phone="0660123456").exists())


class ActivationTestCase(TestCase):
    """TODO 1.4 — the "Activate & send credentials" action: generates a
    password, activates the linked user, flips account_status, and emails
    the credentials exactly once. The plaintext password is never stored
    or exposed anywhere other than that email."""

    def setUp(self):
        self.user = User.objects.create(
            username="0770000000", email="client@example.com", is_active=False
        )
        self.user.set_unusable_password()
        self.user.save()
        self.client_obj = Client.objects.create(
            user=self.user, client_type="individual", full_name="Test Client",
            phone="0770000000", email="client@example.com", account_status="pending",
        )

    def test_activation_sets_active_and_status(self):
        mail.outbox = []
        ok, _msg = activate_client_and_send_credentials(self.client_obj)
        self.assertTrue(ok)
        self.user.refresh_from_db()
        self.client_obj.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.has_usable_password())
        self.assertEqual(self.client_obj.account_status, "active")

    def test_activation_emails_credentials_exactly_once(self):
        mail.outbox = []
        activate_client_and_send_credentials(self.client_obj)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("client@example.com", mail.outbox[0].to)

    def test_activated_user_can_login_with_generated_password(self):
        # Capture the password the same (only) way it's ever exposed: the
        # outgoing email body — never read off the User object directly.
        mail.outbox = []
        activate_client_and_send_credentials(self.client_obj)
        html_body = mail.outbox[0].alternatives[0][0]
        import re
        # secrets.token_urlsafe(12) chars: alnum, -, _
        candidates = re.findall(r"[A-Za-z0-9_-]{14,}", html_body)
        self.user.refresh_from_db()
        found = any(self.user.check_password(c) for c in candidates)
        self.assertTrue(found, "generated password not found/matching in credentials email")

    def test_no_login_link_without_user(self):
        orphan = Client.objects.create(
            client_type="individual", full_name="No User", phone="0000000000",
        )
        ok, _msg = activate_client_and_send_credentials(orphan)
        self.assertFalse(ok)


class LoginGateTestCase(TestCase):
    """TODO 1.5 — login is blocked with a clear message while
    is_active=False (pending approval) and allowed once activated."""

    def setUp(self):
        self.user = User.objects.create(username="0771111111", is_active=False)
        self.user.set_unusable_password()
        self.user.save()
        self.client_obj = Client.objects.create(
            user=self.user, client_type="individual", full_name="Pending Guy",
            phone="0771111111", account_status="pending",
        )

    def test_pending_user_login_blocked(self):
        self.user.set_password("somepass123")
        self.user.save()
        resp = self.client.post("/account/login/", {
            "username": "0771111111", "password": "somepass123",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["user"].is_authenticated)

    def test_rejected_user_gets_distinct_message(self):
        self.client_obj.account_status = "rejected"
        self.client_obj.save()
        self.user.set_password("somepass123")
        self.user.save()
        resp = self.client.post("/account/login/", {
            "username": "0771111111", "password": "somepass123",
        })
        form = resp.context["form"]
        self.assertIn("رفض", str(form.errors))

    def test_activated_user_can_login(self):
        activate_client_and_send_credentials(self.client_obj)
        # Password is random; set a known one post-activation to verify
        # the door is actually open (is_active flipped, form allows it).
        self.user.refresh_from_db()
        self.user.set_password("knownpass123")
        self.user.save()
        logged_in = self.client.login(username="0771111111", password="knownpass123")
        self.assertTrue(logged_in)


class VipGroupSyncTestCase(TestCase):
    """TODO 1.7 — Client.is_vip stays the single source of truth; the
    "VIP"/"Normal" Groups mirror it automatically via the post_save
    signal, for staff who work from Users/Groups in the admin."""

    def setUp(self):
        Group.objects.get_or_create(name="VIP")
        Group.objects.get_or_create(name="Normal")
        self.user = User.objects.create(username="0772222222", is_active=True)
        self.client_obj = Client.objects.create(
            user=self.user, client_type="individual", full_name="Sync Test",
            phone="0772222222", account_status="active", is_vip=False,
        )

    def test_new_normal_client_lands_in_normal_group(self):
        self.assertTrue(self.user.groups.filter(name="Normal").exists())
        self.assertFalse(self.user.groups.filter(name="VIP").exists())

    def test_flipping_is_vip_moves_group_membership(self):
        self.client_obj.is_vip = True
        self.client_obj.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.groups.filter(name="VIP").exists())
        self.assertFalse(self.user.groups.filter(name="Normal").exists())

    def test_flipping_back_reverts_group(self):
        self.client_obj.is_vip = True
        self.client_obj.save()
        self.client_obj.is_vip = False
        self.client_obj.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.groups.filter(name="Normal").exists())
        self.assertFalse(self.user.groups.filter(name="VIP").exists())

    def test_client_with_no_user_does_not_error(self):
        # Legacy walk-in client, no linked login — signal must be a no-op,
        # not raise.
        orphan = Client.objects.create(
            client_type="individual", full_name="No Login", phone="0000000001",
        )
        orphan.is_vip = True
        orphan.save()  # must not raise


class DashboardAuthRequiredTestCase(TestCase):
    """TODO 1.8 — the old phone/session dashboard login is retired;
    /mon-espace/ now requires request.user via @login_required and
    redirects anonymous visitors to /account/login/."""

    def test_anonymous_dashboard_redirects_to_login(self):
        resp = self.client.get("/mon-espace/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/account/login/", resp.url)

    def test_authenticated_user_reaches_dashboard(self):
        user = User.objects.create_user(username="0773333333", password="x", is_active=True)
        Client.objects.create(
            user=user, client_type="individual", full_name="Dash User",
            phone="0773333333", account_status="active",
        )
        self.client.force_login(user)
        resp = self.client.get("/mon-espace/")
        self.assertEqual(resp.status_code, 200)


class SeedDemoUsersCommandTestCase(TestCase):
    """TODO 9.2 — the seed command must run cleanly (groups first, then
    demo clients) and actually produce the VIP/Normal/Accountant fixture
    set it documents, including a VIP enterprise with a *complete* legal
    profile (TODO 2.3) and idempotent re-runs."""

    def test_seed_command_runs_and_creates_expected_roles(self):
        from django.core.management import call_command

        call_command("seed_demo_users")

        vip_enterprise = Client.objects.filter(
            client_type="enterprise", is_vip=True
        ).first()
        self.assertIsNotNone(vip_enterprise)
        self.assertTrue(vip_enterprise.has_complete_legal_info)
        self.assertFalse(vip_enterprise.needs_legal_info_for_proforma)

        self.assertTrue(Client.objects.filter(is_vip=True, client_type="individual").exists())
        self.assertTrue(Client.objects.filter(is_vip=False, client_type="individual").exists())
        self.assertTrue(Client.objects.filter(is_vip=False, client_type="enterprise").exists())

        self.assertTrue(Group.objects.filter(name="VIP").exists())
        self.assertTrue(Group.objects.filter(name="Normal").exists())
        accountant_group = Group.objects.filter(name="Accountant").first()
        self.assertIsNotNone(accountant_group)
        self.assertTrue(
            User.objects.filter(groups=accountant_group, is_staff=True).exists()
        )

    def test_seed_command_is_idempotent(self):
        from django.core.management import call_command

        call_command("seed_demo_users")
        count_after_first = Client.objects.count()
        call_command("seed_demo_users")  # must not raise or duplicate
        self.assertEqual(Client.objects.count(), count_after_first)


class PasswordResetFlowTestCase(TestCase):
    """TODO 1.6 — end-to-end: request reset -> branded email sent with a
    working link -> submitting a new password there actually changes it
    and the user can log in with it."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="0774444444", email="reset@example.com",
            password="oldpassword123", is_active=True,
        )
        Client.objects.create(
            user=self.user, client_type="individual", full_name="Reset Me",
            phone="0774444444", email="reset@example.com", account_status="active",
        )

    def test_reset_request_sends_branded_email(self):
        mail.outbox = []
        resp = self.client.post(
            "/account/password-reset/", {"email": "reset@example.com"}
        )
        self.assertRedirects(resp, "/account/password-reset/done/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset@example.com", mail.outbox[0].to)
        self.assertTrue(mail.outbox[0].alternatives)  # has an HTML branded part

    def test_full_reset_flow_changes_password(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        # First hit with the real token redirects to the session-based
        # "set-password" URL Django's view uses internally.
        resp = self.client.get(
            f"/account/password-reset/{uid}/{token}/", follow=True
        )
        self.assertEqual(resp.status_code, 200)

        resp2 = self.client.post(
            resp.wsgi_request.path,
            {"new_password1": "BrandNewPass123!", "new_password2": "BrandNewPass123!"},
        )
        self.assertRedirects(resp2, "/account/password-reset/complete/")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNewPass123!"))
        self.assertFalse(self.user.check_password("oldpassword123"))

    def test_unknown_email_does_not_leak_existence(self):
        mail.outbox = []
        resp = self.client.post(
            "/account/password-reset/", {"email": "doesnotexist@example.com"}
        )
        # Django's default behaviour: same redirect either way, no email sent.
        self.assertRedirects(resp, "/account/password-reset/done/")
        self.assertEqual(len(mail.outbox), 0)
