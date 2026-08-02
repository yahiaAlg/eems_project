"""
Seed placeholder content for the offering's fiche technique: backfills
the `objectives` / `program_outline` / `prerequisites` text fields with
sane defaults (so the auto-generated fiche technique is never empty),
adds one supplementary attachment (a program-outline JPEG), and
demonstrates the "custom upload" fiche technique path on one offering.

No PDF-generation library is used anywhere (no ReportLab, WeasyPrint,
etc.). The fiche technique has two modes on the Offering model:

  - "auto" (the default — nothing to seed): the specialty page links to
    enrollment:fiche_technique, a view that renders a real,
    print-optimized HTML document live from the offering's current data
    every time it's opened (see
    enrollment/documents/fiche_technique_placeholder.html). Editing the
    offering's fields afterwards updates it instantly.
  - "custom": the admin has uploaded a real file (PDF / Word / image)
    instead. To demonstrate this path, one offering is switched to
    "custom" here with a generated JPEG standing in for a
    scanned/exported official sheet — Pillow only, not a PDF.

Real documents should be uploaded by the admin via the Offering change
page; everything generated here is purely demonstrative placeholder
content.

Idempotent: skips offerings that already have attachments / a custom
fiche technique file, and only fills text fields that are blank.

Usage:
    python manage.py seed_fiche_technique     # run after seed_enrollment
"""

import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from enrollment.models import Offering, OfferingAttachment

NAVY = (15, 23, 42)
ACCENT = (245, 158, 11)
WHITE = (255, 255, 255)
MUTED = (100, 116, 139)

DEFAULT_OBJECTIVES = [
    "التمكن من الأسس النظرية والتقنية للتخصص",
    "اكتساب مهارات ميدانية عملية عبر التربصات",
    "الاستعداد لاجتياز امتحان الشهادة الرسمية",
]

DEFAULT_PROGRAM = [
    "الوحدة 1 — المفاهيم الأساسية والتنظيم",
    "الوحدة 2 — التطبيقات التقنية والعملية",
    "الوحدة 3 — السلامة والوقاية في محيط العمل",
    "الوحدة 4 — التربص الميداني والتقييم النهائي",
]

DEFAULT_PREREQUISITES = [
    "السن الأدنى المطلوب حسب مستوى الدخول",
    "شهادة المستوى الدراسي المطلوب (راجع مستوى الدخول أعلاه)",
    "فحص طبي يثبت اللياقة لمزاولة التخصص",
]

# The one offering (by order in the queryset) used to demo "custom fiche
# technique" mode.
CUSTOM_FICHE_DEMO_INDEX = 0


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


def _program_outline_image(offering, size=(1000, 700)):
    """A simple step-diagram JPEG (Pillow image — not a PDF)."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", size, (248, 250, 252))
    draw = ImageDraw.Draw(img)
    w, h = size
    draw.rectangle([0, 0, w, 90], fill=NAVY)
    draw.text((30, 28), f"مخطط برنامج التكوين — {offering.code}", font=_font(26), fill=WHITE)

    steps = ["التأهيل النظري", "التطبيق الميداني", "التربص العملي", "التقييم والشهادة"]
    step_w = (w - 60) / len(steps)
    for i, step in enumerate(steps):
        x = 30 + i * step_w
        draw.rounded_rectangle([x, 160, x + step_w - 20, 260], radius=14, outline=ACCENT, width=4)
        draw.text((x + (step_w - 20) / 2, 210), str(i + 1), font=_font(34), fill=ACCENT, anchor="mm")
        for j, line in enumerate(_wrapped(draw, step, _font(16, bold=False), step_w - 40)):
            draw.text((x + (step_w - 20) / 2, 290 + j * 22), line, font=_font(16, bold=False), fill=NAVY, anchor="mm")
        if i < len(steps) - 1:
            draw.line([x + step_w - 20, 210, x + step_w, 210], fill=ACCENT, width=3)

    draw.text((w / 2, h - 40), "EEMS — مؤسسة التميز للإدارة والسلامة", font=_font(15, bold=False), fill=MUTED, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return ContentFile(buf.getvalue(), name=f"programme-{offering.code}.jpg")


def _custom_fiche_scan_image(offering, size=(1000, 1414)):
    """Simulates an admin-uploaded 'scanned/exported official sheet' image
    — used only for the one demo offering on fiche_technique_mode='custom',
    to show that pathway working end-to-end. Deliberately plainer than the
    live auto-generated fiche technique template."""
    from PIL import Image, ImageDraw, ImageFilter

    img = Image.new("RGB", size, (250, 249, 246))
    draw = ImageDraw.Draw(img)
    w, h = size
    margin = 80

    draw.text((margin, 60), "الفيشة التقنية", font=_font(34), fill=(30, 30, 30))
    draw.text((margin, 104), offering.title, font=_font(18, bold=False), fill=(90, 90, 90))
    draw.text((margin, 132), f"الرمز: {offering.code}", font=_font(15, bold=False), fill=(120, 120, 120))
    draw.line([(margin, 168), (w - margin, 168)], fill=(60, 60, 60), width=2)

    y = 200
    rows = [
        ("مدة التكوين", f"{offering.duration_months} شهرا"),
        ("قدرة الاستيعاب", str(offering.seats_available)),
    ]
    for label, value in rows:
        draw.text((margin, y), f"{label}: {value}", font=_font(17, bold=False), fill=(50, 50, 50))
        y += 30
    y += 20

    draw.text((margin, y), "تعريف التخصص", font=_font(20), fill=(30, 30, 30)); y += 32
    desc = offering.description or "تعريف مفصل للتخصص متوفر قريبا."
    for line in _wrapped(draw, desc, _font(16, bold=False), w - 2 * margin)[:14]:
        draw.text((margin, y), line, font=_font(16, bold=False), fill=(50, 50, 50))
        y += 25

    draw.text((margin, h - 70), "نسخة ممسوحة ضوئيا — رُفعت من طرف الإدارة (محاكاة توضيحية)", font=_font(13, bold=False), fill=(150, 150, 150))

    img = img.filter(ImageFilter.GaussianBlur(0.4))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w, h], outline=(210, 210, 205), width=10)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return ContentFile(buf.getvalue(), name=f"fiche-scan-{offering.code}.jpg")


class Command(BaseCommand):
    help = "Seed fiche technique text defaults + supplementary attachment, and one custom-mode demo."

    @transaction.atomic
    def handle(self, *args, **options):
        offerings = list(Offering.objects.filter(is_active=True).order_by("order")[:6])
        if not offerings:
            self.stdout.write(self.style.WARNING("↷ لا توجد تخصصات — شغّل 'seed_enrollment' أولا."))
            return

        created, filled, custom = 0, 0, 0
        for i, offering in enumerate(offerings):
            text_fields_changed = False
            if not offering.objectives:
                offering.objectives = "\n".join(DEFAULT_OBJECTIVES)
                text_fields_changed = True
            if not offering.program_outline:
                offering.program_outline = "\n".join(DEFAULT_PROGRAM)
                text_fields_changed = True
            if not offering.prerequisites:
                offering.prerequisites = "\n".join(DEFAULT_PREREQUISITES)
                text_fields_changed = True

            # Demo the "custom upload" path on exactly one offering; every
            # other offering stays on the (already-default) "auto" mode,
            # which needs no seeded file at all.
            if i == CUSTOM_FICHE_DEMO_INDEX and not offering.fiche_technique_file:
                offering.fiche_technique_mode = "custom"
                offering.fiche_technique_file.save(
                    f"fiche-scan-{offering.code}.jpg", _custom_fiche_scan_image(offering), save=False,
                )
                text_fields_changed = True
                custom += 1

            if text_fields_changed:
                offering.save(update_fields=[
                    "objectives", "program_outline", "prerequisites",
                    "fiche_technique_mode", "fiche_technique_file",
                ])
                filled += 1

            if not offering.attachments.exists():
                programme = OfferingAttachment(offering=offering, title="مخطط برنامج التكوين", order=0)
                programme.file.save(f"programme-{offering.code}.jpg", _program_outline_image(offering), save=False)
                programme.save()
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"✔ {created} مرفق إضافي، {filled} فيشة تقنية مُحدَّثة ({custom} منها بنمط مخصص تجريبي) عبر {len(offerings)} تخصص"
        ))
