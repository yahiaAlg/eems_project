import json
import time

from django.test import TestCase, override_settings

from enrollment.models import FormationSession, Offering

from . import signing
from .models import FormationLink

URL = "/internal/sync/formation/"
SECRET = "s3cret"


def payload(**over):
    p = {
        "isi_id": 7,
        "code": "HSE0101",
        "specialty_code": "",
        "fields": {
            "title": "Sécurité incendie",
            "branch_label": "HSE",
            "duration_days": 3,
            "seats_available": 12,
            "is_active": True,
        },
        "fiche": {
            "description": "Desc A.",
            "objectives": "Obj 1\nObj 2",
            "program_outline": "Mod 1\nMod 2",
            "main_tasks": "Task 1",
            "prerequisites": "Aucun prérequis particulier",
        },
    }
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(p.get(k), dict):
            p[k] = {**p[k], **v}
        else:
            p[k] = v
    return p


@override_settings(SYNC_SHARED_SECRET=SECRET, BRIDGE_CATALOGUE_SLUG="catalogue-eems")
class FormationUpsertTests(TestCase):
    def setUp(self):
        self.session = FormationSession.objects.create(name="Catalogue", slug="catalogue-eems")

    def post(self, data, ts=None, secret=SECRET, sig=None):
        body = json.dumps(data).encode()
        ts = ts or int(time.time())
        return self.client.post(
            URL,
            data=body,
            content_type="application/json",
            HTTP_X_SYNC_TIMESTAMP=str(ts),
            HTTP_X_SYNC_SIGNATURE=sig or signing.sign(secret, ts, body),
        )

    def test_rejects_bad_signature(self):
        self.assertEqual(self.post(payload(), secret="wrong").status_code, 403)
        self.assertEqual(Offering.objects.count(), 0)

    def test_rejects_stale_timestamp(self):
        self.assertEqual(self.post(payload(), ts=int(time.time()) - 3600).status_code, 403)

    def test_rejects_when_no_secret_configured(self):
        with override_settings(SYNC_SHARED_SECRET="", INSTITUTE_PING_SECRET=""):
            self.assertEqual(self.post(payload()).status_code, 403)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(URL).status_code, 405)

    def test_creates_offering_with_fiche_in_auto_mode(self):
        r = self.post(payload())
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertTrue(data["created"])
        o = Offering.objects.get(pk=data["offering_id"])
        self.assertEqual((o.code, o.title, o.duration_days, o.seats_available), ("HSE0101", "Sécurité incendie", 3, 12))
        self.assertEqual(o.fiche_technique_mode, "auto")
        self.assertEqual(o.objectives_list, ["Obj 1", "Obj 2"])
        self.assertTrue(o.is_active)
        self.assertEqual(o.slug, "securite-incendie")
        self.assertTrue(FormationLink.objects.filter(isi_formation_id=7, offering=o).exists())

    def test_repush_is_idempotent(self):
        self.post(payload())
        r = self.post(payload())
        self.assertFalse(r.json()["created"])
        self.assertEqual(Offering.objects.count(), 1)

    def test_adopts_existing_offering_by_code_and_title(self):
        existing = Offering.objects.create(
            session=self.session, code="HSE0101", title="sécurité  incendie", description="Texte du site"
        )
        r = self.post(payload())
        self.assertFalse(r.json()["created"])
        self.assertEqual(Offering.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.description, "Texte du site")  # not overwritten
        self.assertEqual(existing.objectives, "Obj 1\nObj 2")  # empty -> filled

    def test_isi_changes_update_untouched_fields(self):
        self.post(payload())
        r = self.post(payload(fiche={"description": "Desc B."}, fields={"duration_days": 5}))
        o = Offering.objects.get()
        self.assertEqual((o.description, o.duration_days), ("Desc B.", 5))
        self.assertIn("description", r.json()["written"])

    def test_staff_edits_on_website_are_kept(self):
        self.post(payload())
        o = Offering.objects.get()
        o.description = "Réécrit par le staff"
        o.save()
        r = self.post(payload(fiche={"description": "Desc B.", "objectives": "Nouvel objectif"}))
        o.refresh_from_db()
        self.assertEqual(o.description, "Réécrit par le staff")
        self.assertEqual(o.objectives, "Nouvel objectif")
        self.assertIn("description", r.json()["skipped"])

    def test_custom_fiche_mode_is_never_overwritten(self):
        self.post(payload())
        Offering.objects.update(fiche_technique_mode="custom")
        self.post(payload(fiche={"objectives": "Autre"}))
        self.assertEqual(Offering.objects.get().objectives, "Obj 1\nObj 2")

    def test_deactivation_is_mirrored(self):
        self.post(payload())
        self.post(payload(fields={"is_active": False}))
        self.assertFalse(Offering.objects.get().is_active)

    def test_missing_catalogue_session_gives_409(self):
        self.session.delete()
        self.assertEqual(self.post(payload()).status_code, 409)

    def test_bad_payload_gives_400(self):
        self.assertEqual(self.post({"isi_id": 1, "code": "", "fields": {}}).status_code, 400)

    def test_ping(self):
        ts = int(time.time())
        body = b"{}"
        r = self.client.post(
            "/internal/sync/ping/", data=body, content_type="application/json",
            HTTP_X_SYNC_TIMESTAMP=str(ts), HTTP_X_SYNC_SIGNATURE=signing.sign(SECRET, ts, body),
        )
        self.assertEqual(r.status_code, 200)
