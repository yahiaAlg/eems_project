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

---

# Accounts, cart, wishlist, proforma & tarification (Phase 1–9)

Full role-based client system on top of the subscription flow above, built
across `accounts` (new app) and extensions to `enrollment`. Summary — see
`TODO.md` for the phase-by-phase spec and `docs/TESTING_ACCOUNTS_AND_CHECKOUT.md`
for the manual test matrix.

## Accounts (Phase 1)
Real `django.contrib.auth.User` login (no custom `AUTH_USER_MODEL`) replaces
the old phone/session dashboard login. Public registration (individual or
enterprise) creates an inactive user + a `pending` `Client`; an admin action
("تفعيل الحساب وإرسال بيانات الدخول") generates a random password, activates
the account, and emails the credentials once. Login/logout/password-reset
live under `/account/...` via Django's built-in views with branded templates.
"VIP"/"Normal" Groups mirror `Client.is_vip` automatically (`accounts.signals`).

## Profile & enterprise legal info (Phase 2)
`Client` gained the full enterprise legal/accounting field set (forme
juridique, NIF, NIS, RIB, TVA exemption, billing contact, ...). A "My
Profile" page lets clients edit their own record; a VIP enterprise can't
submit a proforma request until those fields are complete.

## Role-based pricing (Phase 3)
Base prices are omitted from the rendered HTML entirely for anonymous and
non-VIP visitors — everywhere a price could appear (catalog, detail, cart,
checkout, purchase history).

## Cart & wishlist (Phase 4)
`Cart`/`CartItem` (trainer selection VIP-only, enforced server-side) and
`WishlistItem` replace the old single-offering subscribe flow as the primary
entry point; the legacy direct-subscribe route still works.

## Checkout, branched by role (Phase 5)
VIP → "Request Proforma" (billing basis + trainer per line + optional bon de
commande upload) → `ProformaInvoice`/`ProformaInvoiceItem`, cart lines frozen
at submission time. Non-VIP → "Request Quote" (offering + participant count
only) → `QuoteRequest`/`QuoteRequestItem`, priced later by staff. Both flows
lock/clear the source cart on submit.

## Tarification (Phase 6)
"Accountant" Group scoped to viewing/pricing `ProformaInvoice`/`QuoteRequest`
only. Admin/accountant sets `unit_price`+`billing_basis` per quote line;
once fully priced, a printable invoice is generated the same way as a VIP
proforma (plain HTML + `@media print`, no PDF library) and surfaced in the
client's "My Purchases".

## Notification emails (Phase 7)
Dedicated templates (all extending `emails/base_email.html`) for: pending
account, activated + credentials, password reset, VIP proforma → admin/
accountant (with the bon de commande attached/linked), non-VIP quote →
admin/accountant, and quote-priced → client.

## Client space overhaul (Phase 8)
`/mon-espace/` rebuilt with Profile, Active Purchases, Cart, Wishlist,
Request History, and Chart.js-based Metrics — all re-checked against the
Phase 3 pricing rule.

## QA & polish (Phase 9)
- Manual test matrix documented in `docs/TESTING_ACCOUNTS_AND_CHECKOUT.md`.
- New `accounts.seed_demo_users` management command (idempotent) seeds a
  VIP individual, a VIP enterprise (legal info pre-filled, clears the Phase
  2.3 gate), a Normal individual, a Normal enterprise, and an Accountant
  staff login — wired into `reseed_all.sh`.
- This README/CHANGES update.

## Files touched (Phase 1–9, high level)
Added: `accounts/` (app), `enrollment/{cart,wishlist,proforma,quote}`-related
model/view/template additions, `accounts/management/commands/{seed_account_groups,
seed_accountant_group,seed_demo_users}.py`, `emails/*` templates for the new
notifications, `docs/TESTING_ACCOUNTS_AND_CHECKOUT.md`.
Modified: `enrollment/{models,forms,views,urls,admin,signals}.py`,
`eems_project/settings.py` (INSTALLED_APPS), `reseed_all.sh`, `README.md`.
