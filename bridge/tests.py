import json
import time

from django.test import TestCase, override_settings

from enrollment.models import (
    Client, Enrollment, EnrollmentParticipant, FormationSession, Offering, Participant,
)

from .formation_sync import deactivate_offerings, upsert_offering
from .models import ContactPlaceholder, FormationLink, SyncEvent
from .security import sign
from .snapshot import client_snapshot

SECRET = "unit-secret"


def payload(**kw):
    p = {
        "isi_formation_id": 7, "code": "MEE2512", "website_code": "MEE2512",
        "title": "Habilitation électrique", "title_ar": "", "category": "HSE",
        "specialty": {"branch_abbr": "MEE", "branch_name": "Maintenance", "branch_name_ar": "الصيانة",
                      "code": "2512", "title": "Electricien", "title_ar": ""},
        "duration_days": 3, "duration_hours": 21, "max_participants": 12, "is_active": True,
        "fiche": {"description": "Desc.", "objectives": "A\nB", "program_outline": "P1\nP2",
                  "main_tasks": "T1", "prerequisites": "Aucun"},
    }
    p.update(kw)
    return p


class SignedClient:
    def signed(self, method, path, data=None):
        body = json.dumps(data).encode() if data is not None else b""
        ts = str(int(time.time()))
        return self.client.generic(
            method, path, body, content_type="application/json",
            HTTP_X_SYNC_TIMESTAMP=ts, HTTP_X_SYNC_SIGNATURE=sign(SECRET, ts, method, path, body),
        )


@override_settings(SYNC_SHARED_SECRET=SECRET)
class SecurityTests(TestCase):
    def test_unsigned_rejected(self):
        self.assertEqual(self.client.get("/internal/sync/feed/?mode=head").status_code, 403)

    def test_bad_signature_and_stale_timestamp(self):
        path = "/internal/sync/feed/?mode=head"
        r = self.client.get(path, HTTP_X_SYNC_TIMESTAMP=str(int(time.time())), HTTP_X_SYNC_SIGNATURE="x" * 64)
        self.assertEqual(r.status_code, 403)
        old = str(int(time.time()) - 3600)
        r = self.client.get(path, HTTP_X_SYNC_TIMESTAMP=old, HTTP_X_SYNC_SIGNATURE=sign(SECRET, old, "GET", path, b""))
        self.assertEqual(r.status_code, 403)

    @override_settings(SYNC_SHARED_SECRET="")
    def test_disabled_without_secret(self):
        self.assertEqual(self.client.get("/internal/sync/feed/?mode=head").status_code, 404)


class FormationSyncTests(TestCase):
    def test_create_builds_offering_with_auto_fiche(self):
        r = upsert_offering(payload())
        self.assertTrue(r["created"])
        o = Offering.objects.get(pk=r["offering_id"])
        self.assertEqual((o.code, o.duration_days, o.seats_available), ("MEE2512", 3, 12))
        self.assertEqual(o.slug, "habilitation-electrique")
        self.assertEqual(o.fiche_technique_mode, "auto")
        self.assertEqual(o.objectives_list, ["A", "B"])
        self.assertTrue(o.has_fiche_technique)
        self.assertEqual(o.specialty.code, "MEE2512")
        self.assertEqual(o.session.slug, "catalogue-eems")
        self.assertFalse(o.is_active)            # hidden until staff review & publish
        self.assertFalse(r["is_active"])

    @override_settings(ADMINS=[("Admin", "support@example.test")],
                       EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_new_formation_emails_support_and_is_searchable_in_french(self):
        from django.core import mail
        from django.test import TestCase as _T
        with self.captureOnCommitCallbacks(execute=True):
            r = upsert_offering(payload(title="Analyse de Données", title_ar="تحليل البيانات"))
        o = Offering.objects.get(pk=r["offering_id"])
        self.assertEqual(o.title, "تحليل البيانات")          # Arabic title shown...
        self.assertIn("analyse", o.slug)                       # ...French findable via slug search
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["support@example.test"])
        self.assertIn("MEE2512", mail.outbox[0].subject)
        # an update (not a creation) must not re-notify
        with self.captureOnCommitCallbacks(execute=True):
            upsert_offering(payload(title="Analyse de Données", title_ar="تحليل البيانات", max_participants=15))
        self.assertEqual(len(mail.outbox), 1)

    def test_admin_banner_filter_and_french_search(self):
        from django.contrib.auth import get_user_model
        U = get_user_model()
        U.objects.create_superuser("adm", "a@b.c", "pw")
        self.client.login(username="adm", password="pw")
        upsert_offering(payload(title="Analyse de Données", title_ar="تحليل البيانات"))
        r = self.client.get("/admin/enrollment/offering/?q=Analyse", follow=True)
        self.assertContains(r, "MEE2512")
        self.assertContains(r, "isi_review=pending")           # alert banner
        r = self.client.get("/admin/enrollment/offering/?isi_review=pending")
        self.assertContains(r, "MEE2512")

    @override_settings(SYNC_NEW_OFFERINGS_ACTIVE=True)
    def test_can_publish_immediately_by_setting(self):
        r = upsert_offering(payload())
        self.assertTrue(Offering.objects.get(pk=r["offering_id"]).is_active)

    def test_isi_inactive_stays_inactive_even_with_publish_setting(self):
        with override_settings(SYNC_NEW_OFFERINGS_ACTIVE=True):
            r = upsert_offering(payload(is_active=False))
        self.assertFalse(Offering.objects.get(pk=r["offering_id"]).is_active)

    def test_staff_publish_survives_unrelated_isi_edit(self):
        r = upsert_offering(payload())
        o = Offering.objects.get(pk=r["offering_id"]); o.is_active = True; o.save()   # published by staff
        upsert_offering(payload(duration_days=6))
        o.refresh_from_db()
        self.assertTrue(o.is_active)
        self.assertEqual(o.duration_days, 6)

    def test_deactivate_hides_but_keeps_offering(self):
        r = upsert_offering(payload())
        o = Offering.objects.get(pk=r["offering_id"]); o.is_active = True; o.save()
        self.assertEqual(deactivate_offerings([7, 999]), [7])
        o.refresh_from_db()
        self.assertFalse(o.is_active)
        upsert_offering(payload(duration_days=5))        # unrelated later edit must not re-publish
        o.refresh_from_db()
        self.assertFalse(o.is_active)

    def test_idempotent(self):
        upsert_offering(payload())
        r = upsert_offering(payload())
        self.assertEqual(r["updated"], [])
        self.assertEqual(Offering.objects.count(), 1)

    def test_isi_change_updates_but_website_edits_survive(self):
        r = upsert_offering(payload())
        o = Offering.objects.get(pk=r["offering_id"])
        o.objectives = "Hand edited"          # staff edit on the website
        o.is_active = False                   # staff hid it
        o.save()
        fiche = dict(payload()["fiche"], objectives="A\nB\nC", program_outline="P1\nP2\nP3")
        r2 = upsert_offering(payload(duration_days=5, fiche=fiche))
        o.refresh_from_db()
        self.assertEqual(o.duration_days, 5)                 # ISI changed it -> applied
        self.assertEqual(o.objectives, "Hand edited")        # hand-edited fiche text kept
        self.assertEqual(o.program_outline, "P1\nP2\nP3")    # untouched text follows ISI
        self.assertFalse(o.is_active)                        # ISI didn't change it -> not overwritten
        self.assertIn("duration_days", r2["updated"])

    def test_adopts_existing_offering_without_overwriting(self):
        s = FormationSession.objects.create(name="x", slug="catalogue-eems")
        existing = Offering.objects.create(session=s, code="MEE2512", title="Habilitation électrique",
                                           description="Mine", duration_days=9)
        r = upsert_offering(payload())
        self.assertTrue(r["adopted"])
        existing.refresh_from_db()
        self.assertEqual((existing.description, existing.duration_days), ("Mine", 9))
        self.assertEqual(existing.objectives, "A\nB")        # blank -> filled
        self.assertEqual(Offering.objects.count(), 1)
        self.assertEqual(FormationLink.objects.get().offering_id, existing.pk)

    def test_recreated_after_deletion_readopts_same_offering(self):
        r = upsert_offering(payload())
        deactivate_offerings([7])
        r2 = upsert_offering(payload(isi_formation_id=99))        # ISI re-seeded: new id, same code+title
        self.assertTrue(r2["adopted"])
        self.assertEqual(r2["offering_id"], r["offering_id"])
        self.assertEqual(Offering.objects.count(), 1)
        link = FormationLink.objects.get()
        self.assertEqual((link.isi_formation_id, link.deleted_in_isi), (99, False))
        self.assertFalse(Offering.objects.get().is_active)        # still hidden: staff re-publish

    def test_same_title_gets_unique_slug(self):
        upsert_offering(payload())
        r = upsert_offering(payload(isi_formation_id=8, code="MEE9", website_code="MEE9", specialty=None))
        self.assertEqual(Offering.objects.get(pk=r["offering_id"]).slug, "habilitation-electrique-2")


@override_settings(SYNC_SHARED_SECRET=SECRET)
class FeedTests(SignedClient, TestCase):
    def setUp(self):
        self.s = FormationSession.objects.create(name="x", slug="catalogue-eems")
        self.o = Offering.objects.create(session=self.s, code="C1", title="T1", slug="t1")

    def _enterprise(self, status="active"):
        c = Client.objects.create(client_type="enterprise", company_name="ACME", phone="0550000000",
                                  responsible_name="Boss Man", trade_register_number="RC1", account_status=status)
        placeholder = Participant.objects.create(client=c, full_name="Boss Man")
        ContactPlaceholder.objects.create(participant=placeholder)      # as the web form now does
        return c, Enrollment.objects.create(client=c, participant=placeholder, offering=self.o, status="accepted")

    def test_individual_snapshot(self):
        c = Client.objects.create(client_type="individual", full_name="Amine Benali", phone="0550000001", gender="m")
        p = Participant.objects.create(client=c, full_name="Amine Benali", gender="m")
        Enrollment.objects.create(client=c, participant=p, offering=self.o)
        snap = client_snapshot(c)
        self.assertEqual(snap["type"], "individual")
        (line,) = snap["roster"]
        self.assertEqual((line["ext_id"].startswith("en:"), line["full_name"], line["gender"]),
                         (True, "Amine Benali", "M"))
        self.assertEqual(line["offering"]["code"], "C1")

    def test_enterprise_roster_replaces_placeholder(self):
        c, e = self._enterprise()
        self.assertEqual(client_snapshot(c)["roster"], [])   # placeholder contact is not a trainee
        EnrollmentParticipant.objects.create(enrollment=e, first_name="Ali", last_name="Kaci", employer="")
        (line,) = client_snapshot(c)["roster"]
        self.assertTrue(line["ext_id"].startswith("ep:"))
        self.assertEqual((line["first_name"], line["employer"]), ("Ali", "ACME"))

    def test_unmarked_single_participant_with_contact_name_is_a_real_trainee(self):
        """No more name guessing: only explicitly marked placeholders are skipped."""
        c = Client.objects.create(client_type="enterprise", company_name="ACME", phone="0550000000",
                                  responsible_name="Boss Man")
        Enrollment.objects.create(client=c, participant=Participant.objects.create(client=c, full_name="Boss Man"),
                                  offering=self.o)
        self.assertEqual([l["full_name"] for l in client_snapshot(c)["roster"]], ["Boss Man"])

    def test_legacy_placeholders_marked_by_migration_step(self):
        from importlib import import_module
        from django.apps import apps as real_apps
        mig = import_module("bridge.migrations.0002_contact_placeholder")
        legacy = Client.objects.create(client_type="enterprise", company_name="OLD", phone="1", responsible_name="Old Boss")
        p = Participant.objects.create(client=legacy, full_name="Old Boss")
        multi = Client.objects.create(client_type="enterprise", company_name="API", phone="2", responsible_name="X Y")
        Participant.objects.create(client=multi, full_name="X Y"); Participant.objects.create(client=multi, full_name="Z W")
        mig.mark_legacy_placeholders(real_apps, None)
        self.assertTrue(hasattr(Participant.objects.get(pk=p.pk), "contact_placeholder"))
        self.assertEqual(ContactPlaceholder.objects.count(), 1)

    def test_web_form_marks_enterprise_contact_as_placeholder(self):
        # Regression guard: the enterprise branch of the web enrollment form must mark
        # its contact participant (no existing test posts that form end to end).
        import inspect
        from enrollment import views
        src = inspect.getsource(views)
        self.assertIn("ContactPlaceholder.objects.get_or_create(participant=participant)", src)

    def test_api_style_enterprise_uses_participants(self):
        c = Client.objects.create(client_type="enterprise", company_name="ACME", phone="0550000000",
                                  responsible_name="Boss Man")
        for n in ("Ali Kaci", "Sara Nour"):
            Enrollment.objects.create(client=c, participant=Participant.objects.create(client=c, full_name=n),
                                      offering=self.o)
        self.assertEqual(sorted(l["full_name"] for l in client_snapshot(c)["roster"]), ["Ali Kaci", "Sara Nour"])

    def test_rejected_and_cancelled_dropped_pending_account_is_tombstone(self):
        c, e = self._enterprise()
        e.status = "cancelled"; e.save()
        EnrollmentParticipant.objects.create(enrollment=e, first_name="Ali", last_name="Kaci")
        self.assertEqual(client_snapshot(c)["roster"], [])
        c.account_status = "pending"; c.save()
        self.assertTrue(client_snapshot(c)["deleted"])

    def test_events_and_feed_cursor(self):
        with self.captureOnCommitCallbacks(execute=True):
            c, e = self._enterprise()
            EnrollmentParticipant.objects.create(enrollment=e, first_name="Ali", last_name="Kaci")
        self.assertEqual(SyncEvent.objects.filter(client_id=c.pk).count(), 1)   # collapsed
        head = self.signed("GET", "/internal/sync/feed/?mode=head").json()["cursor"]
        self.assertGreater(head, 0)
        path = "/internal/sync/feed/?cursor=0&limit=50"
        data = self.signed("GET", path).json()
        self.assertEqual([x["ext_id"] for x in data["clients"]], [c.pk])
        self.assertEqual(len(data["clients"][0]["roster"]), 1)
        self.assertFalse(data["has_more"])
        nxt = self.signed("GET", f"/internal/sync/feed/?cursor={data['cursor']}&limit=50").json()
        self.assertEqual(nxt["clients"], [])
        # a later change shows up again
        with self.captureOnCommitCallbacks(execute=True):
            EnrollmentParticipant.objects.create(enrollment=e, first_name="Sara", last_name="Nour")
        again = self.signed("GET", f"/internal/sync/feed/?cursor={data['cursor']}&limit=50").json()
        self.assertEqual(len(again["clients"][0]["roster"]), 2)

    def test_deleted_client_is_tombstone_and_full_mode(self):
        with self.captureOnCommitCallbacks(execute=True):
            c, _ = self._enterprise()
            pk = c.pk
            c.delete()
        data = self.signed("GET", "/internal/sync/feed/?cursor=0&limit=50").json()
        self.assertEqual(data["clients"], [{"ext_id": pk, "deleted": True, "reason": "removed"}])
        c2, _ = self._enterprise()
        full = self.signed("GET", "/internal/sync/feed/?mode=full&after_id=0&limit=50").json()
        self.assertEqual([x["ext_id"] for x in full["clients"]], [c2.pk])

    def test_head_reports_max_client_id(self):
        c, _ = self._enterprise()
        data = self.signed("GET", "/internal/sync/feed/?mode=head").json()
        self.assertEqual(data["max_client_id"], c.pk)

    def test_deactivate_endpoint(self):
        upsert_offering(payload())
        r = self.signed("POST", "/internal/sync/formations/deactivate/", {"isi_formation_ids": [7]})
        self.assertEqual(r.json(), {"deactivated": [7]})

    def test_formations_endpoint(self):
        r = self.signed("POST", "/internal/sync/formations/", payload())
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["results"][0]["created"])
