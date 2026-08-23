# Subscription flow — what changed

Extract this zip over your project root (`eems_project/`), same paths, then:

```
python manage.py migrate
```

That's it — no reseed required (a data migration fixes the already-seeded navbar/footer URLs for you).

## 1. Specialty detail page CTA

Already existed (`_fiche_technique.html` → `.btn-enroll` → `enrollment:subscribe`), added Aug 2. Left as-is — flag if you meant something else (placement/prominence).

## 2. General, branch-first subscription entry point (new)

- `GET /formations/inscription/` — new page: branch → specialty → training, each select populated via AJAX as the previous one is chosen. Only branches/specialties that currently have an **open offering** are shown (not the full ~500-entry nomenclature). Picking a training navigates straight into the existing per-offering `enrollment:subscribe` form — no duplicate form logic.
- New endpoints: `enrollment:ajax_specialties` (`?branch=<id>`), `enrollment:ajax_offerings` (`?specialty=<code>`).
- Navbar "التسجيل الإلكتروني" button and footer "سجّل في تكوين" link now point here instead of the catalog (`seed_data.py` updated + `pages/migrations/0009_fix_enrollment_cta_urls.py` patches existing rows).

## 3. Profile dashboard + subscription CRUD (new)

No password system existed anywhere in the project, so I used the lightest thing that's actually real: **phone-based session login** — the phone number typed at subscription time doubles as the login identifier (no password invented). Flagging this as the one real judgment call in this task; say the word if you want a different auth model instead.

- On successful subscribe, the client is auto-logged in and redirected to `GET /mon-espace/` (dashboard) instead of the old static thank-you page.
- Returning visitors: `GET /mon-espace/connexion/` — enter the same phone number, land back on the dashboard. `/mon-espace/deconnexion/` logs out. A "مساحتي" link was added to the navbar.
- Dashboard lists every enrollment tied to that phone (across sessions/offerings) with:
  - **تأكيد (confirm)** → POST `/mon-espace/<id>/confirmer/`. Sends a confirmation email (new template `emails/enrollment_confirmed.html`) if the client gave one, and locks the row.
  - **إلغاء (cancel)** → POST `/mon-espace/<id>/annuler/`. Disabled once confirmed.
  - Both actions are enforced server-side (404 on cross-client tampering, blocked once locked), not just hidden in the UI — verified with a test client.
- `Enrollment.status` gained `confirmed` / `cancelled` choices, plus `confirmed_at` / `cancelled_at` timestamps and `can_confirm` / `can_cancel` properties. `seats_taken` now also counts `confirmed` as an occupied seat.

## Files touched

Modified: `enrollment/{forms,models,urls,views}.py`, `enrollment/templatetags/enrollment_extras.py`, `pages/management/commands/seed_data.py`, `pages/templates/pages/partials/_navbar.html`.
Added: `enrollment/migrations/0010_...py`, `pages/migrations/0009_fix_enrollment_cta_urls.py`, `enrollment/templates/enrollment/{subscribe_general,dashboard,dashboard_login}.html`, `pages/templates/emails/enrollment_confirmed.html`, `enrollment/static/enrollment/css/{subscribe_general,dashboard}.css`, `enrollment/static/enrollment/js/subscribe_general.js`.

## Tested (Django test client, sqlite)

Full chain branch→specialty→offering→subscribe→dashboard; confirm locks cancel; direct POST to cancel a confirmed enrollment is rejected; cross-client tampering on another phone's enrollment returns 404; unauthenticated `/mon-espace/` redirects to login; unknown-phone login shows an error; confirmation email renders and sends (locmem backend).
