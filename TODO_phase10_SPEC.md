# Functional Spec — Phase 10: Enrollment lifecycle, company rosters, client‑space fixes & pedagogical bridge

**How to use this doc:** hand this file (plus fresh copies of `eems_project.zip` and `isi_pedagogical_webapp.zip`) to a new session and implement section by section, in order — 10.0 is a hard dependency for everything else. Every "ASSUME" tag below marks something I inferred from `db.sqlite3`'s schema or from cross‑references in `accounts/*.py`, because `enrollment/models.py`, `enrollment/views.py`, `enrollment/forms.py`, `enrollment/admin.py` and `enrollment/urls.py` were **not** in the reference zip I was given — only `accounts/` was. **Before touching anything in `enrollment/`, open those five files first and reconcile them against each ASSUME note**; adjust names, don't guess past that point.

Two separate Django projects/DBs throughout: `eems_project` (apps: `accounts`, `enrollment`, `pages` — the last also not in the reference zip) and `isi_pedagogical_webapp` (apps: `formations`, `clients`, `resources`, `core`, `reporting`, `documents`). No shared FK. Every hand‑off is a generated file, not a join.

Confirmed today, from `eems_project/db.sqlite3` schema and code actually in the zip:

```
enrollment_enrollment(id, motivation, status, created_at, updated_at,
                       client_id, handled_by_id, offering_id,
                       participant_id, cancelled_at, confirmed_at)
enrollment_enrollmentnote(id, text, created_at, author_id, enrollment_id)
enrollment_participant(id, full_name, phone, email, birth_date, gender,
                        education_level, position, client_id)
enrollment_client(id, client_type, phone, email, wilaya, address, full_name,
                   birth_date, gender, education_level, company_name,
                   trade_register_number, sector, responsible_name,
                   responsible_position, source, created_at, updated_at,
                   account_status, is_vip, user_id, article_imposition, city,
                   forme_juridique, main_contact_email, main_contact_name,
                   main_contact_phone, nif, nis, postal_code, rib,
                   tva_exempt, website)
enrollment_formationsession(id, name, slug, start_date, registration_deadline,
                             is_active, order)   -- start_date/registration_deadline NULLABLE
enrollment_offering(..., session_id, specialty_id, seats_available, ...)
```

Enrollment status values seen in the admin filter sidebar (image): `under_review` قيد الدراسة, `contacted` تم التواصل, `accepted` مقبول, `confirmed` مؤكد من الطرف المشترك, `waitlist` قائمة انتظار, `rejected` مرفوض, `cancelled` ملغى من الطرف المشترك. **ASSUME** these are the exact internal keys — confirm against `Enrollment.STATUS_CHOICES` in `enrollment/models.py` and use whatever the real constant names are; do not invent new keys.

Confirmed today, from `isi_pedagogical_webapp/formations/models.py` and `utils.py` (both fully present in the zip):

```python
# formations/models.py — Participant (fields we must exactly mirror)
first_name, last_name            # both required by the importer (see below),
                                  # even though the model's own help_text says
                                  # "at least FR or AR" — the importer disagrees
                                  # with the model docstring; importer wins,
                                  # spec accordingly.
gender                            # "M"/"F", optional
first_name_ar, last_name_ar
date_of_birth, place_of_birth, place_of_birth_ar
job_title, employer
phone, email
```

```python
# formations/utils.py::import_participants_from_file — exact contract
HEADER_MAPPING = {
    "prénom": "first_name", "prenom": "first_name",
    "nom": "last_name",
    "prénom ar": "first_name_ar", "prenom ar": "first_name_ar",
    "nom ar": "last_name_ar",
    "date naissance": "date_of_birth", "date de naissance": "date_of_birth",
    "lieu naissance": "place_of_birth", "lieu de naissance": "place_of_birth",
    "lieu naissance ar": "place_of_birth_ar",
    "fonction": "job_title",
    "employeur": "employer",
    "email": "email",
    "téléphone": "phone", "telephone": "phone",
}
# headers matched case-insensitively, .strip()'d — accents matter (both
# accented/unaccented variants are mapped, so either works)
# date formats accepted, tried in order: %d/%m/%Y, %Y-%m-%d, %d-%m-%Y
# row rejected (logged as an error, not imported) if first_name or last_name empty
# row skipped as duplicate if (session, first_name, last_name) already exists
# import stops once session.available_spots == 0; remaining rows counted as "rejected"
```

```python
# formations/views.py::participant_export — exact export header row/order
["Prénom", "Nom", "Prénom AR", "Nom AR", "Date naissance", "Lieu naissance",
 "Lieu naissance AR", "Fonction", "Employeur", "Téléphone", "Email",
 "Présence", "Résultat"]   # last 2 columns are pedagogical-only, we never emit them
```

```python
# formations/models.py — Session (for context on 10.7's bridge; not modified by us)
client = FK(clients.Client, null=False)   # every pedagogical Session belongs to ONE company
trainer = FK(resources.Trainer, null=False)
date_start, date_end
capacity
status: planned / in_progress / completed / archived / cancelled
can_add_participants = status in ("planned", "in_progress") and available_spots > 0
```

```python
# isi_pedagogical_webapp/clients/models.py — Client (natural-key candidates for the bridge)
name (Raison sociale), name_ar, address, city, phone, email, contact_person,
nif, nis, rc, is_active
```

---

## 10.0 — Foundational data model changes (do this first)

### 10.0.1 New model: `enrollment.EnrollmentParticipant`

Add to `enrollment/models.py`:

```python
class EnrollmentParticipant(models.Model):
    """One roster line for an enterprise Enrollment. Field set is a
    deliberate 1:1 mirror of formations.Participant on the pedagogical
    side (see Phase 10 spec) so CSV export round-trips into
    formations.utils.import_participants_from_file with zero mapping.
    """
    GENDER_CHOICES = [("M", "Homme"), ("F", "Femme")]  # match formations.Participant exactly

    enrollment = models.ForeignKey(
        "enrollment.Enrollment", on_delete=models.CASCADE, related_name="roster"
    )

    first_name = models.CharField(max_length=50, verbose_name="الاسم (Prénom)")
    last_name = models.CharField(max_length=50, verbose_name="اللقب (Nom)")
    first_name_ar = models.CharField(max_length=50, blank=True, verbose_name="الاسم بالعربية")
    last_name_ar = models.CharField(max_length=50, blank=True, verbose_name="اللقب بالعربية")

    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, verbose_name="الجنس")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="تاريخ الميلاد")
    place_of_birth = models.CharField(max_length=100, blank=True, verbose_name="مكان الميلاد")
    place_of_birth_ar = models.CharField(max_length=100, blank=True, verbose_name="مكان الميلاد (AR)")

    job_title = models.CharField(max_length=100, blank=True, verbose_name="الوظيفة")
    employer = models.CharField(
        max_length=200, blank=True, verbose_name="جهة العمل",
        help_text="Defaults to the enrollment's Client.company_name at creation time, editable per line."
    )

    phone = models.CharField(max_length=20, blank=True, verbose_name="الهاتف")
    email = models.EmailField(blank=True, verbose_name="البريد الإلكتروني")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مشارك (قائمة المؤسسة)"
        verbose_name_plural = "المشاركون (قائمة المؤسسة)"
        unique_together = ["enrollment", "first_name", "last_name"]
        ordering = ["last_name", "first_name"]

    def clean(self):
        # Importer on the pedagogical side hard-requires both first_name and
        # last_name non-empty — enforce that here too, at save time, not just
        # in the form, so no code path can create an unexportable row.
        if not self.first_name.strip() or not self.last_name.strip():
            raise ValidationError("الاسم واللقب (بالحروف اللاتينية) إلزاميان.")
```

Migration: `enrollment/migrations/00XX_add_enrollmentparticipant.py` (plain `makemigrations`, nothing custom).

### 10.0.2 `Enrollment` — two new fields

```python
# on enrollment.Enrollment
roster_locked_at = models.DateTimeField(null=True, blank=True)
```

`roster_locked_at` is set the moment 10.7's "Planifier la session" action runs; `None` = roster still editable by the client. (No separate boolean — the timestamp doubles as both the flag and an audit trail of *when* it was locked.)

### 10.0.3 `EnrollmentNote` — client visibility flag

```python
# on enrollment.EnrollmentNote
visible_to_client = models.BooleanField(
    default=False,
    verbose_name="مرئية للزبون",
    help_text="عند التفعيل، تظهر هذه الملاحظة في مساحة الزبون. المخفية افتراضيا للحفاظ على خصوصية الملاحظات الداخلية.",
)
```

Default `False` deliberately — this repurposes a field that was staff-only until now, so nothing becomes client-visible by accident on deploy. Staff opt a note in per-note.

`EnrollmentNoteInline` in `enrollment/admin.py` (**ASSUME** that's the inline class name — it's the "ملاحظات المتابعة" formset seen on the enrollment change page) gains `visible_to_client` in its `fields`.

### 10.0.4 Migrations

One migration for all three changes above is fine (`enrollment/migrations/00XX_phase10_models.py`); run `python manage.py makemigrations enrollment && python manage.py migrate`.

---

## 10.1 — Email on enrollment acceptance

### 10.1.1 Detection: signal, not admin hook

Don't hook this into whatever admin action currently sets `status="accepted"` (there may be more than one entry point — direct field edit on the change form *and* the bulk action seen in the enrollment list screenshot). Instead, in `enrollment/signals.py` (create if it doesn't exist yet, or add to it):

```python
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Enrollment

@receiver(pre_save, sender=Enrollment)
def _capture_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._previous_status = Enrollment.objects.only("status").get(pk=instance.pk).status
        except Enrollment.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None

from django.db.models.signals import post_save

@receiver(post_save, sender=Enrollment)
def notify_on_accepted_transition(sender, instance, created, **kwargs):
    if created:
        return
    previous = getattr(instance, "_previous_status", None)
    if previous != "accepted" and instance.status == "accepted":
        from .services import notify_enrollment_accepted
        notify_enrollment_accepted(instance)
```

This fires exactly once per transition **into** `accepted`, regardless of whether it came from the change form or the bulk action, and never re-fires on subsequent saves while status stays `accepted`.

### 10.1.2 Service function

`enrollment/services.py` (mirror the existing `accounts/services.py::activate_client_and_send_credentials` pattern exactly — same "never raises, returns are for admin messages only" contract):

```python
from pages.emails import send_branded_mail

def notify_enrollment_accepted(enrollment):
    client = enrollment.client
    recipient = client.email
    if not recipient:
        return False, f"{client.display_name}: لا يوجد بريد إلكتروني — لم يُرسل إشعار القبول."

    session = enrollment.offering.session  # enrollment_formationsession, may have no start_date yet
    sent = send_branded_mail(
        template="emails/enrollment_accepted.html",
        subject=f"تم قبول تسجيلك — {enrollment.offering.title}",
        to=[recipient],
        context={
            "client_name": client.display_name,
            "offering_title": enrollment.offering.title,
            "session_date": session.start_date,  # None-safe in the template, see below
            "is_enterprise": client.client_type == "enterprise",
            "roster_url": (
                f"{settings.SITE_URL}/mon-espace/inscriptions/{enrollment.pk}/participants/"
                if client.client_type == "enterprise" else None
            ),
            "dashboard_url": f"{settings.SITE_URL}/mon-espace/",
        },
    )
    return (True, f"تم إرسال إشعار القبول إلى {recipient}.") if sent else (
        False, f"{client.display_name}: تعذر إرسال إشعار القبول إلى {recipient}."
    )
```

**ASSUME** `settings.SITE_URL` exists (used elsewhere for absolute links in emails); if not, use `django.contrib.sites` or hardcode the production domain like `EEMSPasswordResetView.extra_email_context["site_url"]` already does (`"https://excellance-ms.dz"`).

### 10.1.3 Template

`pages/templates/emails/enrollment_accepted.html`, extends `emails/base_email.html` (same base every other transactional email uses). Content:

- Headline: "تم قبول تسجيلك في {{ offering_title }}."
- If `session_date`: "تاريخ الدورة: {{ session_date|date:"d/m/Y" }}." — else: "سيتم تحديد تاريخ الدورة قريبا وسنُعلمكم." (never show a raw `None`/empty string).
- If `is_enterprise` and `roster_url`: a button "أضف قائمة المشاركين" → `roster_url`.
- Else (individual): a button "مساحتي" → `dashboard_url`.

### 10.1.4 Tests

- Transition `under_review → accepted` sends exactly one email to `client.email`.
- Transition `accepted → confirmed` (or any other status) sends **no** additional acceptance email.
- Saving an already-`accepted` enrollment again (e.g. editing `motivation`) sends **no** duplicate email.
- `client.email == ""` → function returns `(False, ...)`, no exception raised, nothing crashes the admin save.

---

## 10.2 — Company roster (`EnrollmentParticipant` CRUD + CSV export)

### 10.2.1 Gating

Roster page reachable only when **all** of:
- `request.user` is authenticated and `request.user.client_id == enrollment.client_id` (or staff, read‑only for staff — see 10.2.5).
- `enrollment.client.client_type == "enterprise"`.
- `enrollment.status in ("accepted", "confirmed")`.
- `enrollment.roster_locked_at is None` for **editing**; a locked roster still renders read‑only (so the client can see what was submitted after 10.7 locks it).

Anything else → `404` (don't leak enrollment existence to other users) or a plain "غير متاح" message if it's the *client's own* enrollment but wrong status/type.

### 10.2.2 URL & view

`enrollment/urls.py`, inside the `enrollment` app namespace (**ASSUME** — verify the app_name):

```python
path(
    "mon-espace/inscriptions/<int:enrollment_id>/participants/",
    views.enrollment_roster,
    name="enrollment_roster",
),
path(
    "mon-espace/inscriptions/<int:enrollment_id>/participants/export/",
    views.enrollment_roster_export,
    name="enrollment_roster_export",
),
```

`enrollment/views.py`:

```python
from django.forms import modelformset_factory
from .models import Enrollment, EnrollmentParticipant

EnrollmentParticipantFormSet = modelformset_factory(
    EnrollmentParticipant,
    fields=["first_name", "last_name", "first_name_ar", "last_name_ar",
            "gender", "date_of_birth", "place_of_birth", "place_of_birth_ar",
            "job_title", "employer", "phone", "email"],
    extra=1,
    can_delete=True,
)

@login_required
def enrollment_roster(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment, pk=enrollment_id, client__user=request.user
    )
    if enrollment.client.client_type != "enterprise" or enrollment.status not in ("accepted", "confirmed"):
        raise Http404
    locked = enrollment.roster_locked_at is not None
    queryset = EnrollmentParticipant.objects.filter(enrollment=enrollment)
    max_rows = enrollment.offering.seats_available  # see 10.2.3 note on the seat-math simplification

    if request.method == "POST" and not locked:
        formset = EnrollmentParticipantFormSet(
            request.POST, queryset=queryset, prefix="roster"
        )
        if formset.is_valid():
            instances = formset.save(commit=False)
            for obj in instances:
                obj.enrollment = enrollment
                if not obj.employer:
                    obj.employer = enrollment.client.company_name
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, "تم حفظ قائمة المشاركين.")
            return redirect("enrollment:enrollment_roster", enrollment_id=enrollment.pk)
    else:
        formset = EnrollmentParticipantFormSet(queryset=queryset, prefix="roster")

    return render(request, "enrollment/enrollment_roster.html", {
        "enrollment": enrollment,
        "formset": formset,
        "locked": locked,
        "max_rows": max_rows,
    })
```

### 10.2.3 Seat cap — explicit simplification

Cap the roster at `enrollment.offering.seats_available` client‑side (JS disables "Add row" past that count) **and** server-side (formset `clean()` rejects `> seats_available` non-deleted forms). This does **not** account for seats already consumed by other enrollments on the same offering (individual sign‑ups, or another company's roster) — that's a known gap, flagged here rather than solved: real seat arbitration across all enrollments on one offering is a bigger feature (would need a `select_for_update` reservation step) and is out of scope for Phase 10. If seat contention across enrollments turns out to matter in practice, it's the next phase, not this one.

### 10.2.4 Template & dynamic JS (no page reload per row)

`enrollment/templates/enrollment/enrollment_roster.html` — standard Django management‑form‑driven dynamic formset:

- Render `{{ formset.management_form }}` (hidden `TOTAL_FORMS`/`INITIAL_FORMS`/`MIN_NUM_FORMS`/`MAX_NUM_FORMS` inputs) once.
- Render each bound form as a `<tr>` inside a `<tbody id="roster-rows">`.
- A hidden, JS‑only template row (`<template id="empty-row-template">`) built from `{{ formset.empty_form }}` (Django's `__prefix__` placeholder row), rendered once outside the visible table.
- `enrollment/static/enrollment/js/roster.js`:
  - `addRow()`: clone `#empty-row-template` content, replace every `__prefix__` occurrence in `name=`/`id=`/`for=` attributes with the current `TOTAL_FORMS` value, append to `#roster-rows`, then increment the `TOTAL_FORMS` hidden input. Disable the "Add" button once row count reaches `max_rows` (from a `data-max-rows` attribute on the table, sourced from the `max_rows` context var).
  - `removeRow(rowEl)`: if the row has an `id` field with a value (existing DB row), check its `DELETE` checkbox and hide the row (`display:none`) — **don't** remove it from the DOM, Django's formset needs the `DELETE=on` POST value to actually delete it server-side. If the row has no `id` value (a still-unsaved new row), just remove it from the DOM and decrement `TOTAL_FORMS`.
  - Client‑side validation before submit: `first_name` and `last_name` non‑empty on every non‑deleted row (mirrors the server‑side `clean()` from 10.0.1) — block submit and highlight the offending row instead of round‑tripping to the server for a mistake this cheap to catch.
- Whole thing is one `<form method="post">` around the table — **one** submit, not one request per row. This matches "dynamic JS, no reload per row" *for adding/removing rows*; the save itself is still a single normal POST, which is the correct/simplest reading of "submitted as one POST" from the original ask.
- If `locked`: render the same table with all inputs `disabled`, hide Add/Remove/Save controls, show a banner "تم تأكيد القائمة وجدولة الدورة بتاريخ {{ enrollment.offering.session.start_date|date:"d/m/Y" }} — القائمة مقفلة."

### 10.2.5 Staff-side entry points

- Enrollment change page (staff admin) gets a read‑only inline or a link "عرض قائمة المشاركين (N)" to the same roster view (staff can view but this spec doesn't require staff *editing* rows — that's a `data-fixing` job better done in `/admin/` directly on `EnrollmentParticipant` via a standard `ModelAdmin`, which register anyway for that reason: `admin.site.register(EnrollmentParticipant)` with `list_display = ["enrollment", "first_name", "last_name", "employer"]`, `list_filter = ["enrollment__offering"]`).
- `/mon-espace/` enrollment card (from 10.4) shows a "participants: N" badge and, for enterprise + accepted/confirmed, a button straight into `enrollment_roster`.

### 10.2.6 CSV export

```python
@login_required
def enrollment_roster_export(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id, client__user=request.user)
    if enrollment.client.client_type != "enterprise":
        raise Http404

    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")  # BOM so Excel opens accented headers correctly
    response["Content-Disposition"] = (
        f'attachment; filename="participants_{enrollment.offering.code}_{enrollment.pk}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow([
        "Prénom", "Nom", "Prénom AR", "Nom AR", "Date naissance",
        "Lieu naissance", "Lieu naissance AR", "Fonction", "Employeur",
        "Téléphone", "Email",
    ])  # exact header row/order copied from formations/views.py::participant_export,
        # minus the two pedagogical-only columns (Présence, Résultat) we have no data for
    for p in enrollment.roster.all().order_by("last_name", "first_name"):
        writer.writerow([
            p.first_name, p.last_name, p.first_name_ar, p.last_name_ar,
            p.date_of_birth.strftime("%d/%m/%Y") if p.date_of_birth else "",
            p.place_of_birth, p.place_of_birth_ar, p.job_title, p.employer,
            p.phone, p.email,
        ])
    return response
```

`filename` uses `%d/%m/%Y` to match one of the three formats `import_participants_from_file` accepts — verified above, don't change this format without re‑checking `utils.py`.

### 10.2.7 Tests

- Non‑enterprise client → `404` on both roster URLs.
- Enterprise client, `status="under_review"` → `404`.
- Enterprise client, `status="accepted"`, 0 rows → page renders, "Add row" works, save with 3 valid rows creates 3 `EnrollmentParticipant`.
- Submitting a row with empty `last_name` → formset invalid, no partial save, error shown on that row.
- Adding a 21st row when `seats_available == 20` → server rejects (client‑side already should have disabled it, but test the server path directly via a raw POST bypassing JS).
- `roster_locked_at` set → GET renders disabled fields; POST is ignored/redirected without changes.
- Exported CSV re‑imported into a fresh pedagogical‑app `Session` via `import_participants_from_file` → `result["imported"] == roster count`, `result["errors"] == []`.

---

## 10.3 — Quick‑register CTA with prefill

### 10.3.1 Where

Offering/specialty detail template (the page that hosts the `.btn-enroll` → `enrollment:subscribe` link mentioned in `CHANGES.md` §1 — **ASSUME** template path `enrollment/templates/enrollment/_fiche_technique.html` or similar, confirm actual name).

```django
{% if request.user.is_authenticated and request.user.client.account_status == "active" %}
  <a href="{% url 'enrollment:subscribe' offering.pk %}?prefill=1" class="btn btn-quick-register">
    التسجيل السريع
  </a>
{% endif %}
```

Anonymous/inactive‑account visitors see only the existing plain `.btn-enroll` — unchanged.

### 10.3.2 View change

**ASSUME** the existing subscribe view is `enrollment/views.py::subscribe(request, offering_pk)` using `enrollment.forms.IndividualSubscribeForm` (name referenced in `accounts/forms.py`'s docstring) for individuals. Add, without touching the POST branch at all:

```python
def subscribe(request, offering_pk):
    ...
    initial = {}
    if request.method == "GET" and request.GET.get("prefill") and request.user.is_authenticated:
        client = getattr(request.user, "client", None)
        if client:
            initial = {
                "full_name": client.full_name,
                "phone": client.phone,
                "email": client.email,
                "wilaya": client.wilaya,
                "address": client.address,
                "birth_date": client.birth_date,
                "gender": client.gender,
                "education_level": client.education_level,
                # enterprise path, if the offering's subscribe form branches on client_type:
                "company_name": client.company_name,
                "responsible_name": client.responsible_name,
                "responsible_position": client.responsible_position,
            }
    form = IndividualSubscribeForm(initial=initial)  # or whatever the real form class/branching is
    ...
```

**Before implementing:** open `enrollment/forms.py` and confirm the exact field names on the subscribe form(s) — they are *not* guaranteed to be named identically to `Client`'s fields (the earlier `RegistrationForm` docstring in `accounts/forms.py` explicitly says the subscribe form "also carries enrollment‑specific fields like `motivation`/`employment_status` that don't belong on the account" — meaning the subscribe form is a **different, richer** form than `RegistrationForm`, and only the fields that genuinely overlap with `Client` should be prefilled; leave `motivation`, `employment_status`, "كيف سمعت عنا", "الوقت المفضل للاتصال" etc. blank for the client to fill fresh each time, since those are per‑registration, not account‑level facts).

### 10.3.3 Tests

- Anonymous user on an offering page → no quick‑register button, form is blank as today.
- Authenticated client, `account_status="active"`, clicks quick‑register → identity fields pre‑populated, all still editable, submitting works exactly as the manual path (same view, same validation).
- Authenticated client with `account_status="pending"` → no quick‑register button (not yet activated, per 10.3.1's condition).

---

## 10.4 — Fix: accepted enrollment not reflected in `/mon-espace/`

### 10.4.1 Root cause to confirm first

Before writing new code: open the current dashboard view (**ASSUME** `enrollment/views.py::dashboard` or similar, serving `/mon-espace/`) and check whether it queries `Enrollment` **at all**. Given the symptom (accepted enrollment shows nowhere, stats read 0 even though `QuoteRequest`/`ProformaInvoice` stats for the same client work fine), the likely cause is that the dashboard's `context` was built before `Enrollment` existed as a client‑visible concept and only ever wired up `Cart`/`WishlistItem`/`QuoteRequest`/`ProformaInvoice` (all added later, in Phases 4–6 per `CHANGES.md`) — `Enrollment` itself predates all of that (`CHANGES.md` §2–3) and was seemingly never folded back in when the dashboard was rebuilt in Phase 8. Confirm this by grepping the dashboard view for `Enrollment` — if it's genuinely absent, this is an addition, not a bugfix in the narrow sense; if it's present but filtered wrong (e.g. `status="confirmed"` only), it's a filter fix. **Write the fix to match whichever is actually true** rather than assuming.

### 10.4.2 What to add

In the dashboard view, add:

```python
enrollments = Enrollment.objects.filter(client=client).select_related("offering").order_by("-updated_at")
context["enrollments"] = enrollments
context["enrollment_counts"] = {
    status_key: enrollments.filter(status=status_key).count()
    for status_key, _label in Enrollment.STATUS_CHOICES  # ASSUME this is the real attr name
}
```

Deliberately **not** collapsing statuses into an invented "confirmed bucket" — render each real status with its own count and its own Arabic label (reuse `Enrollment.STATUS_CHOICES`/`get_status_display()`, the same source of truth the admin filter sidebar already uses, so the two never drift apart). If the existing "مجموع التسجيلات / تسجيلات مؤكدة / قيد الانتظار" stat cards are kept, map them literally: "مجموع" = `enrollments.count()`, "مؤكدة" = `enrollment_counts["confirmed"]` (not `accepted` — those are different, real statuses; don't conflate), "قيد الانتظار" = `enrollment_counts["waitlist"]` + `enrollment_counts["under_review"]` if the UI wants those merged, but say so explicitly in the template rather than in a silently-merged queryset.

### 10.4.3 Template

New block on the dashboard ("نظرة عامة" tab and/or a dedicated "تسجيلاتي" tab, matching the existing tab bar seen in the `/mon-espace/` screenshot — "سلتي / مشترياتي / قائمة رغباتي / ملفي الشخصي / إحصائياتي"): add "تسجيلاتي" as a new tab. Each row: offering title, `{{ enrollment.get_status_display }}`, `{{ enrollment.updated_at|date:"d/m/Y" }}`, and (10.2/10.5 hooks) a participants‑count badge + "أضف المشاركين" button when applicable, and a notes toggle (10.5).

### 10.4.4 Tests

- Fixture: client with one `Enrollment(status="accepted")`. Load `/mon-espace/` → enrollment appears in the new tab/list, with status "مقبول", **without** any reseed or relogin.
- Change status to `"confirmed"` via admin, reload same page (same session, no logout) → status text updates on next request (no caching issue).
- Stats card counts match a manual `Enrollment.objects.filter(...).count()` for the same client in a Django shell — write this as an actual assertion, not eyeballed.

---

## 10.5 — Surface staff notes to the client

Depends on 10.0.3 (`visible_to_client` field).

### 10.5.1 Query

In the same dashboard context (10.4) or lazily per‑enrollment via a template‑tag/`{% for %}`:

```python
enrollment.roster... # unrelated
visible_notes = enrollment.notes.filter(visible_to_client=True).order_by("created_at")  # ASSUME related_name "notes"
```

### 10.5.2 Template

Under each enrollment row (10.4.3), a collapsible "ملاحظات" section listing `visible_notes`: `{{ note.text }}` + `{{ note.created_at|date:"d/m/Y H:i" }}`. **No author name** shown client‑side (staff identity stays internal) unless a later decision reverses this — flagged here as the default, change only on explicit instruction.

### 10.5.3 Admin

`EnrollmentNoteInline.fields` (or equivalent) gains the `visible_to_client` checkbox, defaulting unchecked — staff must actively opt a note in. Add a short `help_text` in the admin (already drafted in 10.0.3) so this isn't a silent trap for staff used to the old all‑internal behaviour.

### 10.5.4 Tests

- Note created with `visible_to_client=False` (the default) → absent from `/mon-espace/`.
- Note created with `visible_to_client=True` → appears, in creation order, with no author name in the client‑facing markup.

---

## 10.6 — Login redirect to `/mon-espace/` + catalogue quick‑access

### 10.6.1 Redirect

In `eems_project/settings.py`:

```python
LOGIN_REDIRECT_URL = "enrollment:dashboard"  # ASSUME url name — confirm against enrollment/urls.py
```

`EEMSLoginView` (`accounts/views.py`) already sets `redirect_authenticated_user = True` and doesn't override `get_success_url`, so it already falls through to `LOGIN_REDIRECT_URL` by default **once that setting points at the dashboard** — this is a one‑line settings change, not a view change, *provided* nothing else currently overrides it (search the settings file and `EEMSLoginView` for any existing `LOGIN_REDIRECT_URL`/`success_url` first; if one already points elsewhere, that's the actual bug to fix here). `?next=` support is untouched — Django's `LoginView` always honours `next` over `LOGIN_REDIRECT_URL` when present, so deep links keep working.

### 10.6.2 Catalogue CTA

On the dashboard template ("نظرة عامة" tab, top‑level, not buried in a sub‑tab):

```django
<a href="{% url 'pages:catalogue' %}" class="btn btn-catalogue">تصفح الكتالوج</a>
```

**ASSUME** `pages:catalogue` — confirm against the nav bar's "تصنيف التكوينات" link target in `pages/templates/pages/partials/_navbar.html` (mentioned as an existing file in `CHANGES.md`'s "Files touched" list) and use whatever URL name that actually resolves to.

### 10.6.3 Tests

- Login with no `?next=` → lands on `/mon-espace/`.
- Login with `?next=/formations/catalogue-eems/BTP0720/inscription/` → lands there, not on the dashboard (next still wins).
- Dashboard page contains a working link to the catalogue landing page.

---

## 10.7 — Schedule the session with a specific date

Depends on 10.0.2 (`roster_locked_at`) and, practically, on 10.2 having at least some rows (though not strictly enforced — see below).

### 10.7.1 Staff action

New staff‑only view (or a Django admin action on `EnrollmentAdmin`, either is fine — admin action is less code and matches the existing "bulk set status" action already in that list view):

```python
@admin.action(description="📅 جدولة الجلسة (تحديد تاريخ الدورة)")
def schedule_session(self, request, queryset):
    for enrollment in queryset:
        if enrollment.status not in ("accepted", "confirmed"):
            self.message_user(request, f"{enrollment}: يجب أن يكون التسجيل مقبولا أولا.", level=messages.WARNING)
            continue
        # date itself comes from a small intermediate form/page, not the bulk action directly —
        # Django admin actions can't natively prompt for extra input without a custom
        # intermediate template (same pattern Django's own docs use for "export as CSV
        # with a date range"); build enrollment/templates/admin/schedule_session_intermediate.html
        ...
```

Simplify by making this a dedicated non‑bulk view instead, reachable from a button on the Enrollment change page (`enrollment/admin.py::EnrollmentAdmin` → override `change_form_template`, or simpler: a plain Django view at `/admin/enrollment/enrollment/<id>/schedule/` linked from the change page) that takes one date input and calls a service function:

```python
# enrollment/services.py
def schedule_session(enrollment, start_date, registration_deadline=None):
    session = enrollment.offering.session
    session.start_date = start_date
    if registration_deadline:
        session.registration_deadline = registration_deadline
    session.save(update_fields=["start_date", "registration_deadline"])

    enrollment.roster_locked_at = timezone.now()
    enrollment.save(update_fields=["roster_locked_at"])

    if enrollment.client.email:
        send_branded_mail(
            template="emails/session_scheduled.html",
            subject=f"تم تحديد تاريخ الدورة — {enrollment.offering.title}",
            to=[enrollment.client.email],
            context={
                "client_name": enrollment.client.display_name,
                "offering_title": enrollment.offering.title,
                "session_date": start_date,
            },
        )
```

Setting `session.start_date` this way affects the **`FormationSession` shared by every enrollment on that offering** (confirmed above: `Offering.session` is a single FK, many `Enrollment`s can point at the same `Offering`) — so scheduling from one enrollment's page sets the date for everyone on that offering. That's very likely the intended behaviour (one cohort, one date), but call it out explicitly in the staff‑facing UI ("سيُطبَّق هذا التاريخ على كل التسجيلات في هذه الدورة") so it isn't a surprise the first time two companies share an offering.

`enrollment.roster_locked_at` is set **on this specific enrollment only** (roster locking is per‑company, per 10.0.2/10.2.1) — scheduling the session locks *that* enrollment's own roster; it does not touch other enrollments' `roster_locked_at` on the same offering (each company's admin locks independently, only the shared date is, well, shared).

### 10.7.2 Not enforcing "roster must be non‑empty first"

Deliberately **not** blocking scheduling on an empty roster — a company might get its session date confirmed before it has finalized names (matches "participants optional" from 10.2). Staff can schedule with 0 rows; the roster page (10.2.4) simply becomes read‑only at that point, same as with rows in it, showing "القائمة مقفلة" with 0 rows listed. If this turns out to be the wrong call in practice, gate it behind `enrollment.roster.exists()` — flagged as an easy toggle, not a structural decision.

### 10.7.3 Bridge artifact for the pedagogical app hand‑off

No automated `formations.Session` creation (deliberately — `trainer`, `room`/`location_type`, `capacity`, `base_price`/`price_mode` all live only in `isi_pedagogical_webapp` and have no EEMS‑side equivalent to source them from; auto‑creating a half‑filled `Session` would just move data‑entry work around, not remove it). Instead, alongside the CSV export from 10.2.6, generate one small companion text file, `session_brief_<enrollment_id>.txt`, for the staff member creating the `Session` in the pedagogical app by hand:

```
Formation (EEMS offering code): {{ enrollment.offering.code }} — {{ enrollment.offering.title }}
Client (raison sociale):        {{ enrollment.client.company_name }}
NIF / NIS:                      {{ enrollment.client.nif }} / {{ enrollment.client.nis }}
Contact:                        {{ enrollment.client.responsible_name }} ({{ enrollment.client.responsible_position }})
                                 {{ enrollment.client.phone }} — {{ enrollment.client.email }}
Scheduled date:                 {{ session.start_date|date:"d/m/Y" }}
Participants attached:          {{ enrollment.roster.count }} (see participants_{offering.code}_{enrollment.pk}.csv)
```

This gives the pedagogical‑app operator everything needed to either match an existing `clients.Client` (by `nif`/`nis`/`name`) or create a new one, then create the `Session` and use the *existing* "Importer" screen (already built, seen in the screenshots) for the CSV. Bundle both files behind one "Télécharger le dossier de session" button (zip the two, or offer two separate download links — either is fine).

### 10.7.4 Tests

- Scheduling sets `FormationSession.start_date` correctly and locks the calling enrollment's roster (`roster_locked_at` not null).
- Scheduling a second enrollment on the *same* offering does not re‑lock the first enrollment's roster, but does see the same updated `session.start_date` (shared FK).
- `session_scheduled` email sent once, to the enrolling client only (not to other companies sharing the offering).
- Roster page for a locked enrollment renders read‑only, no 500 on 0 rows.

---

## Files touched (expected — for the `CHANGES.md` entry once this ships)

**Added:**
`enrollment/migrations/00XX_phase10_models.py`,
`enrollment/services.py` (or additions if it already exists),
`enrollment/templates/enrollment/enrollment_roster.html`,
`enrollment/static/enrollment/js/roster.js`,
`enrollment/static/enrollment/css/roster.css` (optional, styling only),
`pages/templates/emails/enrollment_accepted.html`,
`pages/templates/emails/session_scheduled.html`,
`docs/TESTING_PHASE10.md` (manual test matrix, mirroring `docs/TESTING_ACCOUNTS_AND_CHECKOUT.md`'s existing format).

**Modified:**
`enrollment/models.py` (+`EnrollmentParticipant`, +`Enrollment.roster_locked_at`, +`EnrollmentNote.visible_to_client`),
`enrollment/admin.py` (+`EnrollmentParticipant` registration, +`visible_to_client` on the note inline, +schedule‑session entry point),
`enrollment/views.py` (+`enrollment_roster`, +`enrollment_roster_export`, dashboard view gets `Enrollment`/notes context, `subscribe` gets `initial=` prefill),
`enrollment/urls.py` (+2 roster URLs, +1 schedule‑session URL),
`enrollment/signals.py` (+acceptance‑email signal pair),
`accounts/views.py` (only if `LOGIN_REDIRECT_URL` turns out to be overridden there instead of in settings),
`eems_project/settings.py` (`LOGIN_REDIRECT_URL`),
offering/specialty detail template (+quick‑register CTA),
dashboard template (+"تسجيلاتي" tab, +catalogue CTA, +notes, +roster badge/button).

**Not touched at all (by design):** anything under `isi_pedagogical_webapp/` — the hand‑off stays file‑based (10.2.6 CSV + 10.7.3 brief), no code changes on that side for this phase.
