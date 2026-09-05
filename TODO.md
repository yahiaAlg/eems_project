# EEMS → Training E-Commerce Platform — TODO

Context: Django project `eems_project`, app `enrollment` (models: `Client`, `Participant`,
`Enrollment`, `Offering`, `FormationSession`, `Formateur`), app `pages` (has `send_branded_mail`
helper in `pages/emails.py`). Client login today is phone/session-based (`dashboard_login`,
`CLIENT_PHONE_SESSION_KEY`) with **no Django auth User yet**. Default `django.contrib.auth.User`
is in use (no custom `AUTH_USER_MODEL`).

Feed these tasks to the AI **one at a time, in order**. Each task assumes all prior tasks are done.
Do not skip ahead — later tasks depend on models/fields created earlier.

---

## Phase 1 — Auth Foundation (Django built-in)

- [x] **1.1** Create an `accounts` app. Add `is_vip` (bool, default False) and `account_status`
  (choices: `pending`, `active`, `rejected`) fields — either directly on `Client` or on a new
  `Client.user` link table. Do not create a custom `AUTH_USER_MODEL`; use `django.contrib.auth.User`.
- [x] **1.2** Add `Client.user = OneToOneField(User, null=True, blank=True)`. Write a data
  migration plan note (no need to backfill existing rows with real users; nullable is fine for
  legacy walk-in clients created by admins).
- [x] **1.3** Build a public registration view/form covering both individual and enterprise
  signup (reuse the field split already used in `Client`: individual vs enterprise fields).
  On submit: create `User(is_active=False)` + linked `Client(account_status="pending")`. Send an
  admin-notification email via `send_branded_mail` ("new account pending approval").
- [x] **1.4** Add a Django admin action on `Client`/`User`: "Activate & send credentials" —
  generates a strong random password (`django.utils.crypto.get_random_string` or
  `secrets.token_urlsafe`), calls `user.set_password(...)`, sets `is_active=True` and
  `account_status="active"`, then emails the username + generated password to the client via a
  dedicated `send_branded_mail` template. Never log or display the plaintext password anywhere
  except that one email.
- [x] **1.5** Wire `django.contrib.auth.urls` for login/logout under `/account/`, with templates
  matching the existing site chrome (extend `pages/templates/pages/base.html`). Block login for
  `is_active=False` users with a clear "your account is pending approval" message.
- [x] **1.6** Wire Django's built-in password-reset flow (`PasswordResetView`,
  `PasswordResetDoneView`, `PasswordResetConfirmView`, `PasswordResetCompleteView`) under
  `/account/password-reset/...`, with branded templates/emails via the existing email base
  template (`pages/templates/emails/base_email.html`).
- [x] **1.7** Add a "VIP" and "Normal" Django `Group` (seed via a management command similar to
  existing `seed_*` commands). Toggling `Client.is_vip` (or group membership — pick one and use
  it consistently everywhere else in this TODO) is done by admin/accountant only, never by the
  client.
- [x] **1.8** Retire the phone/session dashboard login (`dashboard_login`,
  `CLIENT_PHONE_SESSION_KEY`) in favor of `request.user`/`@login_required`. Keep `dashboard.html`
  URL working but redirect anonymous users to the new `/account/login/`.

## Phase 2 — Client Profile & Enterprise Legal Info

- [x] **2.1** Extend `Client` with the full enterprise legal fields needed for accounting exports
  (cross-check against the uploaded `revenus_par_client` CSV columns): legal form
  (`forme_juridique`), commercial-register number (already `trade_register_number` — rename/alias
  to RC if needed), `nif`, `nis`, `article_imposition`, `rib`, `tva_exempt` (bool), postal code,
  city, website, and a distinct "main contact" name/phone/email (separate from
  `responsible_name`/`responsible_position` if those mean something different).
- [x] **2.2** Build a "My Profile" page in the client space: edit personal/contact fields for
  individuals, and personal + legal/enterprise fields for enterprises, reusing the
  individual/enterprise conditional pattern from `IndividualSubscribeForm`.
- [x] **2.3** Add a validation gate: an enterprise VIP client cannot submit a proforma request
  (Phase 5) until required legal fields are filled in on their profile. Show a clear prompt
  linking to the profile page if incomplete.

## Phase 3 — Role-Based Pricing Visibility

- [x] **3.1** Confirm/extend `Offering` pricing fields to support both billing bases: price
  per day and price per participant (reuse `monthly_fee`/`total_fee` or add
  `price_per_day` / `price_per_participant` — pick whichever fits the existing data best).
- [x] **3.2** In `specialty_detail.html` (offering detail page), show the base price block only
  when `request.user.is_authenticated and request.user.client.is_vip`. Non-VIP and anonymous
  visitors must not see prices at all (not blurred — fully absent from the rendered HTML).
- [x] **3.3** Apply the same visibility rule everywhere else prices could leak: catalog cards,
  cart page, checkout confirmation, order-history/proforma pages.

## Phase 4 — Cart & Wishlist

- [x] **4.1** Create `Cart` (one active cart per `Client`) and `CartItem` (`offering`,
  `participant_count`, `billing_basis` [`per_day`/`per_participant`], `trainer` FK to `Formateur`
  nullable, `notes`) models. `trainer` selection is only ever settable/visible for VIP carts —
  enforce in the form/view layer, not just the template.
- [x] **4.2** Replace the single-offering `subscribe` flow's entry points with "Add to cart"
  buttons on the catalog and specialty-detail pages, supporting multiple formations queued
  before checkout. Keep the old direct-subscribe route working for backward compatibility if
  easy, otherwise redirect it into "add to cart + go to cart".
- [x] **4.3** Build the cart page: list items, edit participant count, remove item, VIP-only
  trainer dropdown per item, subtotal/total shown only to VIP (per Phase 3 rule).
- [x] **4.4** Create `WishlistItem` (`client`, `offering`) model with unique-together
  constraint. Add "Save for later" buttons on catalog/detail pages and a Wishlist page in the
  client space with a "move to cart" action per item.
- [x] **4.5** Add Cart / Wishlist / Profile / My Purchases / Metrics as tabs/sections in the
  client space navigation (`enrollment/templates/enrollment/dashboard.html` or a new tabbed
  layout replacing it).

## Phase 5 — Checkout Flow, Branched by Role

- [x] **5.1 (VIP)** "Request Proforma" action on the cart: confirm billing basis per line item,
  confirm trainer choice per line (already set in cart), optional "bon de commande" upload
  (accept PDF or image, validate extension/mimetype and a sane max size).
- [x] **5.2 (VIP)** Create `ProformaInvoice` model (client, items snapshot with offering, trainer,
  billing basis, quantity, unit price, line total, attached bon-de-commande file, status,
  created_at). Generate printable invoice/receipt pages using dedicated URLs that render HTML
  templates with print-specific CSS (`@media print` rules) — no PDF generation libraries (no
  ReportLab, WeasyPrint, etc.) — with the client's legal info, itemized lines, trainer names, and
  totals.
- [x] **5.3 (Non-VIP)** "Request Quote" action on the cart: creates a `QuoteRequest` (client,
  items with offering + participant_count only — no trainer, no price, no attachment field
  shown or accepted).
- [x] **5.4** On submit of either flow, lock the selected cart items into the created record and
  clear/deactivate the cart (or mark it "converted").

## Phase 6 — Admin / Accountant Tarification

- [x] **6.1** Create an "Accountant" Django `Group` with permissions scoped to
  `ProformaInvoice` and `QuoteRequest` review and to setting custom tariffs — not full admin
  access.
- [x] **6.2** Create `CustomTariff` (or per-line fields directly on `QuoteRequestItem`): admin or
  accountant sets `unit_price` + `billing_basis` per formation line on a given `QuoteRequest`
  (non-VIP path), overriding/defining the price that VIP users would otherwise see as the base
  price.
- [x] **6.3** Build a review interface (Django admin customization is fine) for admin/accountant
  to open a pending `QuoteRequest`, enter the custom tariff per line, and mark it
  `priced`/`approved`.
- [x] **6.4** Once tariffs are set, generate the resulting proforma/invoice document for that
  quote (same printable-HTML-page path as 5.2, no PDF library) and surface it in the client's
  "My Purchases" page.

## Phase 7 — Notification Emails

- [ ] **7.1** Define distinct email templates (extending `emails/base_email.html`) for: VIP
  proforma request → admin; VIP proforma request → accountant; non-VIP quote request → admin;
  non-VIP quote request → accountant; account-approved-with-credentials; password reset
  (branded override of Django's default); quote-priced/ready notification → client.
- [ ] **7.2** Trigger each template from the relevant view (or a `post_save` signal, consistent
  with the existing `enrollment/signals.py` pattern) via `send_branded_mail`, pulling admin/
  accountant recipient addresses from `settings.py`.
- [ ] **7.3** For VIP proforma requests, attach the uploaded bon-de-commande file to (or link it
  securely from) the admin/accountant notification emails.

## Phase 8 — Client Space Overhaul

- [ ] **8.1** Rebuild the authenticated client dashboard with sections: Profile, Active
  Purchases (confirmed enrollments/proformas), Cart, Wishlist, Request History (quotes +
  proformas with status), Metrics.
- [ ] **8.2** Build metrics widgets (e.g., total formations taken, total spent for VIP, pending
  request count, wishlist size) using the already-bundled Chart.js vendor asset
  (`pages/static/vendor/chartjs/chart.umd.min.js`).
- [ ] **8.3** Re-verify the Phase 3 pricing-visibility rule holds across every new dashboard
  section (metrics, purchase history, proforma detail) for non-VIP clients.

## Phase 9 — QA & Polish

- [ ] **9.1** Manual test matrix: register → admin activates → credential email → login →
  password reset; full VIP flow (cart → trainer choice → attachment → proforma PDF → emails);
  full non-VIP flow (cart → quote → accountant sets tariff → client sees priced proforma →
  emails); wishlist → cart transfer.
- [ ] **9.2** Update seed/management commands (alongside existing `seed_enrollment.py`,
  `seed_formateurs.py`, etc.) to create sample VIP and Normal users plus the Accountant group,
  for local dev/demo data.
- [ ] **9.3** Update `README.md`/`CHANGES.md` describing the new registration, cart, wishlist,
  proforma, and tarification flows.
