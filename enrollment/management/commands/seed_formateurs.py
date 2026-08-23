"""
Give the real formateurs (imported from docs/Trainer-2026-08-23.csv by
seed_enrollment) a tasteful generated initials-avatar photo (brand-colored,
no external assets), and assign them round-robin to a handful of existing
active Offerings so the catalogue/detail/profile pages have something real
to show.

This command deliberately does NOT invent trainer names, titles, bios, or
years of experience. The Trainer CSV export only contains a name and an
employment_type/is_active flag — no specialty, no biography, no years of
experience — so those fields are intentionally left blank here for an
admin to fill in later from real records, rather than fabricated.

Idempotent: safe to run multiple times.

Usage:
    python manage.py seed_formateurs     # run after seed_enrollment
"""

import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from enrollment.models import Formateur, Offering

NAVY = (15, 23, 42)
ACCENT = (245, 158, 11)


def _initials(name):
    parts = [p for p in name.replace("أ.", "").strip().split() if p]
    return "".join(p[0] for p in parts[:2]).upper() if parts else "EE"


def _avatar_photo(name, size=(400, 400)):
    """Generate a simple, tasteful brand-colored initials avatar."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", size, NAVY)
    draw = ImageDraw.Draw(img)
    w, h = size
    # Soft accent ring
    margin = 18
    draw.ellipse([margin, margin, w - margin, h - margin], outline=ACCENT, width=6)

    initials = _initials(name)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 140
        )
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), initials, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((w - tw) / 2 - bbox[0], (h - th) / 2 - bbox[1]),
        initials,
        fill=(255, 255, 255),
        font=font,
    )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return ContentFile(buf.getvalue(), name=f"formateur-{initials}.jpg")


class Command(BaseCommand):
    help = (
        "Give real (Trainer-CSV-imported) formateurs a placeholder avatar "
        "photo and assign them round-robin to existing active offerings."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        formateurs = list(
            Formateur.objects.filter(is_active=True).order_by("full_name")
        )
        if not formateurs:
            self.stdout.write(
                self.style.WARNING(
                    "↷ لا يوجد مكوّنون — شغّل 'python manage.py seed_enrollment' أولا "
                    "لاستيراد المكوّنين الحقيقيين من ملف Trainer CSV."
                )
            )
            return

        avatars = 0
        for f in formateurs:
            if not f.photo:
                f.photo.save(f"{f.slug}.jpg", _avatar_photo(f.full_name), save=False)
                f.save(update_fields=["photo"])
                avatars += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"✔ {avatars} صورة رمزية جديدة عبر {len(formateurs)} مكوّن حقيقي (Trainer CSV)"
            )
        )

        offerings = list(Offering.objects.filter(is_active=True).order_by("order"))
        if not offerings:
            self.stdout.write(
                self.style.WARNING(
                    "↷ لا توجد تخصصات — شغّل 'python manage.py seed_enrollment' أولا لربط المكوّنين بتكوينات."
                )
            )
            return

        assigned = 0
        for i, offering in enumerate(offerings):
            if offering.formateur_id:
                continue  # don't override a manually-assigned formateur
            offering.formateur = formateurs[i % len(formateurs)]
            offering.save(update_fields=["formateur"])
            assigned += 1
        self.stdout.write(
            self.style.SUCCESS(f"✔ assigned formateurs to {assigned} offering(s)")
        )
