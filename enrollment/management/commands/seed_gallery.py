"""
Seed a handful of secondary gallery images (used by the lightbox slider
on the specialty detail page) for a few sample offerings. Purely
demonstrative — real photos should be uploaded via the admin gallery
inline on each Offering.

Idempotent: safe to run multiple times (skips offerings that already
have gallery images).

Usage:
    python manage.py seed_gallery
"""

import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from enrollment.models import Offering, OfferingImage

NAVY = (15, 23, 42)
NAVY_MID = (30, 41, 59)
ACCENT = (245, 158, 11)
PALETTE = [(16, 185, 129), (59, 130, 246), (245, 158, 11), (168, 85, 247)]

CAPTIONS = ["أثناء التكوين", "ورشة تطبيقية", "قاعة التدريب", "تربص ميداني"]


def _gallery_photo(seed, caption, size=(900, 600)):
    from PIL import Image, ImageDraw, ImageFont

    color = PALETTE[seed % len(PALETTE)]
    img = Image.new("RGB", size, NAVY)
    draw = ImageDraw.Draw(img)
    w, h = size

    # Diagonal duotone stripes for a distinct, non-photographic placeholder look
    stripe_w = 70
    for x in range(-h, w, stripe_w * 2):
        draw.polygon([(x, 0), (x + stripe_w, 0), (x + stripe_w - h, h), (x - h, h)], fill=NAVY_MID)

    # Soft color glow corner
    glow = Image.new("L", size, 0)
    gdraw = ImageDraw.Draw(glow)
    gx, gy, gr = int(w * 0.18), int(h * 0.8), int(w * 0.34)
    gdraw.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=110)
    from PIL import ImageFilter
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    color_layer = Image.new("RGB", size, color)
    img = Image.composite(color_layer, img, glow)
    draw = ImageDraw.Draw(img)

    # Centered icon-like frame mark
    cx, cy = w // 2, int(h * 0.42)
    r = 60
    draw.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=16, outline=(255, 255, 255), width=4)
    draw.rounded_rectangle([cx - r + 12, cy - r + 12, cx + r - 12, cy + r - 12], radius=10, outline=color, width=3)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), caption, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw / 2, cy + r + 30), caption, fill=(255, 255, 255), font=font)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return ContentFile(buf.getvalue(), name=f"gallery-{seed}.jpg")


class Command(BaseCommand):
    help = "Seed demo gallery (secondary) images for a few sample offerings."

    @transaction.atomic
    def handle(self, *args, **options):
        offerings = Offering.objects.filter(is_active=True).order_by("order")[:6]
        if not offerings:
            self.stdout.write(self.style.WARNING("↷ لا توجد تخصصات — شغّل 'seed_enrollment' أولا."))
            return

        created = 0
        for offering in offerings:
            if offering.gallery_images.exists():
                continue
            for i, caption in enumerate(CAPTIONS):
                OfferingImage.objects.create(
                    offering=offering,
                    image=_gallery_photo(i, caption),
                    caption=caption,
                    order=i,
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"✔ {created} صورة إضافية عبر {offerings.count()} تخصص"))
