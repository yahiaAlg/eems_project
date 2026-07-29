"""
Seed sample Formateur (instructor) profiles, with a tasteful generated
initials-avatar photo (brand-colored, no external assets), and assign
them round-robin to a handful of existing active Offerings so the
catalogue/detail/profile pages have something real to show.

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

FORMATEURS = [
    {
        "full_name": "أ. كريم بوزيدي",
        "title": "خبير HSE معتمد — مدقق ISO 45001",
        "years_experience": 14,
        "bio": (
            "مهندس في السلامة الصناعية بخبرة تفوق 14 سنة في قطاعي المحروقات والبناء. "
            "شارك في تكوين أكثر من 1200 متربص، ومدقق معتمد لأنظمة إدارة الصحة والسلامة "
            "المهنية ISO 45001. يركّز في تكويناته على الجانب التطبيقي والحالات الميدانية الحقيقية."
        ),
    },
    {
        "full_name": "أ. سميرة حاجي",
        "title": "أخصائية بيئة وتسيير المخاطر الصناعية",
        "years_experience": 9,
        "bio": (
            "حاصلة على ماجستير في علوم البيئة، عملت لسنوات كمسؤولة بيئة في مؤسسات صناعية "
            "كبرى قبل الانضمام إلى فريق التكوين بمؤسسة التميز. تُدرّس تخصصات إدارة النفايات "
            "والتدقيق البيئي بأسلوب عملي قريب من واقع المؤسسات الجزائرية."
        ),
    },
    {
        "full_name": "أ. ياسين مرزوقي",
        "title": "مكوّن معتمد في البناء والأشغال العمومية",
        "years_experience": 11,
        "bio": (
            "مهندس مدني بخبرة ميدانية واسعة في مشاريع البناء والأشغال العمومية بالجزائر. "
            "يجمع بين التكوين النظري والتطبيق الميداني المباشر في الورشات الشريكة للمؤسسة."
        ),
    },
    {
        "full_name": "أ. أمينة شريف",
        "title": "مكوّنة في التسيير الإداري والمحاسبي",
        "years_experience": 7,
        "bio": (
            "خبيرة في التسيير الإداري والمحاسبي للمؤسسات الصغيرة والمتوسطة، عملت مستشارة "
            "لدى عدة مؤسسات ناشئة بسطيف قبل التفرغ للتكوين المهني بدوام كامل."
        ),
    },
]


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
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 140)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), initials, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((w - tw) / 2 - bbox[0], (h - th) / 2 - bbox[1]), initials, fill=(255, 255, 255), font=font)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return ContentFile(buf.getvalue(), name=f"formateur-{initials}.jpg")


class Command(BaseCommand):
    help = "Seed sample Formateur profiles and assign them round-robin to existing active offerings."

    @transaction.atomic
    def handle(self, *args, **options):
        formateurs = []
        for i, data in enumerate(FORMATEURS, start=1):
            f, _ = Formateur.objects.update_or_create(
                full_name=data["full_name"],
                defaults={
                    "title": data["title"],
                    "bio": data["bio"],
                    "years_experience": data["years_experience"],
                    "order": i,
                    "is_active": True,
                },
            )
            if not f.photo:
                f.photo.save(f"{f.slug}.jpg", _avatar_photo(f.full_name), save=False)
                f.save()
            formateurs.append(f)
        self.stdout.write(self.style.SUCCESS(f"✔ {len(formateurs)} formateurs"))

        offerings = list(Offering.objects.filter(is_active=True).order_by("order"))
        if not offerings:
            self.stdout.write(self.style.WARNING(
                "↷ لا توجد تخصصات — شغّل 'python manage.py seed_enrollment' أولا لربط المكوّنين بتكوينات."
            ))
            return

        assigned = 0
        for i, offering in enumerate(offerings):
            if offering.formateur_id:
                continue  # don't override a manually-assigned formateur
            offering.formateur = formateurs[i % len(formateurs)]
            offering.save(update_fields=["formateur"])
            assigned += 1
        self.stdout.write(self.style.SUCCESS(f"✔ assigned formateurs to {assigned} offering(s)"))
