"""
Seed default/placeholder content for the formateur "Udemy-style" profile
page: certificates (JPEG images — real files, not PDFs), a career
timeline, and a CV.

No PDF-generation library is used anywhere (no ReportLab, WeasyPrint,
etc.). The CV itself has two modes on the Formateur model:

  - "auto" (the default — nothing to seed): the profile page links to
    enrollment:formateur_cv, a view that renders a real, print-optimized
    HTML document live from the formateur's current data every time it's
    opened (see enrollment/documents/cv_placeholder.html). Editing the
    bio/career afterwards updates it instantly, no regeneration needed.
  - "custom": the admin has uploaded a real file (PDF / Word / image)
    instead. To demonstrate this path in the demo data, one formateur is
    switched to "custom" here with a generated JPEG standing in for a
    scanned/exported CV — Pillow only, not a PDF.

Certificates are always real JPEG images (Pillow) — a certificate is
naturally a "photo of a paper document" in practice, so there's no
HTML-vs-file duality for them, just the file itself.

Real documents should be uploaded by the admin via the Formateur change
page; everything generated here is purely demonstrative placeholder
content.

Idempotent: skips a formateur's cv_file / certificates / career_entries
individually if they already have content.

Usage:
    python manage.py seed_formateur_profiles     # run after seed_formateurs
"""

import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from enrollment.models import Formateur, FormateurCareerEntry, FormateurCertificate

NAVY = (15, 23, 42)
ACCENT = (245, 158, 11)
WHITE = (255, 255, 255)
MUTED = (100, 116, 139)
PAPER = (248, 250, 252)

CAREER_TEMPLATES = [
    ("متربص / مساعد ميداني", 6),
    ("مسؤول تقني", 3),
    ("مكوّن معتمد لدى مؤسسة التميز EEMS", 0),
]

CERT_TITLES = [
    ("شهادة تكوين المكوّنين", "المعهد الوطني للتكوين المهني"),
    ("اعتماد مهني في مجال الاختصاص", "EEMS — مؤسسة التميز للإدارة والسلامة"),
]

# The one formateur (by order in the queryset) used to demo "custom CV" mode.
CUSTOM_CV_DEMO_INDEX = 0


def _font(size, bold=True):
    from PIL import ImageFont
    path = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _wrapped(draw, text, font, max_width):
    """Greedy word-wrap using actual glyph widths."""
    words = text.split()
    lines, current = [], ""
    for w in words:
        trial = f"{current} {w}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def _seal(draw, cx, cy, r, label="EEMS"):
    """A small ornamental circular seal/ribbon, drawn with plain shapes."""
    import math
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACCENT, width=4)
    draw.ellipse([cx - r + 9, cy - r + 9, cx + r - 9, cy + r - 9], outline=NAVY, width=2)
    draw.text((cx, cy - 6), label, font=_font(15), fill=NAVY, anchor="mm")
    draw.text((cx, cy + 12), "★", font=_font(13), fill=ACCENT, anchor="mm")
    # ribbon tails
    for dx in (-1, 1):
        draw.polygon([
            (cx + dx * (r - 14), cy + r - 10),
            (cx + dx * (r - 2), cy + r + 26),
            (cx + dx * (r - 22), cy + r + 18),
        ], fill=ACCENT)


def _certificate_image(title, issuer, recipient, size=(1200, 850)):
    """An ornate landscape certificate placeholder image (JPEG — not a PDF)."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", size, WHITE)
    draw = ImageDraw.Draw(img)
    w, h = size

    # Outer + inner decorative frame
    draw.rectangle([0, 0, w, h], fill=WHITE)
    draw.rectangle([26, 26, w - 26, h - 26], outline=ACCENT, width=7)
    draw.rectangle([42, 42, w - 42, h - 42], outline=NAVY, width=2)
    for corner in [(50, 50), (w - 50, 50), (50, h - 50), (w - 50, h - 50)]:
        draw.ellipse([corner[0] - 5, corner[1] - 5, corner[0] + 5, corner[1] + 5], fill=ACCENT)

    draw.text((w / 2, 128), "EEMS", font=_font(24), fill=ACCENT, anchor="mm")
    draw.text((w / 2, 160), "مؤسسة التميز للإدارة والسلامة", font=_font(16, bold=False), fill=MUTED, anchor="mm")

    draw.line([(w / 2 - 60, 195), (w / 2 + 60, 195)], fill=ACCENT, width=3)
    draw.text((w / 2, 250), "شهادة", font=_font(56), fill=NAVY, anchor="mm")
    y = 320
    for line in _wrapped(draw, title, _font(30), w - 280):
        draw.text((w / 2, y), line, font=_font(30), fill=NAVY, anchor="mm")
        y += 42

    draw.text((w / 2, y + 40), "تشهد بأن", font=_font(16, bold=False), fill=MUTED, anchor="mm")
    draw.text((w / 2, y + 82), recipient, font=_font(34), fill=ACCENT, anchor="mm")
    draw.line([(w / 2 - 180, y + 108), (w / 2 + 180, y + 108)], fill=(226, 232, 240), width=2)
    draw.text((w / 2, y + 140), "قد حصل/ت على هذا الاعتماد ضمن مسارها المهني والتكويني", font=_font(16, bold=False), fill=(51, 65, 85), anchor="mm")
    draw.text((w / 2, y + 172), issuer, font=_font(15, bold=False), fill=MUTED, anchor="mm")

    # signature line + seal
    draw.line([(90, h - 110), (330, h - 110)], fill=(148, 163, 184), width=2)
    draw.text((210, h - 90), "التوقيع", font=_font(14, bold=False), fill=MUTED, anchor="mm")
    _seal(draw, w - 190, h - 140, 58)

    draw.text((90, h - 60), "وثيقة نموذجية تلقائية", font=_font(12, bold=False), fill=(148, 163, 184), anchor="lm")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return ContentFile(buf.getvalue(), name="certificate.jpg")


def _custom_cv_scan_image(formateur, size=(1000, 1414)):
    """Simulates an admin-uploaded 'scanned/exported CV' image — used only
    for the one demo formateur on cv_mode='custom', to show that pathway
    working end-to-end. Deliberately styled differently from the live
    auto-generated CV template (plainer, more 'photocopied' look)."""
    from PIL import Image, ImageDraw, ImageFilter

    img = Image.new("RGB", size, (250, 249, 246))
    draw = ImageDraw.Draw(img)
    w, h = size
    margin = 80

    draw.text((margin, 70), formateur.full_name, font=_font(38), fill=(30, 30, 30))
    draw.text((margin, 118), formateur.title or "مكوّن مهني", font=_font(19, bold=False), fill=(90, 90, 90))
    draw.line([(margin, 158), (w - margin, 158)], fill=(60, 60, 60), width=2)

    y = 190
    draw.text((margin, y), "نبذة", font=_font(22), fill=(30, 30, 30)); y += 34
    bio = formateur.bio or "معلومات إضافية غير متوفرة."
    for line in _wrapped(draw, bio, _font(17, bold=False), w - 2 * margin)[:8]:
        draw.text((margin, y), line, font=_font(17, bold=False), fill=(50, 50, 50))
        y += 26
    y += 20

    draw.text((margin, y), "معلومات", font=_font(22), fill=(30, 30, 30)); y += 34
    for label, value in [
        ("سنوات الخبرة", f"{formateur.years_experience or '—'} سنة"),
        ("البريد الإلكتروني", formateur.email or "—"),
    ]:
        draw.text((margin, y), f"{label}: {value}", font=_font(17, bold=False), fill=(50, 50, 50))
        y += 30

    draw.text((margin, h - 70), "نسخة ممسوحة ضوئيا — رُفعت من طرف الإدارة (محاكاة توضيحية)", font=_font(13, bold=False), fill=(150, 150, 150))

    # subtle "scan" texture: light blur + slight noise-free vignette via border shading
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w, h], outline=(210, 210, 205), width=10)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return ContentFile(buf.getvalue(), name=f"cv-scan-{formateur.slug}.jpg")


class Command(BaseCommand):
    help = "Seed placeholder certificates / career timeline for formateurs, and one custom-mode CV demo."

    @transaction.atomic
    def handle(self, *args, **options):
        formateurs = list(Formateur.objects.all())
        if not formateurs:
            self.stdout.write(self.style.WARNING(
                "↷ لا يوجد مكوّنون — شغّل 'python manage.py seed_formateurs' أولا."
            ))
            return

        cvs, certs, careers = 0, 0, 0

        for i, f in enumerate(formateurs):
            # --- CV: demo the "custom upload" path on exactly one formateur;
            #     everyone else stays on the (already-default) "auto" mode,
            #     which needs no seeded file at all. ---
            if i == CUSTOM_CV_DEMO_INDEX and not f.cv_file:
                f.cv_mode = "custom"
                f.cv_file.save(f"cv-scan-{f.slug}.jpg", _custom_cv_scan_image(f), save=False)
                f.save(update_fields=["cv_mode", "cv_file"])
                cvs += 1

            # --- Certificates (always real JPEG images) ---
            if not f.certificates.exists():
                for i2, (title, issuer) in enumerate(CERT_TITLES):
                    cert = FormateurCertificate(formateur=f, title=title, issuer=issuer, order=i2)
                    cert.file.save(
                        f"cert-{f.slug}-{i2}.jpg",
                        _certificate_image(title, issuer, f.full_name),
                        save=False,
                    )
                    cert.save()
                    certs += 1

            # --- Career timeline ---
            if not f.career_entries.exists():
                base_year = 2026 - (f.years_experience or 8)
                cursor = base_year
                for i3, (role, span) in enumerate(CAREER_TEMPLATES):
                    start = cursor
                    end = None if span == 0 else min(cursor + span, 2026)
                    FormateurCareerEntry.objects.create(
                        formateur=f,
                        role_title=role,
                        organization="مؤسسة التميز للإدارة والسلامة (EEMS)" if span == 0 else "",
                        start_year=start,
                        end_year=end,
                        description="",
                        order=i3,
                    )
                    cursor = (end or 2026)
                careers += 1

        self.stdout.write(self.style.SUCCESS(
            f"✔ {cvs} CV مخصص (تجريبي)، {certs} شهادة، {careers} مسار مهني — عبر {len(formateurs)} مكوّن "
            f"(الباقي على النمط التلقائي بدون أي ملف)"
        ))
