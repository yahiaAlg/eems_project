from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Cart,
    CartItem,
    Client,
    Comment,
    Enquiry,
    Enrollment,
    EnrollmentNote,
    EnrollmentParticipant,
    FormationSession,
    Offering,
    Participant,
    ProformaInvoice,
    ProformaInvoiceItem,
    QuoteRequest,
    QuoteRequestItem,
    SessionChangeRequest,
    STATUS_CHOICES,
    WishlistItem,
)


class PricingVisibilityTestCase(TestCase):
    """TODO 8.3 — locks in, as an automated regression test, the Phase 3
    pricing-visibility rule ("non-VIP and anonymous visitors must not see
    prices at all") across every dashboard-space page introduced/rebuilt
    in Phase 8: the metrics page (8.2), My Purchases / request history
    (8.1), and the printable proforma/quote documents (5.2/6.4) a client
    can reach from there.

    Each non-VIP fixture below is deliberately built with priced data
    (`unit_price`/`line_total`/`billing_basis` set directly at the ORM
    level, bypassing the view/form-layer rules from TODO 4.1 that would
    normally stop a non-VIP cart line from ever being priced in the first
    place). This isolates what's actually being checked here: that every
    template gates its price display on `client.is_vip` /
    `_can_view_prices(request)` rather than merely happening to have no
    priced data to show — so the rule keeps holding even if a future bug
    elsewhere lets priced data reach a non-VIP client's records.
    """

    def setUp(self):
        session = FormationSession.objects.create(
            name="Session", slug="session", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session,
            code="OFF1",
            title="Offering 1",
            duration_months=3,
            is_active=True,
            price_per_day=Decimal("50000.00"),
            price_per_participant=Decimal("15000.00"),
        )

    def _make_client(self, username, is_vip):
        user = User.objects.create_user(username=username, password="x", is_active=True)
        client = Client.objects.create(
            user=user,
            client_type="individual",
            phone="0555000000",
            is_vip=is_vip,
            account_status="active",
        )
        return user, client

    def _login(self, user):
        self.client.force_login(user)

    # -- dashboard overview (Phase 8.1) --------------------------------

    def test_dashboard_hides_cart_total_for_non_vip_even_when_priced(self):
        user, client = self._make_client("nonvip_dash", is_vip=False)
        cart = Cart.get_active_for_client(client)
        # Priced directly at the ORM level — a non-VIP client's cart form
        # should never set this, but the template must not rely on that.
        CartItem.objects.create(
            cart=cart, offering=self.offering, participant_count=2,
            billing_basis="per_participant",
        )
        self._login(user)
        content = self.client.get("/mon-espace/").content.decode()
        self.assertNotIn("15 000 دج", content)
        self.assertNotIn("30 000 دج", content)

    def test_dashboard_shows_cart_total_for_vip(self):
        user, client = self._make_client("vip_dash", is_vip=True)
        cart = Cart.get_active_for_client(client)
        CartItem.objects.create(
            cart=cart, offering=self.offering, participant_count=2,
            billing_basis="per_participant",
        )
        self._login(user)
        content = self.client.get("/mon-espace/").content.decode()
        self.assertIn("30 000 دج", content)

    # -- metrics page (Phase 8.2) ---------------------------------------

    def test_metrics_page_has_no_spend_widget_for_non_vip(self):
        user, client = self._make_client("nonvip_metrics", is_vip=False)
        # Even if a ProformaInvoice somehow exists on a non-VIP record
        # (e.g. after a VIP downgrade), the VIP-only spend chart must not
        # render for a currently-non-VIP client.
        invoice = ProformaInvoice.objects.create(client=client, status="confirmed")
        ProformaInvoiceItem.objects.create(
            invoice=invoice, offering=self.offering, offering_code="OFF1",
            offering_title="Offering 1", billing_basis="per_participant",
            participant_count=2, unit_price=Decimal("15000.00"),
            line_total=Decimal("30000.00"),
        )
        self._login(user)
        content = self.client.get("/mon-espace/statistiques/").content.decode()
        self.assertNotIn('<canvas id="monthlySpendChart">', content)
        self.assertNotIn("30000.0", content)

    def test_metrics_page_has_spend_widget_for_vip(self):
        user, client = self._make_client("vip_metrics", is_vip=True)
        invoice = ProformaInvoice.objects.create(client=client, status="confirmed")
        ProformaInvoiceItem.objects.create(
            invoice=invoice, offering=self.offering, offering_code="OFF1",
            offering_title="Offering 1", billing_basis="per_participant",
            participant_count=2, unit_price=Decimal("15000.00"),
            line_total=Decimal("30000.00"),
        )
        self._login(user)
        content = self.client.get("/mon-espace/statistiques/").content.decode()
        self.assertIn('<canvas id="monthlySpendChart">', content)
        self.assertIn("30000.0", content)

    # -- My Purchases / request history (Phase 8.1) ----------------------

    def test_my_purchases_hides_proforma_total_for_non_vip(self):
        user, client = self._make_client("nonvip_purchases", is_vip=False)
        invoice = ProformaInvoice.objects.create(client=client, status="confirmed")
        ProformaInvoiceItem.objects.create(
            invoice=invoice, offering=self.offering, offering_code="OFF1",
            offering_title="Offering 1", billing_basis="per_participant",
            participant_count=2, unit_price=Decimal("15000.00"),
            line_total=Decimal("30000.00"),
        )
        self._login(user)
        content = self.client.get("/mon-espace/achats/").content.decode()
        self.assertNotIn("30 000 دج", content)

    def test_my_purchases_shows_proforma_total_for_vip(self):
        user, client = self._make_client("vip_purchases", is_vip=True)
        invoice = ProformaInvoice.objects.create(client=client, status="confirmed")
        ProformaInvoiceItem.objects.create(
            invoice=invoice, offering=self.offering, offering_code="OFF1",
            offering_title="Offering 1", billing_basis="per_participant",
            participant_count=2, unit_price=Decimal("15000.00"),
            line_total=Decimal("30000.00"),
        )
        self._login(user)
        content = self.client.get("/mon-espace/achats/").content.decode()
        self.assertIn("30 000 دج", content)

    def test_my_purchases_shows_quote_total_once_priced_for_non_vip(self):
        """Not a Phase 3 violation: once the accountant prices a non-VIP
        client's own quote (TODO 6.2/6.3), that client is *meant* to see
        that specific figure (TODO 6.4) — this is the client's own final
        tariff, not the VIP-only catalog base price."""
        user, client = self._make_client("nonvip_quote", is_vip=False)
        quote = QuoteRequest.objects.create(client=client, status="priced")
        QuoteRequestItem.objects.create(
            quote=quote, offering=self.offering, offering_code="OFF1",
            offering_title="Offering 1", participant_count=2,
            billing_basis="per_participant", unit_price=Decimal("12000.00"),
        )
        self._login(user)
        content = self.client.get("/mon-espace/achats/").content.decode()
        self.assertIn("24 000 دج", content)

    # -- proforma / quote printable detail pages -------------------------

    def test_proforma_print_is_not_reachable_by_another_client(self):
        _owner_user, owner = self._make_client("vip_owner", is_vip=True)
        invoice = ProformaInvoice.objects.create(client=owner, status="confirmed")
        ProformaInvoiceItem.objects.create(
            invoice=invoice, offering=self.offering, offering_code="OFF1",
            offering_title="Offering 1", billing_basis="per_day",
            participant_count=1, unit_price=Decimal("50000.00"),
            line_total=Decimal("50000.00"),
        )
        other_user, _other = self._make_client("other_client", is_vip=False)
        self._login(other_user)
        resp = self.client.get(f"/mon-espace/proforma/{invoice.pk}/")
        self.assertEqual(resp.status_code, 404)

    def test_quote_print_hides_tariff_while_still_pending(self):
        user, client = self._make_client("nonvip_pending_quote", is_vip=False)
        quote = QuoteRequest.objects.create(client=client, status="pending")
        QuoteRequestItem.objects.create(
            quote=quote, offering=self.offering, offering_code="OFF1",
            offering_title="Offering 1", participant_count=1,
        )
        self._login(user)
        resp = self.client.get(f"/mon-espace/devis/{quote.pk}/", follow=True)
        self.assertEqual(resp.status_code, 200)
        # Redirected back to My Purchases with an explanatory message —
        # never rendered the (empty) tariff document itself.
        self.assertTemplateNotUsed(resp, "enrollment/documents/quote_print.html")


class ProformaLegalInfoGateTestCase(TestCase):
    """TODO 2.3 — regression coverage for the previously-confirmed gap: a
    VIP enterprise client with an incomplete legal profile must be blocked
    from submitting a "Request Proforma", both server-side (direct
    GET/POST to the view) and in the cart's UI (the button is replaced by
    an explanatory prompt linking to the profile page)."""

    def setUp(self):
        session = FormationSession.objects.create(
            name="Session", slug="session-gate", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session,
            code="OFFGATE",
            title="Offering Gate",
            duration_months=3,
            is_active=True,
            price_per_day=Decimal("50000.00"),
            price_per_participant=Decimal("15000.00"),
        )

    def _make_vip_enterprise(self, username, *, complete_legal_info):
        user = User.objects.create_user(username=username, password="x", is_active=True)
        extra = {}
        if complete_legal_info:
            extra = dict(
                trade_register_number="RC123",
                forme_juridique="SARL",
                nif="NIF123",
                nis="NIS123",
                article_imposition="ART123",
                rib="RIB123",
                address="Some address",
                postal_code="19000",
                city="Sétif",
                main_contact_name="Contact",
                main_contact_phone="0555000000",
                main_contact_email="contact@example.com",
            )
        client = Client.objects.create(
            user=user,
            client_type="enterprise",
            company_name="Enterprise Co",
            phone="0555000000",
            is_vip=True,
            account_status="active",
            **extra,
        )
        return user, client

    def _add_cart_item(self, client):
        cart = Cart.get_active_for_client(client)
        return CartItem.objects.create(
            cart=cart, offering=self.offering, participant_count=1,
            billing_basis="per_day",
        )

    def test_incomplete_legal_info_blocks_proforma_get(self):
        user, client = self._make_vip_enterprise("gate_get", complete_legal_info=False)
        self._add_cart_item(client)
        self.client.force_login(user)
        resp = self.client.get("/mon-espace/panier/proforma/", follow=True)
        self.assertRedirects(resp, "/mon-espace/profil/")
        self.assertEqual(ProformaInvoice.objects.filter(client=client).count(), 0)

    def test_incomplete_legal_info_blocks_proforma_post(self):
        user, client = self._make_vip_enterprise("gate_post", complete_legal_info=False)
        self._add_cart_item(client)
        self.client.force_login(user)
        resp = self.client.post("/mon-espace/panier/proforma/", {}, follow=True)
        self.assertRedirects(resp, "/mon-espace/profil/")
        self.assertEqual(ProformaInvoice.objects.filter(client=client).count(), 0)

    def test_complete_legal_info_allows_proforma_page(self):
        user, client = self._make_vip_enterprise("gate_ok", complete_legal_info=True)
        self._add_cart_item(client)
        self.client.force_login(user)
        resp = self.client.get("/mon-espace/panier/proforma/")
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "enrollment/request_proforma.html")

    def test_cart_shows_gate_prompt_not_button_when_incomplete(self):
        user, client = self._make_vip_enterprise("gate_cart", complete_legal_info=False)
        self._add_cart_item(client)
        self.client.force_login(user)
        content = self.client.get("/mon-espace/panier/").content.decode()
        self.assertIn("proforma-legal-gate", content)
        self.assertIn("/mon-espace/profil/", content)
        self.assertNotIn('href="/mon-espace/panier/proforma/"', content)

    def test_cart_shows_button_when_complete(self):
        user, client = self._make_vip_enterprise("gate_cart_ok", complete_legal_info=True)
        self._add_cart_item(client)
        self.client.force_login(user)
        content = self.client.get("/mon-espace/panier/").content.decode()
        self.assertNotIn("proforma-legal-gate", content)
        self.assertIn('href="/mon-espace/panier/proforma/"', content)

    def test_non_enterprise_vip_never_gated(self):
        """Individuals can't have missing 'enterprise' legal fields — the
        gate must never apply to them, regardless of is_vip."""
        user = User.objects.create_user(username="gate_indiv", password="x", is_active=True)
        client = Client.objects.create(
            user=user, client_type="individual", full_name="Fulan",
            phone="0555000001", is_vip=True, account_status="active",
        )
        self.assertFalse(client.needs_legal_info_for_proforma)
        self._add_cart_item(client)
        self.client.force_login(user)
        resp = self.client.get("/mon-espace/panier/proforma/")
        self.assertEqual(resp.status_code, 200)


class CartWishlistCheckoutTestCase(TestCase):
    """TODO 4.1–4.4 / 5.3–5.4 / 6.2–6.3 — cross-cutting checks that
    aren't covered by PricingVisibilityTestCase: server-side trainer
    enforcement for non-VIP carts (not just template hiding), wishlist
    move-to-cart, and cart lock/reopen semantics on checkout."""

    def setUp(self):
        session = FormationSession.objects.create(
            name="Session2", slug="session2", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session, code="OFF2", title="Offering 2",
            duration_months=3, is_active=True,
            price_per_day=Decimal("40000.00"),
            price_per_participant=Decimal("10000.00"),
        )
        from .models import Formateur
        self.trainer = Formateur.objects.create(full_name="Trainer X", is_active=True)

    def _make_client(self, username, is_vip):
        user = User.objects.create_user(username=username, password="x", is_active=True)
        client = Client.objects.create(
            user=user, client_type="individual", full_name="T",
            phone="0555000111", is_vip=is_vip, account_status="active",
        )
        return user, client

    def test_non_vip_cannot_set_trainer_via_crafted_post(self):
        """Even if a non-VIP client crafts a POST with a `trainer` field
        (the form drops it entirely for non-VIP, TODO 4.1), the view must
        not let a trainer end up set on the CartItem."""
        user, client = self._make_client("nonvip_trainer_hack", is_vip=False)
        cart = Cart.get_active_for_client(client)
        item = CartItem.objects.create(cart=cart, offering=self.offering, participant_count=1)
        self.client.force_login(user)
        resp = self.client.post(
            f"/mon-espace/panier/{item.pk}/modifier/",
            {
                f"item{item.pk}-participant_count": "2",
                f"item{item.pk}-trainer": str(self.trainer.pk),
                f"item{item.pk}-billing_basis": "per_day",
            },
        )
        item.refresh_from_db()
        self.assertIsNone(item.trainer)
        self.assertEqual(item.billing_basis, "")
        self.assertEqual(item.participant_count, 2)

    def test_wishlist_move_to_cart_transfers_and_removes(self):
        user, client = self._make_client("wish_move", is_vip=False)
        item = WishlistItem.objects.create(client=client, offering=self.offering)
        self.client.force_login(user)
        resp = self.client.post(f"/mon-espace/liste-souhaits/{item.pk}/panier/", follow=True)
        self.assertFalse(WishlistItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(
            CartItem.objects.filter(cart__client=client, offering=self.offering).exists()
        )

    def test_wishlist_scoped_to_owner(self):
        _u1, owner = self._make_client("wish_owner", is_vip=False)
        other_user, _other = self._make_client("wish_other", is_vip=False)
        item = WishlistItem.objects.create(client=owner, offering=self.offering)
        self.client.force_login(other_user)
        resp = self.client.post(f"/mon-espace/liste-souhaits/{item.pk}/panier/")
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(WishlistItem.objects.filter(pk=item.pk).exists())

    def test_quote_submission_locks_cart_and_opens_fresh_one(self):
        user, client = self._make_client("quote_lock", is_vip=False)
        cart = Cart.get_active_for_client(client)
        CartItem.objects.create(cart=cart, offering=self.offering, participant_count=1)
        self.client.force_login(user)
        self.client.post("/mon-espace/panier/devis/", follow=True)
        cart.refresh_from_db()
        self.assertEqual(cart.status, "converted")
        self.assertEqual(QuoteRequest.objects.filter(client=client).count(), 1)
        new_cart = Cart.get_active_for_client(client)
        self.assertNotEqual(new_cart.pk, cart.pk)
        self.assertEqual(new_cart.items_count, 0)

    def test_empty_cart_quote_request_rejected(self):
        user, client = self._make_client("quote_empty", is_vip=False)
        self.client.force_login(user)
        resp = self.client.post("/mon-espace/panier/devis/", follow=True)
        self.assertEqual(QuoteRequest.objects.filter(client=client).count(), 0)


class AccountantTarificationTestCase(TestCase):
    """TODO 6.1–6.3 — the Accountant group's scoped admin access, and the
    mark_as_priced gate: only fires when every line actually has a
    tariff, and sends the client the quote-priced notification."""

    def setUp(self):
        from django.contrib.auth.models import Group
        from django.core.management import call_command
        call_command("seed_accountant_group", verbosity=0)
        self.accountant_group = Group.objects.get(name="Accountant")
        self.accountant_user = User.objects.create_user(
            username="accountant1", password="x", is_staff=True,
        )
        self.accountant_user.groups.add(self.accountant_group)

        session = FormationSession.objects.create(
            name="Session3", slug="session3", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session, code="OFF3", title="Offering 3",
            duration_months=3, is_active=True,
        )
        user = User.objects.create_user(username="nonvip_tariff", password="x", is_active=True)
        self.nonvip_client = Client.objects.create(
            user=user, client_type="individual", full_name="T",
            phone="0555000222", is_vip=False, account_status="active",
        )

    def test_accountant_has_no_access_to_unrelated_models(self):
        self.assertFalse(
            self.accountant_user.has_perm("enrollment.change_client")
        )
        self.assertFalse(
            self.accountant_user.has_perm("enrollment.change_offering")
        )
        self.assertFalse(
            self.accountant_user.has_perm("auth.change_user")
        )

    def test_accountant_can_view_and_change_quoterequest(self):
        self.assertTrue(
            self.accountant_user.has_perm("enrollment.view_quoterequest")
        )
        self.assertTrue(
            self.accountant_user.has_perm("enrollment.change_quoterequest")
        )
        self.assertFalse(
            self.accountant_user.has_perm("enrollment.add_quoterequest")
        )
        self.assertFalse(
            self.accountant_user.has_perm("enrollment.delete_quoterequest")
        )

    def test_mark_as_priced_skips_incompletely_priced_quote(self):
        from django.contrib import admin as django_admin
        quote = QuoteRequest.objects.create(client=self.nonvip_client, status="pending")
        QuoteRequestItem.objects.create(
            quote=quote, offering=self.offering, offering_code="OFF3",
            offering_title="Offering 3", participant_count=1,
            # no billing_basis / unit_price set -> not priced
        )
        self.client.force_login(self.accountant_user)
        resp = self.client.post(
            "/admin/enrollment/quoterequest/",
            {
                "action": "mark_as_priced",
                "_selected_action": [quote.pk],
            },
            follow=True,
        )
        quote.refresh_from_db()
        self.assertEqual(quote.status, "pending")  # unchanged, gate held

    def test_mark_as_priced_moves_fully_priced_quote_and_notifies_client(self):
        quote = QuoteRequest.objects.create(
            client=self.nonvip_client, status="pending"
        )
        self.nonvip_client.email = "client_tariff@example.com"
        self.nonvip_client.save()
        QuoteRequestItem.objects.create(
            quote=quote, offering=self.offering, offering_code="OFF3",
            offering_title="Offering 3", participant_count=2,
            billing_basis="per_participant", unit_price=Decimal("9000.00"),
        )
        self.client.force_login(self.accountant_user)
        from django.core import mail
        mail.outbox = []
        self.client.post(
            "/admin/enrollment/quoterequest/",
            {"action": "mark_as_priced", "_selected_action": [quote.pk]},
            follow=True,
        )
        quote.refresh_from_db()
        self.assertEqual(quote.status, "priced")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("client_tariff@example.com", mail.outbox[0].to)


class ProfileFormSecurityTestCase(TestCase):
    """TODO 2.2 — a client editing their own profile must never be able
    to smuggle in a change to is_vip/account_status/phone/client_type via
    a crafted POST, even though those aren't rendered as form fields."""

    def _make_client(self, username, is_vip=False, client_type="individual"):
        user = User.objects.create_user(username=username, password="x", is_active=True)
        client = Client.objects.create(
            user=user, client_type=client_type,
            full_name="Original Name" if client_type == "individual" else "",
            company_name="Original Co" if client_type == "enterprise" else "",
            phone="0555000333", is_vip=is_vip, account_status="active",
        )
        return user, client

    def test_client_cannot_self_promote_to_vip(self):
        user, client = self._make_client("selfpromote", is_vip=False)
        self.client.force_login(user)
        self.client.post("/mon-espace/profil/", {
            "email": "new@example.com", "wilaya": "سطيف", "address": "",
            "full_name": "New Name", "is_vip": "on",
            "account_status": "active", "phone": "0000000000",
        })
        client.refresh_from_db()
        self.assertFalse(client.is_vip)
        self.assertEqual(client.phone, "0555000333")
        self.assertEqual(client.full_name, "New Name")  # legit field did save

    def test_client_cannot_change_own_account_status(self):
        user, client = self._make_client("selfstatus", is_vip=False)
        client.account_status = "pending"
        client.save()
        self.client.force_login(user)
        self.client.post("/mon-espace/profil/", {
            "email": "", "wilaya": "", "address": "", "full_name": "X",
            "account_status": "active",
        })
        client.refresh_from_db()
        self.assertEqual(client.account_status, "pending")

    def test_individual_profile_form_has_no_enterprise_fields(self):
        _user, client = self._make_client("indiv_form", client_type="individual")
        from .forms import ClientProfileForm
        form = ClientProfileForm(instance=client)
        self.assertNotIn("forme_juridique", form.fields)
        self.assertNotIn("nif", form.fields)
        self.assertIn("full_name", form.fields)

    def test_enterprise_profile_form_has_no_individual_fields(self):
        _user, client = self._make_client("ent_form", client_type="enterprise")
        from .forms import ClientProfileForm
        form = ClientProfileForm(instance=client)
        self.assertNotIn("full_name", form.fields)
        self.assertNotIn("birth_date", form.fields)
        self.assertIn("forme_juridique", form.fields)
        self.assertIn("nif", form.fields)


class PrintDocumentTestCase(TestCase):
    """TODO 5.2/6.4 — printable proforma/quote pages are plain HTML with
    print CSS (no PDF library), reachable by the owning client."""

    def setUp(self):
        session = FormationSession.objects.create(
            name="Session4", slug="session4", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session, code="OFF4", title="Offering 4",
            duration_months=3, is_active=True,
        )

    def test_proforma_print_has_print_css_and_no_pdf_header(self):
        user = User.objects.create_user(username="print_vip", password="x", is_active=True)
        client = Client.objects.create(
            user=user, client_type="individual", full_name="P",
            phone="0555000444", is_vip=True, account_status="active",
        )
        invoice = ProformaInvoice.objects.create(client=client, status="confirmed")
        ProformaInvoiceItem.objects.create(
            invoice=invoice, offering=self.offering, offering_code="OFF4",
            offering_title="Offering 4", billing_basis="per_day",
            participant_count=1, unit_price=Decimal("30000.00"),
            line_total=Decimal("30000.00"),
        )
        self.client.force_login(user)
        resp = self.client.get(f"/mon-espace/proforma/{invoice.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotEqual(resp.get("Content-Type", ""), "application/pdf")
        self.assertIn(b"@media print", resp.content)


class BonDeCommandeUploadE2ETestCase(TestCase):
    """TODO 5.1/5.2/7.3 — the optional bon-de-commande upload actually
    makes it onto the created ProformaInvoice end-to-end (not just unit
    validation), and a bad file is rejected without creating anything."""

    def setUp(self):
        session = FormationSession.objects.create(
            name="Session5", slug="session5", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session, code="OFF5", title="Offering 5",
            duration_months=3, is_active=True,
            price_per_day=Decimal("20000.00"),
        )
        user = User.objects.create_user(username="bdc_vip", password="x", is_active=True)
        self.client_obj = Client.objects.create(
            user=user, client_type="individual", full_name="BDC",
            phone="0555000555", is_vip=True, account_status="active",
        )
        self.user = user
        cart = Cart.get_active_for_client(self.client_obj)
        CartItem.objects.create(
            cart=cart, offering=self.offering, participant_count=1,
            billing_basis="per_day",
        )

    def test_valid_pdf_attaches_to_invoice(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        pdf_bytes = b"%PDF-1.4 fake but valid header content..."
        upload = SimpleUploadedFile("bon.pdf", pdf_bytes, content_type="application/pdf")
        self.client.force_login(self.user)
        item = CartItem.objects.get(cart__client=self.client_obj)
        resp = self.client.post(
            "/mon-espace/panier/proforma/",
            {f"item{item.pk}-billing_basis": "per_day", "bon_de_commande": upload},
            follow=True,
        )
        invoice = ProformaInvoice.objects.get(client=self.client_obj)
        self.assertTrue(invoice.bon_de_commande)
        self.assertEqual(invoice.bon_de_commande_original_name, "bon.pdf")

    def test_fake_extension_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # .pdf extension but content is plain text -> magic-byte check fails
        upload = SimpleUploadedFile(
            "bon.pdf", b"not really a pdf", content_type="application/pdf"
        )
        self.client.force_login(self.user)
        item = CartItem.objects.get(cart__client=self.client_obj)
        self.client.post(
            "/mon-espace/panier/proforma/",
            {f"item{item.pk}-billing_basis": "per_day", "bon_de_commande": upload},
        )
        self.assertFalse(ProformaInvoice.objects.filter(client=self.client_obj).exists())

    def test_disallowed_extension_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        upload = SimpleUploadedFile(
            "bon.exe", b"MZ\x90\x00fake exe", content_type="application/octet-stream"
        )
        self.client.force_login(self.user)
        item = CartItem.objects.get(cart__client=self.client_obj)
        self.client.post(
            "/mon-espace/panier/proforma/",
            {f"item{item.pk}-billing_basis": "per_day", "bon_de_commande": upload},
        )
        self.assertFalse(ProformaInvoice.objects.filter(client=self.client_obj).exists())

    def test_proforma_without_attachment_still_works(self):
        self.client.force_login(self.user)
        item = CartItem.objects.get(cart__client=self.client_obj)
        self.client.post(
            "/mon-espace/panier/proforma/",
            {f"item{item.pk}-billing_basis": "per_day"},
        )
        invoice = ProformaInvoice.objects.get(client=self.client_obj)
        self.assertFalse(invoice.bon_de_commande)


class EnrollmentAcceptanceEmailTestCase(TestCase):
    """TODO 10.1 — the pre_save/post_save signal pair fires the acceptance
    email exactly once per transition *into* "accepted", regardless of
    entry point, and never on unrelated saves."""

    def setUp(self):
        session = FormationSession.objects.create(
            name="Session Phase10", slug="session-phase10", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session, code="P10", title="Formation Phase 10",
            duration_months=3, is_active=True,
        )
        self.client_obj = Client.objects.create(
            client_type="individual", full_name="Client Phase10",
            phone="0555000333", email="accepted@example.com",
        )
        self.participant = Participant.objects.create(
            client=self.client_obj, full_name="Client Phase10",
        )
        self.enrollment = Enrollment.objects.create(
            client=self.client_obj, participant=self.participant,
            offering=self.offering, status="pending",
        )

    def test_transition_to_accepted_sends_one_email(self):
        from django.core import mail
        mail.outbox = []
        self.enrollment.status = "accepted"
        self.enrollment.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("accepted@example.com", mail.outbox[0].to)

    def test_transition_from_accepted_to_confirmed_sends_no_extra_email(self):
        from django.core import mail
        self.enrollment.status = "accepted"
        self.enrollment.save()
        mail.outbox = []
        self.enrollment.status = "confirmed"
        self.enrollment.save()
        self.assertEqual(len(mail.outbox), 0)

    def test_resaving_already_accepted_sends_no_duplicate_email(self):
        from django.core import mail
        self.enrollment.status = "accepted"
        self.enrollment.save()
        mail.outbox = []
        self.enrollment.motivation = "updated note"
        self.enrollment.save()
        self.assertEqual(len(mail.outbox), 0)

    def test_no_client_email_returns_false_without_raising(self):
        from django.core import mail
        self.client_obj.email = ""
        self.client_obj.save()
        mail.outbox = []
        from .services import notify_enrollment_accepted
        ok, message = notify_enrollment_accepted(self.enrollment)
        self.assertFalse(ok)
        self.assertEqual(len(mail.outbox), 0)

    def test_bulk_admin_action_still_triggers_email(self):
        from django.core import mail
        staff = User.objects.create_user(
            username="staff10", password="x", is_staff=True, is_superuser=True,
        )
        self.client.force_login(staff)
        mail.outbox = []
        self.client.post(
            "/admin/enrollment/enrollment/",
            {"action": "mark_accepted", "_selected_action": [self.enrollment.pk]},
            follow=True,
        )
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, "accepted")
        self.assertEqual(len(mail.outbox), 1)


class DashboardEnrollmentVisibilityTestCase(TestCase):
    """TODO 10.4 — an enrollment moved to "accepted" (or any real status
    other than "pending"/"confirmed") must still show up on /mon-espace/;
    it used to fall into neither the actionable banner nor the Active
    Purchases card and simply vanish."""

    def setUp(self):
        self.session = FormationSession.objects.create(
            name="Session 10.4", slug="session-10-4", is_active=True
        )
        self.offering = Offering.objects.create(
            session=self.session,
            code="D104",
            title="Formation Dashboard 10.4",
            duration_months=1,
            is_active=True,
        )
        self.user = User.objects.create_user(
            username="client104", password="x", is_active=True
        )
        self.client_obj = Client.objects.create(
            user=self.user,
            client_type="individual",
            phone="0555000555",
            account_status="active",
        )
        self.participant = Participant.objects.create(
            client=self.client_obj, full_name="Participant 10.4",
        )
        self.enrollment = Enrollment.objects.create(
            client=self.client_obj,
            participant=self.participant,
            offering=self.offering,
            status="accepted",
        )

    def test_accepted_enrollment_appears_on_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get("/mon-espace/")
        content = response.content.decode()
        self.assertIn("Formation Dashboard 10.4", content)
        self.assertIn("مقبول", content)
        self.assertIn(self.enrollment, response.context["enrollments"])

    def test_status_change_reflected_without_relogin(self):
        self.client.force_login(self.user)
        self.client.get("/mon-espace/")  # same session as below, no relogin
        self.enrollment.status = "confirmed"
        self.enrollment.confirmed_at = timezone.now()
        self.enrollment.save()
        response = self.client.get("/mon-espace/")
        content = response.content.decode()
        self.assertIn("مؤكد من طرف المشترك", content)

    def test_enrollment_counts_match_manual_queries(self):
        other_offering = Offering.objects.create(
            session=self.session,
            code="D104B",
            title="Formation Dashboard 10.4 B",
            duration_months=1,
            is_active=True,
        )
        Enrollment.objects.create(
            client=self.client_obj,
            participant=self.participant,
            offering=other_offering,
            status="pending",
        )
        self.client.force_login(self.user)
        response = self.client.get("/mon-espace/")
        counts = response.context["enrollment_counts"]
        for status_key, _label in STATUS_CHOICES:
            expected = Enrollment.objects.filter(
                client=self.client_obj, status=status_key
            ).count()
            self.assertEqual(counts[status_key], expected)
        self.assertEqual(
            response.context["total_enrollments"],
            Enrollment.objects.filter(client=self.client_obj).count(),
        )

    # -- accepted -> confirm action reachable (bug fix) ---------------------

    def test_accepted_enrollment_shows_in_actionable_confirm_banner(self):
        """Regression test — the Confirm button used to vanish the moment
        staff moved an enrollment from "pending" to "accepted", leaving no
        way for the client to ever turn their acceptance into a purchase."""
        self.client.force_login(self.user)
        response = self.client.get("/mon-espace/")
        self.assertIn(self.enrollment, response.context["pending_enrollments"])
        self.assertContains(response, "تأكيد التسجيل")
        self.assertContains(
            response, reverse("enrollment:dashboard_confirm", args=[self.enrollment.pk])
        )

    def test_confirming_accepted_enrollment_makes_it_an_active_purchase(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("enrollment:dashboard_confirm", args=[self.enrollment.pk]),
            follow=True,
        )
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, "confirmed")
        response = self.client.get(reverse("enrollment:my_purchases"))
        self.assertIn(self.enrollment, response.context["purchases"])

    def test_waitlisted_and_rejected_do_not_show_confirm_banner(self):
        """Only "pending"/"accepted" are genuinely actionable — a
        waitlisted or rejected application isn't an offer the client can
        confirm into a purchase, so it must stay out of this banner (it
        still shows, read-only, in the full "تسجيلاتي" list below)."""
        self.enrollment.status = "waitlisted"
        self.enrollment.save(update_fields=["status"])
        rejected_offering = Offering.objects.create(
            session=self.session,
            code="D104C",
            title="Formation Dashboard 10.4 C",
            duration_months=1,
            is_active=True,
        )
        rejected = Enrollment.objects.create(
            client=self.client_obj,
            participant=self.participant,
            offering=rejected_offering,
            status="rejected",
        )
        self.client.force_login(self.user)
        response = self.client.get("/mon-espace/")
        self.assertNotIn(self.enrollment, response.context["pending_enrollments"])
        self.assertNotIn(rejected, response.context["pending_enrollments"])
        self.assertIn(self.enrollment, response.context["enrollments"])
        self.assertIn(rejected, response.context["enrollments"])


class StaffNotesVisibilityTestCase(TestCase):
    """TODO 10.5 — staff notes only reach the client dashboard once opted
    in via `visible_to_client=True`; author identity stays internal."""

    def setUp(self):
        self.session = FormationSession.objects.create(
            name="Session 10.5", slug="session-10-5", is_active=True
        )
        self.offering = Offering.objects.create(
            session=self.session,
            code="D105",
            title="Formation Dashboard 10.5",
            duration_months=1,
            is_active=True,
        )
        self.user = User.objects.create_user(
            username="client105", password="x", is_active=True
        )
        self.client_obj = Client.objects.create(
            user=self.user,
            client_type="individual",
            phone="0555000666",
            account_status="active",
        )
        self.participant = Participant.objects.create(
            client=self.client_obj, full_name="Participant 10.5",
        )
        self.enrollment = Enrollment.objects.create(
            client=self.client_obj,
            participant=self.participant,
            offering=self.offering,
            status="accepted",
        )
        self.staff_user = User.objects.create_user(
            username="staff105", password="x", is_staff=True
        )

    def test_internal_note_stays_hidden(self):
        EnrollmentNote.objects.create(
            enrollment=self.enrollment,
            author=self.staff_user,
            text="ملاحظة داخلية لا يجب أن يراها الزبون.",
            visible_to_client=False,
        )
        self.client.force_login(self.user)
        content = self.client.get("/mon-espace/").content.decode()
        self.assertNotIn("ملاحظة داخلية لا يجب أن يراها الزبون.", content)

    def test_client_visible_note_appears_without_author(self):
        note = EnrollmentNote.objects.create(
            enrollment=self.enrollment,
            author=self.staff_user,
            text="يرجى إحضار نسخة من بطاقة التعريف.",
            visible_to_client=True,
        )
        self.client.force_login(self.user)
        content = self.client.get("/mon-espace/").content.decode()
        self.assertIn("يرجى إحضار نسخة من بطاقة التعريف.", content)
        self.assertNotIn(self.staff_user.username, content)

    def test_notes_render_in_creation_order(self):
        first = EnrollmentNote.objects.create(
            enrollment=self.enrollment, author=self.staff_user,
            text="الملاحظة الأولى", visible_to_client=True,
        )
        second = EnrollmentNote.objects.create(
            enrollment=self.enrollment, author=self.staff_user,
            text="الملاحظة الثانية", visible_to_client=True,
        )
        self.client.force_login(self.user)
        content = self.client.get("/mon-espace/").content.decode()
        self.assertLess(content.index(first.text), content.index(second.text))

    def test_mixed_visibility_only_shows_opted_in_note(self):
        EnrollmentNote.objects.create(
            enrollment=self.enrollment, author=self.staff_user,
            text="ملاحظة داخلية مختلطة", visible_to_client=False,
        )
        visible = EnrollmentNote.objects.create(
            enrollment=self.enrollment, author=self.staff_user,
            text="ملاحظة ظاهرة للزبون", visible_to_client=True,
        )
        self.client.force_login(self.user)
        response = self.client.get("/mon-espace/")
        content = response.content.decode()
        self.assertNotIn("ملاحظة داخلية مختلطة", content)
        self.assertIn("ملاحظة ظاهرة للزبون", content)
        for e in response.context["enrollments"]:
            if e.pk == self.enrollment.pk:
                self.assertEqual([n.pk for n in e.visible_notes], [visible.pk])


class CompanyRosterTestCase(TestCase):
    """TODO 10.2 — EnrollmentParticipant CRUD (dynamic formset), seat-cap
    enforcement, staff read-only entry point, CSV export."""

    def setUp(self):
        session = FormationSession.objects.create(
            name="Session Roster", slug="session-roster", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session,
            code="ROST01",
            title="Formation Roster",
            duration_months=1,
            is_active=True,
            seats_available=2,
        )
        self.user = User.objects.create_user(
            username="enterprise10", password="x", is_active=True
        )
        self.client_obj = Client.objects.create(
            user=self.user,
            client_type="enterprise",
            phone="0555000444",
            email="roster@example.com",
            company_name="Société Roster",
            account_status="active",
        )
        self.participant = Participant.objects.create(
            client=self.client_obj, full_name="Contact Roster",
        )
        self.enrollment = Enrollment.objects.create(
            client=self.client_obj,
            participant=self.participant,
            offering=self.offering,
            status="accepted",
        )

    def _roster_url(self, enrollment=None):
        return reverse(
            "enrollment:enrollment_roster",
            args=[(enrollment or self.enrollment).pk],
        )

    def _export_url(self, enrollment=None):
        return reverse(
            "enrollment:enrollment_roster_export",
            args=[(enrollment or self.enrollment).pk],
        )

    def _management_data(self, total=1, initial=0, prefix="roster"):
        return {
            f"{prefix}-TOTAL_FORMS": str(total),
            f"{prefix}-INITIAL_FORMS": str(initial),
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
        }

    def _row_data(self, index, first_name="", last_name="", prefix="roster", **extra):
        data = {
            f"{prefix}-{index}-id": "",
            f"{prefix}-{index}-first_name": first_name,
            f"{prefix}-{index}-last_name": last_name,
            f"{prefix}-{index}-first_name_ar": "",
            f"{prefix}-{index}-last_name_ar": "",
            f"{prefix}-{index}-gender": "",
            f"{prefix}-{index}-date_of_birth": "",
            f"{prefix}-{index}-place_of_birth": "",
            f"{prefix}-{index}-place_of_birth_ar": "",
            f"{prefix}-{index}-job_title": "",
            f"{prefix}-{index}-employer": "",
            f"{prefix}-{index}-phone": "",
            f"{prefix}-{index}-email": "",
        }
        data.update({f"{prefix}-{index}-{k}": v for k, v in extra.items()})
        return data

    # -- gating (10.2.1/10.2.7) ------------------------------------------

    def test_non_enterprise_client_gets_404(self):
        self.client_obj.client_type = "individual"
        self.client_obj.full_name = "Individual Roster"
        self.client_obj.save()
        self.client.force_login(self.user)
        response = self.client.get(self._roster_url())
        self.assertEqual(response.status_code, 404)
        response = self.client.get(self._export_url())
        self.assertEqual(response.status_code, 404)

    def test_status_not_yet_accepted_gets_404(self):
        self.enrollment.status = "pending"
        self.enrollment.save()
        self.client.force_login(self.user)
        response = self.client.get(self._roster_url())
        self.assertEqual(response.status_code, 404)

    def test_other_clients_enrollment_gets_404(self):
        other_user = User.objects.create_user(
            username="other10", password="x", is_active=True
        )
        Client.objects.create(
            user=other_user, client_type="individual", phone="0555000555",
            full_name="Other Client", account_status="active",
        )
        self.client.force_login(other_user)
        response = self.client.get(self._roster_url())
        self.assertEqual(response.status_code, 404)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self._roster_url())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    # -- CRUD (10.2.2/10.2.7) --------------------------------------------

    def test_roster_page_renders_with_zero_rows(self):
        self.client.force_login(self.user)
        response = self.client.get(self._roster_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "قائمة المشاركين")

    def test_saving_one_valid_row_creates_participant(self):
        self.client.force_login(self.user)
        data = self._management_data(total=1)
        data.update(self._row_data(0, first_name="Ahmed", last_name="Belaid"))
        response = self.client.post(self._roster_url(), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EnrollmentParticipant.objects.filter(enrollment=self.enrollment).count(), 1)
        row = EnrollmentParticipant.objects.get(enrollment=self.enrollment)
        # Employer auto-fills from the client's company name when left blank.
        self.assertEqual(row.employer, "Société Roster")

    def test_empty_last_name_is_invalid_and_does_not_save(self):
        self.client.force_login(self.user)
        data = self._management_data(total=1)
        data.update(self._row_data(0, first_name="Ahmed", last_name=""))
        response = self.client.post(self._roster_url(), data)
        self.assertEqual(response.status_code, 200)  # re-rendered with errors, no redirect
        self.assertEqual(EnrollmentParticipant.objects.filter(enrollment=self.enrollment).count(), 0)

    def test_untouched_extra_row_is_silently_ignored(self):
        self.client.force_login(self.user)
        data = self._management_data(total=2)
        data.update(self._row_data(0, first_name="Ahmed", last_name="Belaid"))
        data.update(self._row_data(1))  # left fully blank
        response = self.client.post(self._roster_url(), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EnrollmentParticipant.objects.filter(enrollment=self.enrollment).count(), 1)

    def test_deleting_existing_row_removes_it(self):
        row = EnrollmentParticipant.objects.create(
            enrollment=self.enrollment, first_name="Ahmed", last_name="Belaid",
        )
        self.client.force_login(self.user)
        data = self._management_data(total=1, initial=1)
        data.update(
            self._row_data(0, first_name="Ahmed", last_name="Belaid", id=str(row.pk), DELETE="on")
        )
        response = self.client.post(self._roster_url(), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(EnrollmentParticipant.objects.filter(pk=row.pk).exists())

    # -- seat cap (10.2.3/10.2.7) -----------------------------------------

    def test_exceeding_seats_available_is_rejected_server_side(self):
        # seats_available == 2 (see setUp) — a 3rd row must be rejected even
        # via a raw POST that bypasses the JS "disable Add past cap" guard.
        self.client.force_login(self.user)
        data = self._management_data(total=3)
        data.update(self._row_data(0, first_name="A", last_name="One"))
        data.update(self._row_data(1, first_name="B", last_name="Two"))
        data.update(self._row_data(2, first_name="C", last_name="Three"))
        response = self.client.post(self._roster_url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EnrollmentParticipant.objects.filter(enrollment=self.enrollment).count(), 0)

    def test_exactly_at_seat_cap_is_accepted(self):
        self.client.force_login(self.user)
        data = self._management_data(total=2)
        data.update(self._row_data(0, first_name="A", last_name="One"))
        data.update(self._row_data(1, first_name="B", last_name="Two"))
        response = self.client.post(self._roster_url(), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EnrollmentParticipant.objects.filter(enrollment=self.enrollment).count(), 2)

    # -- locked roster (10.2.1/10.2.7) -------------------------------------

    def test_locked_roster_renders_read_only(self):
        self.enrollment.roster_locked_at = timezone.now()
        self.enrollment.save(update_fields=["roster_locked_at"])
        self.client.force_login(self.user)
        response = self.client.get(self._roster_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "القائمة مقفلة")

    def test_locked_roster_ignores_post(self):
        self.enrollment.roster_locked_at = timezone.now()
        self.enrollment.save(update_fields=["roster_locked_at"])
        self.client.force_login(self.user)
        data = self._management_data(total=1)
        data.update(self._row_data(0, first_name="Ahmed", last_name="Belaid"))
        response = self.client.post(self._roster_url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EnrollmentParticipant.objects.filter(enrollment=self.enrollment).count(), 0)

    # -- staff read-only entry point (10.2.5/10.2.7) -----------------------

    def test_staff_can_view_but_not_edit(self):
        staff = User.objects.create_user(
            username="staffroster", password="x", is_staff=True, is_superuser=True,
        )
        self.client.force_login(staff)
        response = self.client.get(self._roster_url())
        self.assertEqual(response.status_code, 200)

        data = self._management_data(total=1)
        data.update(self._row_data(0, first_name="Ahmed", last_name="Belaid"))
        response = self.client.post(self._roster_url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EnrollmentParticipant.objects.filter(enrollment=self.enrollment).count(), 0)

    def test_staff_roster_link_appears_on_admin_change_page(self):
        staff = User.objects.create_user(
            username="staffroster2", password="x", is_staff=True, is_superuser=True,
        )
        self.client.force_login(staff)
        response = self.client.get(f"/admin/enrollment/enrollment/{self.enrollment.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "عرض قائمة المشاركين")

    # -- CSV export (10.2.6/10.2.7) -----------------------------------------

    def test_csv_export_header_and_rows(self):
        EnrollmentParticipant.objects.create(
            enrollment=self.enrollment, first_name="Ahmed", last_name="Belaid",
            employer="Société Roster",
        )
        self.client.force_login(self.user)
        response = self.client.get(self._export_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8-sig")
        content = response.content.decode("utf-8-sig")
        lines = content.strip().splitlines()
        self.assertIn("Prénom,Nom,Prénom AR,Nom AR", lines[0])
        self.assertIn("Ahmed,Belaid", lines[1])


class ScheduleSessionTestCase(TestCase):
    """TODO 10.7 — staff schedules a session with a specific date: sets
    `FormationSession.start_date` for every enrollment sharing that
    offering, locks only the calling enrollment's own roster, emails the
    enrolling client, and generates the CSV+brief bundle for the
    pedagogical-app hand-off (10.7.3)."""

    def setUp(self):
        self.session_obj = FormationSession.objects.create(
            name="Session Schedule", slug="session-schedule", is_active=True
        )
        self.offering = Offering.objects.create(
            session=self.session_obj,
            code="SCH01",
            title="Formation Schedule",
            duration_months=1,
            is_active=True,
            seats_available=5,
        )
        self.user = User.objects.create_user(
            username="enterprise_sched", password="x", is_active=True
        )
        self.client_obj = Client.objects.create(
            user=self.user,
            client_type="enterprise",
            phone="0555111222",
            email="sched@example.com",
            company_name="Société Schedule",
            account_status="active",
        )
        self.participant = Participant.objects.create(
            client=self.client_obj, full_name="Contact Schedule",
        )
        self.enrollment = Enrollment.objects.create(
            client=self.client_obj,
            participant=self.participant,
            offering=self.offering,
            status="accepted",
        )

        # A second company sharing the same offering — used to check the
        # shared-date / independent-lock behaviour (10.7.4).
        self.user2 = User.objects.create_user(
            username="enterprise_sched2", password="x", is_active=True
        )
        self.client_obj2 = Client.objects.create(
            user=self.user2,
            client_type="enterprise",
            phone="0555111333",
            email="sched2@example.com",
            company_name="Société Schedule Deux",
            account_status="active",
        )
        self.participant2 = Participant.objects.create(
            client=self.client_obj2, full_name="Contact Schedule 2",
        )
        self.enrollment2 = Enrollment.objects.create(
            client=self.client_obj2,
            participant=self.participant2,
            offering=self.offering,
            status="accepted",
        )

        self.staff = User.objects.create_user(
            username="staffsched", password="x", is_staff=True, is_superuser=True,
        )

    def _schedule_url(self, enrollment=None):
        return reverse(
            "admin:enrollment_enrollment_schedule",
            args=[(enrollment or self.enrollment).pk],
        )

    def _change_url(self, enrollment=None):
        return f"/admin/enrollment/enrollment/{(enrollment or self.enrollment).pk}/change/"

    # -- service function (10.7.1/10.7.4) ---------------------------------

    def test_schedule_session_sets_date_and_locks_roster(self):
        from .services import schedule_session

        start = timezone.now().date() + timezone.timedelta(days=30)
        ok, message = schedule_session(self.enrollment, start)
        self.assertTrue(ok)
        self.session_obj.refresh_from_db()
        self.enrollment.refresh_from_db()
        self.assertEqual(self.session_obj.start_date, start)
        self.assertIsNotNone(self.enrollment.roster_locked_at)

    def test_scheduling_second_enrollment_shares_date_not_lock(self):
        from .services import schedule_session

        start1 = timezone.now().date() + timezone.timedelta(days=10)
        schedule_session(self.enrollment, start1)
        self.enrollment.refresh_from_db()
        first_lock = self.enrollment.roster_locked_at
        self.assertIsNotNone(first_lock)
        # Second enrollment's own roster starts out unlocked.
        self.assertIsNone(self.enrollment2.roster_locked_at)

        start2 = timezone.now().date() + timezone.timedelta(days=20)
        schedule_session(self.enrollment2, start2)
        self.enrollment.refresh_from_db()
        self.enrollment2.refresh_from_db()
        self.session_obj.refresh_from_db()

        # Shared FK: the session now reflects the second call's date.
        self.assertEqual(self.session_obj.start_date, start2)
        # First enrollment's own lock timestamp is untouched by the second call.
        self.assertEqual(self.enrollment.roster_locked_at, first_lock)
        self.assertIsNotNone(self.enrollment2.roster_locked_at)

    def test_schedule_session_emails_only_the_enrolling_client(self):
        from django.core import mail

        from .services import schedule_session

        start = timezone.now().date() + timezone.timedelta(days=15)
        mail.outbox = []
        schedule_session(self.enrollment, start)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.client_obj.email])

    def test_scheduling_does_not_block_on_empty_roster(self):
        # 10.7.2 — deliberately not gated on `enrollment.roster.exists()`.
        from .services import schedule_session

        self.assertEqual(self.enrollment.roster.count(), 0)
        start = timezone.now().date() + timezone.timedelta(days=7)
        ok, _message = schedule_session(self.enrollment, start)
        self.assertTrue(ok)

    def test_roster_page_read_only_after_scheduling_with_zero_rows(self):
        from .services import schedule_session

        start = timezone.now().date() + timezone.timedelta(days=5)
        schedule_session(self.enrollment, start)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("enrollment:enrollment_roster", args=[self.enrollment.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "القائمة مقفلة")

    # -- admin entry point (10.7.1) ----------------------------------------

    def test_schedule_link_appears_on_change_page(self):
        self.client.force_login(self.staff)
        response = self.client.get(self._change_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "جدولة الجلسة")

    def test_admin_schedule_view_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(self._schedule_url())
        self.assertNotEqual(response.status_code, 200)

    def test_admin_schedule_view_get_renders_form(self):
        self.client.force_login(self.staff)
        response = self.client.get(self._schedule_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "جدولة الجلسة")

    def test_admin_schedule_view_warns_when_not_accepted(self):
        self.enrollment.status = "pending"
        self.enrollment.save(update_fields=["status"])
        self.client.force_login(self.staff)
        response = self.client.get(self._schedule_url(), follow=True)
        self.assertRedirects(response, self._change_url())

    def test_admin_schedule_view_post_schedules_and_redirects(self):
        self.client.force_login(self.staff)
        start = timezone.now().date() + timezone.timedelta(days=40)
        response = self.client.post(
            self._schedule_url(),
            {"start_date": start.isoformat(), "registration_deadline": ""},
        )
        self.assertRedirects(response, self._change_url())
        self.session_obj.refresh_from_db()
        self.enrollment.refresh_from_db()
        self.assertEqual(self.session_obj.start_date, start)
        self.assertIsNotNone(self.enrollment.roster_locked_at)

    # -- session bundle download (10.7.3) -----------------------------------

    def test_session_bundle_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("enrollment:enrollment_session_bundle", args=[self.enrollment.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_session_bundle_contains_csv_and_brief(self):
        import io
        import zipfile

        EnrollmentParticipant.objects.create(
            enrollment=self.enrollment, first_name="Ahmed", last_name="Belaid",
        )
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("enrollment:enrollment_session_bundle", args=[self.enrollment.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        zf = zipfile.ZipFile(io.BytesIO(response.content))
        names = zf.namelist()
        csv_name = f"participants_{self.offering.code}_{self.enrollment.pk}.csv"
        brief_name = f"session_brief_{self.enrollment.pk}.txt"
        self.assertIn(csv_name, names)
        self.assertIn(brief_name, names)
        brief = zf.read(brief_name).decode("utf-8")
        self.assertIn("Société Schedule", brief)


class QuickRegisterPrefillTestCase(TestCase):
    """TODO 10.3 — quick-register CTA + prefill on the individual subscribe
    form for an authenticated client with an already-active account."""

    def setUp(self):
        session = FormationSession.objects.create(
            name="Session QR", slug="session-qr", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session,
            code="QR01",
            title="Formation Quick Register",
            duration_months=2,
            is_active=True,
            seats_available=10,
        )
        self.detail_url = self.offering.get_absolute_url()
        self.subscribe_url = reverse(
            "enrollment:subscribe", args=[session.slug, self.offering.code]
        )

    def _make_client(self, username, account_status="active"):
        user = User.objects.create_user(username=username, password="x", is_active=True)
        client = Client.objects.create(
            user=user,
            client_type="individual",
            full_name="زبون تجريبي",
            phone="0555000777",
            email="quickreg@example.com",
            wilaya="سطيف",
            address="حي تجريبي",
            birth_date="1990-01-01",
            gender="m",
            education_level="university",
            account_status=account_status,
        )
        return user, client

    # -- CTA visibility (10.3.1/10.3.3) ------------------------------------

    def test_anonymous_visitor_sees_no_quick_register_cta(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "التسجيل السريع")

    def test_active_client_sees_quick_register_cta(self):
        user, _client = self._make_client("qr_active")
        self.client.force_login(user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "التسجيل السريع")
        self.assertContains(response, self.subscribe_url)

    def test_pending_client_sees_no_quick_register_cta(self):
        user, _client = self._make_client("qr_pending", account_status="pending")
        self.client.force_login(user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "التسجيل السريع")

    # -- prefill behaviour (10.3.2/10.3.3, bug fix: was gated behind
    # ?prefill=1, now automatic on every GET) ------------------------------

    def test_anonymous_get_form_is_blank(self):
        response = self.client.get(self.subscribe_url)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIsNone(form.initial.get("full_name"))
        self.assertIsNone(form.initial.get("phone"))

    def test_active_client_get_populates_identity_fields(self):
        user, client_obj = self._make_client("qr_prefill")
        self.client.force_login(user)
        response = self.client.get(self.subscribe_url)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial.get("full_name"), client_obj.full_name)
        self.assertEqual(form.initial.get("phone"), client_obj.phone)
        self.assertEqual(form.initial.get("email"), client_obj.email)
        self.assertEqual(form.initial.get("wilaya"), client_obj.wilaya)
        self.assertEqual(form.initial.get("address"), client_obj.address)
        self.assertEqual(form.initial.get("education_level"), client_obj.education_level)
        self.assertEqual(form.initial.get("gender"), client_obj.gender)
        self.assertEqual(str(form.initial.get("birth_date")), str(client_obj.birth_date))
        # Rendered inputs actually carry the prefilled value.
        self.assertContains(response, client_obj.full_name)
        self.assertContains(response, client_obj.phone)

    def test_active_client_get_with_legacy_prefill_param_still_populates(self):
        """The old `?prefill=1` link (still used by the "quick register"
        CTA on the offering detail page) keeps working exactly the same,
        now that prefill runs regardless of the query string."""
        user, client_obj = self._make_client("qr_prefill_legacy")
        self.client.force_login(user)
        response = self.client.get(self.subscribe_url, {"prefill": "1"})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial.get("full_name"), client_obj.full_name)

    def test_active_client_get_without_prefill_param_is_also_prefilled(self):
        """Regression test — this used to be the bug: any entry point into
        this exact view that didn't carry `?prefill=1` (e.g. the
        branch-first flow launched from the top-nav "التسجيل الإلكتروني"
        button, whose AJAX-built `subscribe_url` never set the param)
        landed on a blank form for an already-active, fully-profiled
        client. Prefill must not depend on how the person got here."""
        user, client_obj = self._make_client("qr_noparam")
        self.client.force_login(user)
        response = self.client.get(self.subscribe_url)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial.get("full_name"), client_obj.full_name)
        self.assertEqual(form.initial.get("phone"), client_obj.phone)

    def test_pending_client_get_stays_blank(self):
        user, _client = self._make_client("qr_pending2", account_status="pending")
        self.client.force_login(user)
        response = self.client.get(self.subscribe_url)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIsNone(form.initial.get("full_name"))

    def test_per_registration_fields_never_prefilled(self):
        user, _client = self._make_client("qr_perreg")
        self.client.force_login(user)
        response = self.client.get(self.subscribe_url)
        form = response.context["form"]
        self.assertNotIn("motivation", form.initial)
        self.assertNotIn("employment_status", form.initial)
        self.assertNotIn("preferred_contact_time", form.initial)

    def test_prefilled_form_still_submits_like_the_manual_path(self):
        user, client_obj = self._make_client("qr_submit")
        self.client.force_login(user)
        response = self.client.post(
            self.subscribe_url,
            {
                "client_type": "individual",
                "full_name": client_obj.full_name,
                "birth_date": "1990-01-01",
                "gender": "m",
                "phone": "0660112233",
                "email": "submitted@example.com",
                "wilaya": "سطيف",
                "address": "",
                "education_level": "university",
                "employment_status": "",
                "preferred_contact_time": "",
                "source": "web",
                "motivation": "",
                "agree_terms": "on",
                "website": "",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Enrollment.objects.filter(offering=self.offering, participant__phone="0660112233").exists()
        )

    # -- account linking on submit (bug fix) --------------------------------

    def _post_data(self, **overrides):
        data = {
            "client_type": "individual",
            "full_name": "اسم معدل عند التسجيل",
            "birth_date": "1990-01-01",
            "gender": "m",
            "phone": "0660112244",
            "email": "linked@example.com",
            "wilaya": "سطيف",
            "address": "",
            "education_level": "university",
            "employment_status": "",
            "preferred_contact_time": "",
            "source": "web",
            "motivation": "",
            "agree_terms": "on",
            "website": "",
        }
        data.update(overrides)
        return data

    def test_authenticated_active_client_enrollment_links_to_account_not_orphan(self):
        """Regression test — submitting subscribe while logged in used to
        always create a brand-new orphan Client (no `user` link), so the
        enrollment could never show up in the account's مساحتي/مشترياتي
        even after staff changed its status. It must attach to the
        account's own linked, active Client instead, and must not create
        an extra Client at all."""
        user, client_obj = self._make_client("qr_linked")
        self.client.force_login(user)
        clients_before = Client.objects.count()

        response = self.client.post(self.subscribe_url, self._post_data(), follow=True)

        self.assertEqual(response.status_code, 200)
        # No new orphan Client was created for a logged-in, active account.
        self.assertEqual(Client.objects.count(), clients_before)
        enrollment = Enrollment.objects.get(
            offering=self.offering, participant__phone="0660112244"
        )
        self.assertEqual(enrollment.client_id, client_obj.pk)
        self.assertEqual(enrollment.client.user_id, user.pk)
        # ...and therefore visible through the exact query the dashboard
        # (`enrollment:dashboard`) uses, regardless of its later status.
        self.assertIn(enrollment, Enrollment.objects.filter(client=client_obj))

    def test_pending_client_enrollment_still_gets_own_orphan_client(self):
        """A logged-in user whose account isn't active yet (`pending`) must
        keep the old guest-style behaviour: a fresh, unlinked Client — same
        guard as the GET prefill above — rather than silently attaching an
        enrollment to a not-yet-approved account."""
        user, client_obj = self._make_client("qr_pending_submit", account_status="pending")
        self.client.force_login(user)

        response = self.client.post(self.subscribe_url, self._post_data(), follow=True)

        self.assertEqual(response.status_code, 200)
        enrollment = Enrollment.objects.get(
            offering=self.offering, participant__phone="0660112244"
        )
        self.assertNotEqual(enrollment.client_id, client_obj.pk)
        self.assertIsNone(enrollment.client.user_id)

    def test_anonymous_submission_still_creates_orphan_client(self):
        """Genuine guests (TODO 1.8) keep working exactly as before: a
        fresh Client with no `user` link."""
        clients_before = Client.objects.count()

        response = self.client.post(self.subscribe_url, self._post_data(), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Client.objects.count(), clients_before + 1)
        enrollment = Enrollment.objects.get(
            offering=self.offering, participant__phone="0660112244"
        )
        self.assertIsNone(enrollment.client.user_id)


class SpecialtyDetailFormPrefillTestCase(TestCase):
    """The offering detail page's "أضف تعليقك" (comment) and "عندك سؤال
    حول هذا التخصص؟" (enquiry) forms are public, but a logged-in,
    already-active client shouldn't have to retype their own name/phone/
    email — same fix as the subscribe form's prefill (TODO 10.3.2)."""

    def setUp(self):
        session = FormationSession.objects.create(
            name="Session Detail Prefill", slug="session-detail-prefill", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session,
            code="DP01",
            title="Formation Detail Prefill",
            duration_months=2,
            is_active=True,
            seats_available=10,
        )
        self.detail_url = self.offering.get_absolute_url()

    def _make_client(self, username, account_status="active"):
        user = User.objects.create_user(username=username, password="x", is_active=True)
        client = Client.objects.create(
            user=user,
            client_type="individual",
            full_name="زبون تجريبي للتعليقات",
            phone="0555000888",
            email="detailprefill@example.com",
            account_status=account_status,
        )
        return user, client

    def test_anonymous_get_forms_are_blank(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["comment_form"].initial.get("name"))
        self.assertIsNone(response.context["enquiry_form"].initial.get("name"))

    def test_active_client_get_prefills_comment_and_enquiry_forms(self):
        user, client_obj = self._make_client("detail_active")
        self.client.force_login(user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)

        comment_form = response.context["comment_form"]
        self.assertEqual(comment_form.initial.get("name"), client_obj.display_name)
        self.assertEqual(comment_form.initial.get("email"), client_obj.email)

        enquiry_form = response.context["enquiry_form"]
        self.assertEqual(enquiry_form.initial.get("name"), client_obj.display_name)
        self.assertEqual(enquiry_form.initial.get("phone"), client_obj.phone)
        self.assertEqual(enquiry_form.initial.get("email"), client_obj.email)

        # Rendered inputs actually carry the prefilled value.
        self.assertContains(response, client_obj.display_name)
        self.assertContains(response, client_obj.phone)

    def test_pending_client_get_forms_stay_blank(self):
        user, _client = self._make_client("detail_pending", account_status="pending")
        self.client.force_login(user)
        response = self.client.get(self.detail_url)
        self.assertIsNone(response.context["comment_form"].initial.get("name"))
        self.assertIsNone(response.context["enquiry_form"].initial.get("name"))

    def test_comment_submission_still_works_when_logged_in(self):
        user, client_obj = self._make_client("detail_comment_submit")
        self.client.force_login(user)
        response = self.client.post(
            self.detail_url,
            {
                "form_type": "comment",
                "name": client_obj.display_name,
                "email": client_obj.email,
                "rating": 5,
                "text": "تعليق تجريبي.",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Comment.objects.filter(offering=self.offering, text="تعليق تجريبي.").exists()
        )

    def test_enquiry_submission_still_works_when_logged_in(self):
        user, client_obj = self._make_client("detail_enquiry_submit")
        self.client.force_login(user)
        response = self.client.post(
            self.detail_url,
            {
                "form_type": "enquiry",
                "name": client_obj.display_name,
                "phone": client_obj.phone,
                "email": client_obj.email,
                "question": "سؤال تجريبي؟",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Enquiry.objects.filter(offering=self.offering, question="سؤال تجريبي؟").exists()
        )


class CommentAdminNotificationTestCase(TestCase):
    """A new comment — whether from a logged-in client or a plain guest —
    must alert the admin inbox (configured via `settings.ADMINS`) so staff
    know there's something waiting for moderation."""

    def setUp(self):
        session = FormationSession.objects.create(
            name="Session Comment Notif", slug="session-comment-notif", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session,
            code="CN01",
            title="Formation Comment Notif",
            duration_months=2,
            is_active=True,
        )
        self.detail_url = self.offering.get_absolute_url()

    def _post_comment(self, **overrides):
        data = {
            "form_type": "comment",
            "name": "زائر تجريبي",
            "email": "guest@example.com",
            "rating": 4,
            "text": "تعليق تجريبي للإشعار.",
        }
        data.update(overrides)
        return self.client.post(self.detail_url, data, follow=True)

    def test_guest_comment_sends_admin_notification(self):
        from django.core import mail
        mail.outbox = []
        response = self._post_comment()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn("support@excellance-ms.dz", sent.to)
        self.assertIn(self.offering.title, sent.subject)
        self.assertIn("تعليق تجريبي للإشعار.", sent.alternatives[0][0])

    def test_logged_in_client_comment_also_sends_admin_notification(self):
        from django.core import mail
        user = User.objects.create_user(username="commenter", password="x", is_active=True)
        Client.objects.create(
            user=user,
            client_type="individual",
            full_name="زبون معلق",
            phone="0555000999",
            email="commenter@example.com",
            account_status="active",
        )
        self.client.force_login(user)
        mail.outbox = []
        response = self._post_comment(name="زبون معلق", email="commenter@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("support@excellance-ms.dz", mail.outbox[0].to)

    def test_invalid_comment_sends_no_notification(self):
        from django.core import mail
        mail.outbox = []
        response = self._post_comment(text="")  # blank text -> form invalid
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)


class EnrollmentConfirmedAdminNotificationTestCase(TestCase):
    """Mirrors `CommentAdminNotificationTestCase`: once a client confirms
    an enrollment into an Active Purchase via `dashboard_confirm`, the
    admin inbox gets its own notification alongside the client's."""

    def setUp(self):
        self.session = FormationSession.objects.create(
            name="Session Confirm Notif", slug="session-confirm-notif", is_active=True
        )
        self.offering = Offering.objects.create(
            session=self.session,
            code="CFN01",
            title="Formation Confirm Notif",
            duration_months=2,
            is_active=True,
        )
        self.user = User.objects.create_user(
            username="confirm_notif_client", password="x", is_active=True
        )
        self.client_obj = Client.objects.create(
            user=self.user,
            client_type="individual",
            full_name="زبون تأكيد",
            phone="0555000777",
            email="confirmnotif@example.com",
            account_status="active",
        )
        self.participant = Participant.objects.create(
            client=self.client_obj, full_name="زبون تأكيد",
        )
        self.enrollment = Enrollment.objects.create(
            client=self.client_obj,
            participant=self.participant,
            offering=self.offering,
            status="accepted",
        )

    def test_confirming_sends_both_client_and_admin_emails(self):
        from django.core import mail
        self.client.force_login(self.user)
        mail.outbox = []
        self.client.post(
            reverse("enrollment:dashboard_confirm", args=[self.enrollment.pk]),
            follow=True,
        )
        self.assertEqual(len(mail.outbox), 2)
        recipients = [addr for msg in mail.outbox for addr in msg.to]
        self.assertIn("confirmnotif@example.com", recipients)
        self.assertIn("support@excellance-ms.dz", recipients)
        admin_mail = next(m for m in mail.outbox if "support@excellance-ms.dz" in m.to)
        self.assertIn(self.client_obj.display_name, admin_mail.alternatives[0][0])

    def test_no_admins_configured_still_sends_client_email(self):
        from django.core import mail
        from django.test import override_settings
        self.client.force_login(self.user)
        mail.outbox = []
        with override_settings(ADMINS=[]):
            self.client.post(
                reverse("enrollment:dashboard_confirm", args=[self.enrollment.pk]),
                follow=True,
            )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("confirmnotif@example.com", mail.outbox[0].to)


class EnquiryNotificationTestCase(TestCase):
    """Enquiries (offering-specific and general "talk to an advisor")
    previously sent no email at all. Now they get the same admin+visitor
    pair the actual contact form already sends."""

    def setUp(self):
        session = FormationSession.objects.create(
            name="Session Enquiry Notif", slug="session-enquiry-notif", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session,
            code="EQN01",
            title="Formation Enquiry Notif",
            duration_months=2,
            is_active=True,
        )
        self.detail_url = self.offering.get_absolute_url()

    def test_offering_enquiry_sends_admin_and_visitor_emails(self):
        from django.core import mail
        mail.outbox = []
        response = self.client.post(
            self.detail_url,
            {
                "form_type": "enquiry",
                "name": "زائر مستفسر",
                "phone": "0555111222",
                "email": "asker@example.com",
                "question": "هل هذا التخصص مفتوح للتسجيل؟",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)
        recipients = [addr for msg in mail.outbox for addr in msg.to]
        self.assertIn("support@excellance-ms.dz", recipients)
        self.assertIn("asker@example.com", recipients)
        admin_mail = next(m for m in mail.outbox if "support@excellance-ms.dz" in m.to)
        self.assertIn(self.offering.title, admin_mail.subject)

    def test_offering_enquiry_without_email_only_notifies_admin(self):
        from django.core import mail
        mail.outbox = []
        self.client.post(
            self.detail_url,
            {
                "form_type": "enquiry",
                "name": "زائر بدون بريد",
                "phone": "0555111333",
                "question": "سؤال بدون بريد إلكتروني؟",
            },
            follow=True,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("support@excellance-ms.dz", mail.outbox[0].to)

    def test_general_enquiry_sends_admin_and_visitor_emails(self):
        from django.core import mail
        mail.outbox = []
        response = self.client.post(
            reverse("enrollment:general_enquiry"),
            {
                "name": "زائر عام",
                "phone": "0555111444",
                "email": "general@example.com",
                "question": "أريد التحدث مع مستشار.",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)
        recipients = [addr for msg in mail.outbox for addr in msg.to]
        self.assertIn("support@excellance-ms.dz", recipients)
        self.assertIn("general@example.com", recipients)
        self.assertTrue(
            Enquiry.objects.filter(email="general@example.com", offering__isnull=True).exists()
        )

    def test_invalid_enquiry_sends_no_notification(self):
        from django.core import mail
        mail.outbox = []
        response = self.client.post(
            self.detail_url,
            {"form_type": "enquiry", "name": "", "question": ""},  # blank -> invalid
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)


class SessionChangeRequestTestCase(TestCase):
    """A client can propose an alternative session date on a confirmed
    enrollment ('مشترياتي'); this only logs the request and alerts the
    admin inbox — it never touches the actual (shared) session date."""

    def setUp(self):
        self.session = FormationSession.objects.create(
            name="Session Change Req", slug="session-change-req", is_active=True,
            start_date=date(2026, 10, 1),
        )
        self.offering = Offering.objects.create(
            session=self.session,
            code="SCR01",
            title="Formation Change Req",
            duration_months=2,
            is_active=True,
        )
        self.user = User.objects.create_user(
            username="change_req_client", password="x", is_active=True
        )
        self.client_obj = Client.objects.create(
            user=self.user,
            client_type="individual",
            full_name="زبون طلب تغيير",
            phone="0555222333",
            email="changereq@example.com",
            account_status="active",
        )
        self.participant = Participant.objects.create(
            client=self.client_obj, full_name="زبون طلب تغيير",
        )
        self.enrollment = Enrollment.objects.create(
            client=self.client_obj,
            participant=self.participant,
            offering=self.offering,
            status="confirmed",
            confirmed_at=timezone.now(),
        )
        self.url = reverse(
            "enrollment:dashboard_request_session_change", args=[self.enrollment.pk]
        )

    def test_only_confirmed_enrollment_owner_can_reach_the_form(self):
        other_user = User.objects.create_user(
            username="not_the_owner", password="x", is_active=True
        )
        self.client.force_login(other_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_pending_enrollment_cannot_request_a_change(self):
        self.enrollment.status = "pending"
        self.enrollment.confirmed_at = None
        self.enrollment.save()
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_submitting_creates_request_and_notifies_admin(self):
        from django.core import mail
        self.client.force_login(self.user)
        mail.outbox = []
        response = self.client.post(
            self.url,
            {"proposed_date": "2026-11-15", "reason": "تعارض مع موعد آخر."},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        change_request = SessionChangeRequest.objects.get(enrollment=self.enrollment)
        self.assertEqual(change_request.proposed_date, date(2026, 11, 15))
        self.assertEqual(change_request.status, SessionChangeRequest.STATUS_PENDING)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("support@excellance-ms.dz", mail.outbox[0].to)
        self.assertIn(self.client_obj.display_name, mail.outbox[0].alternatives[0][0])

    def test_second_submission_blocked_while_one_is_pending(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {"proposed_date": "2026-11-15", "reason": ""})
        from django.core import mail
        mail.outbox = []
        self.client.post(
            self.url, {"proposed_date": "2026-12-01", "reason": "محاولة ثانية"}, follow=True,
        )
        self.assertEqual(
            SessionChangeRequest.objects.filter(enrollment=self.enrollment).count(), 1
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_no_admins_configured_sends_no_email_but_still_logs_request(self):
        from django.core import mail
        from django.test import override_settings
        self.client.force_login(self.user)
        mail.outbox = []
        with override_settings(ADMINS=[]):
            self.client.post(self.url, {"proposed_date": "2026-11-15", "reason": ""})
        self.assertTrue(SessionChangeRequest.objects.filter(enrollment=self.enrollment).exists())
        self.assertEqual(len(mail.outbox), 0)


class AdminDashboardChartDataTestCase(TestCase):
    """The four Chart.js datasets on the admin dashboard used to be
    dumped straight from Python (`{{ by_status|safe }}` etc.) — that
    happened to look like a JS object literal for plain strings/ints,
    but `daily_last_week`'s `created_at__date` is a real `datetime.date`,
    whose Python repr (`datetime.date(2026, 9, 13)`) is not valid
    JavaScript at all, breaking every chart on the page. Now every
    dataset goes through `json_script`, which properly serializes dates
    via `DjangoJSONEncoder`."""

    def setUp(self):
        self.staff = User.objects.create_superuser(
            username="dash_admin", password="x", email="dash_admin@example.com"
        )
        session = FormationSession.objects.create(
            name="Session Dash", slug="session-dash", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session, code="DASH01", title="Formation Dash",
            duration_months=2, is_active=True,
        )
        user = User.objects.create_user(username="dash_client", password="x", is_active=True)
        client = Client.objects.create(
            user=user, client_type="individual", full_name="زبون",
            phone="0555999888", account_status="active",
        )
        participant = Participant.objects.create(client=client, full_name="زبون")
        Enrollment.objects.create(
            client=client, participant=participant, offering=self.offering, status="accepted",
        )

    def test_dashboard_renders_without_leaking_python_repr(self):
        self.client.force_login(self.staff)
        response = self.client.get("/admin/enrollment/enrollment/dashboard/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("datetime.date(", content)

    def test_dashboard_datasets_are_valid_json(self):
        import json
        import re

        self.client.force_login(self.staff)
        response = self.client.get("/admin/enrollment/enrollment/dashboard/")
        content = response.content.decode()
        for element_id in ("status-data", "source-data", "offering-data", "daily-data"):
            match = re.search(
                rf'<script id="{element_id}"[^>]*>(.*?)</script>', content, re.S
            )
            self.assertIsNotNone(match, f"missing json_script block: {element_id}")
            json.loads(match.group(1))  # raises if not valid JSON


class AccountantPurchaseNotificationTestCase(TestCase):
    """Once a client confirms an enrollment into an Active Purchase, the
    billing team (Accountant-group users with an email) gets its own
    notification alongside the client and admin ones."""

    def setUp(self):
        from django.contrib.auth.models import Group
        from django.core.management import call_command

        call_command("seed_accountant_group", verbosity=0)
        self.accountant_group = Group.objects.get(name="Accountant")

        session = FormationSession.objects.create(
            name="Session Accountant Notif", slug="session-accountant-notif", is_active=True
        )
        self.offering = Offering.objects.create(
            session=session, code="ACC01", title="Formation Accountant Notif",
            duration_months=2, is_active=True,
        )
        self.user = User.objects.create_user(
            username="accountant_notif_client", password="x", is_active=True
        )
        self.client_obj = Client.objects.create(
            user=self.user, client_type="individual", full_name="زبون محاسبة",
            phone="0555333444", email="accountantnotif@example.com", account_status="active",
        )
        self.participant = Participant.objects.create(
            client=self.client_obj, full_name="زبون محاسبة",
        )
        self.enrollment = Enrollment.objects.create(
            client=self.client_obj, participant=self.participant,
            offering=self.offering, status="accepted",
        )

    def test_confirming_notifies_accountant_alongside_client_and_admin(self):
        from django.core import mail

        accountant = User.objects.create_user(
            username="accountant_with_email", password="x", is_staff=True,
            email="accountant@example.com",
        )
        accountant.groups.add(self.accountant_group)

        self.client.force_login(self.user)
        mail.outbox = []
        self.client.post(
            reverse("enrollment:dashboard_confirm", args=[self.enrollment.pk]), follow=True,
        )
        self.assertEqual(len(mail.outbox), 3)
        recipients = [addr for msg in mail.outbox for addr in msg.to]
        self.assertIn("accountantnotif@example.com", recipients)
        self.assertIn("support@excellance-ms.dz", recipients)
        self.assertIn("accountant@example.com", recipients)

    def test_accountant_without_email_is_skipped(self):
        from django.core import mail

        accountant = User.objects.create_user(
            username="accountant_no_email", password="x", is_staff=True,
        )
        accountant.groups.add(self.accountant_group)

        self.client.force_login(self.user)
        mail.outbox = []
        self.client.post(
            reverse("enrollment:dashboard_confirm", args=[self.enrollment.pk]), follow=True,
        )
        recipients = [addr for msg in mail.outbox for addr in msg.to]
        self.assertNotIn("", recipients)
        self.assertEqual(len(mail.outbox), 2)  # client + admin only

    def test_inactive_accountant_is_skipped(self):
        from django.core import mail

        accountant = User.objects.create_user(
            username="accountant_inactive", password="x", is_staff=True,
            email="inactive_accountant@example.com", is_active=False,
        )
        accountant.groups.add(self.accountant_group)

        self.client.force_login(self.user)
        mail.outbox = []
        self.client.post(
            reverse("enrollment:dashboard_confirm", args=[self.enrollment.pk]), follow=True,
        )
        recipients = [addr for msg in mail.outbox for addr in msg.to]
        self.assertNotIn("inactive_accountant@example.com", recipients)

    def test_no_accountant_group_at_all_does_not_break_confirmation(self):
        from django.contrib.auth.models import Group
        from django.core import mail

        Group.objects.filter(name="Accountant").delete()
        self.client.force_login(self.user)
        mail.outbox = []
        response = self.client.post(
            reverse("enrollment:dashboard_confirm", args=[self.enrollment.pk]), follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, "confirmed")
        self.assertEqual(len(mail.outbox), 2)  # client + admin only


class SeedAccountantUserCommandTestCase(TestCase):
    """The minimal, standalone command that gets a single Accountant
    account (with an email) into an environment that isn't running the
    full `seed_demo_users` demo dataset."""

    def test_creates_group_membership_and_email(self):
        from django.contrib.auth.models import Group
        from django.core.management import call_command

        call_command("seed_accountant_user")

        group = Group.objects.get(name="Accountant")
        user = User.objects.get(username="comptable")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(user.email, "comptable@eems.dz")
        self.assertIn(group, user.groups.all())

    def test_respects_env_var_overrides(self):
        from django.core.management import call_command
        from django.test import override_settings
        import os

        os.environ["EEMS_ACCOUNTANT_USERNAME"] = "compta_custom"
        os.environ["EEMS_ACCOUNTANT_EMAIL"] = "custom@example.com"
        try:
            call_command("seed_accountant_user")
            user = User.objects.get(username="compta_custom")
            self.assertEqual(user.email, "custom@example.com")
        finally:
            os.environ.pop("EEMS_ACCOUNTANT_USERNAME", None)
            os.environ.pop("EEMS_ACCOUNTANT_EMAIL", None)

    def test_is_idempotent_and_does_not_reset_existing_flags(self):
        from django.core.management import call_command

        call_command("seed_accountant_user")
        user = User.objects.get(username="comptable")
        user.is_active = False
        user.save(update_fields=["is_active"])

        call_command("seed_accountant_user")  # must not raise or duplicate
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(User.objects.filter(username="comptable").count(), 1)
