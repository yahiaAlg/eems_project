from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from enrollment.models import FormationSession, Offering
from pages.emails import send_branded_mail


class OfferingCodeAndDurationTests(TestCase):
    def setUp(self):
        self.session = FormationSession.objects.create(
            name="S", slug="s", start_date="2026-01-01"
        )

    def _make(self, title, **kw):
        return Offering.objects.create(
            session=self.session, code="MEE2512", title=title, seats_available=5, **kw
        )

    def test_same_code_allowed_and_urls_stay_distinct(self):
        a, b = self._make("Superviseur HSE"), self._make("Produits Chimiques")
        self.assertEqual((a.code, b.code), ("MEE2512", "MEE2512"))
        self.assertNotEqual(a.get_absolute_url(), b.get_absolute_url())
        self.assertContains(self.client.get(b.get_absolute_url()), "Produits Chimiques")
        self.assertContains(self.client.get(a.get_absolute_url()), "Superviseur HSE")

    def test_legacy_code_url_still_resolves(self):
        a = self._make("Superviseur HSE")
        url = reverse("enrollment:detail", args=[self.session.slug, "MEE2512"])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_duration_rules(self):
        o = self._make("a", duration_days=15, duration_months=1)
        self.assertIsNone(o.duration_months)
        self.assertEqual(o.duration_display, "15 يوما")
        o = self._make("b", duration_days=60)
        self.assertEqual((o.duration_months, o.duration_display), (2, "2 شهرين"))
        o = self._make("c", duration_days=75)
        self.assertIsNone(o.duration_months)
        self.assertEqual(o.duration_display, "2 شهرين و 15 يوما")
        o = self._make("d", duration_months=3)  # months only -> days = 90
        self.assertEqual((o.duration_days, o.duration_display), (90, "3 أشهر"))
        o = self._make("e")
        self.assertEqual(o.duration_display, "")


class MailboxRoutingTests(TestCase):
    def test_support_is_default_and_inscription_is_selectable(self):
        seen, creds = [], []
        import pages.emails as pe
        real = pe.EmailMultiAlternatives
        real_gc = pe.get_connection

        def spy_gc(*a, **kw):
            creds.append(kw)
            return real_gc(*a, **kw)

        pe.get_connection = spy_gc

        class Spy(real):
            def __init__(self, *a, **kw):
                seen.append((kw["from_email"], kw["connection"]))
                super().__init__(*a, **kw)

        pe.EmailMultiAlternatives = Spy
        try:
            send_branded_mail("emails/newsletter_confirmation.html", "x", ["a@b.c"])
            send_branded_mail(
                "emails/newsletter_confirmation.html", "x", ["a@b.c"], account="inscription"
            )
        finally:
            pe.EmailMultiAlternatives = real
            pe.get_connection = real_gc
        self.assertIn("support@excellance-ms.dz", seen[0][0])
        self.assertIsNone(seen[0][1])
        self.assertIn("inscription@excellance-ms.dz", seen[1][0])
        self.assertEqual(creds[0]["username"], "inscription@excellance-ms.dz")
        self.assertEqual(creds[0]["password"], "system2026*")
