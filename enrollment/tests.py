from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .models import (
    Cart,
    CartItem,
    Client,
    Enrollment,
    FormationSession,
    Offering,
    Participant,
    ProformaInvoice,
    ProformaInvoiceItem,
    QuoteRequest,
    QuoteRequestItem,
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
