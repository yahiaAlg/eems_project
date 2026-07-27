"""
Seed sample data for the new home-page features (partners, process steps,
testimonials, featured offerings, sample comments/enquiries/enrollments)
so the endpoints described in docs/TESTING.md have something to show.

Idempotent: safe to run multiple times (uses update_or_create / get_or_create).

Usage:
    python manage.py seed_data          # base site content (run first)
    python manage.py seed_enrollment    # sample formations catalog (run second)
    python manage.py seed_samples       # this command (run third)
"""

import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from pages.models import Partner, ProcessStep, Testimonial

PARTNER_COLORS = [
    ("وزارة التكوين والتعليم المهنيين", "#0f172a"),
    ("IOSH", "#0e7490"),
    ("NEBOSH", "#b45309"),
    ("ISO 45001", "#15803d"),
]

PROCESS_STEPS = [
    ("bi bi-pencil-square", "الترشح", "قدّم طلب ترشحك للتخصص الذي يهمك عبر الموقع في دقائق معدودة.", 1),
    ("bi bi-telephone-outbound", "التواصل", "يتصل بك فريقنا لتأكيد معلوماتك والإجابة عن أسئلتك.", 2),
    ("bi bi-clipboard-check", "التسجيل النهائي", "أكمل إجراءات التسجيل وتثبيت مقعدك في الدورة.", 3),
    ("bi bi-mortarboard", "بداية التكوين", "انطلق في مسارك التكويني في الموعد المحدد.", 4),
]

TESTIMONIALS = [
    ("أحمد بلعيد", "خريج دورة سبتمبر 2024", "تكوين محترف وأطر ذوو خبرة ميدانية حقيقية، ساعدني كثيرا في إيجاد عمل بعد التخرج."),
    ("سارة مرابط", "أمينة مخزن، مؤسسة صناعية بسطيف", "التكوين العملي والمتابعة المستمرة من الفريق البيداغوجي كانا نقطة تحول في مساري المهني."),
    ("مؤسسة النور للبناء", "شريك مؤسساتي", "أرسلنا عدة عمال لتكوين السلامة المهنية وكانت النتائج ملموسة في تحسين إجراءات الأمن بالورشات."),
]


def _placeholder_logo(text, hex_color, size=(240, 120)):
    """Generate a simple colored placeholder PNG with a label, entirely
    offline (no external image needed) so Partner.logo always has real,
    valid image bytes."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", size, hex_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([4, 4, size[0] - 4, size[1] - 4], outline="#ffffff", width=3)
    # Centered label — default PIL font, no external font files needed.
    bbox = draw.textbbox((0, 0), text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size[0] - tw) / 2, (size[1] - th) / 2), text, fill="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return ContentFile(buf.getvalue(), name=f"{text[:20]}.png")


class Command(BaseCommand):
    help = "Seed sample data for the new features (partners, process steps, testimonials, featured offerings, sample comments/enquiries)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.seed_partners()
        self.seed_process_steps()
        self.seed_testimonials()
        self.seed_featured_offerings()
        self.seed_comments_and_enquiries()
        self.seed_sample_enrollment()
        self.stdout.write(self.style.SUCCESS("✔ Sample data for the new features loaded."))

    # ── Partners / accreditation logos ───────────────────────────
    def seed_partners(self):
        for i, (name, color) in enumerate(PARTNER_COLORS, start=1):
            partner, created = Partner.objects.get_or_create(
                name=name, defaults={"order": i}
            )
            if not partner.logo:
                partner.logo.save(f"{name}.png", _placeholder_logo(name, color), save=False)
            partner.order = i
            partner.is_active = True
            partner.save()
        self.stdout.write(self.style.SUCCESS(f"✔ {len(PARTNER_COLORS)} partners"))

    # ── "How we work" process steps ──────────────────────────────
    def seed_process_steps(self):
        for icon, title, desc, order in PROCESS_STEPS:
            ProcessStep.objects.update_or_create(
                title=title, defaults={"icon_class": icon, "description": desc, "order": order}
            )
        self.stdout.write(self.style.SUCCESS(f"✔ {len(PROCESS_STEPS)} process steps"))

    # ── Testimonials ──────────────────────────────────────────────
    def seed_testimonials(self):
        for i, (name, role, quote) in enumerate(TESTIMONIALS, start=1):
            Testimonial.objects.update_or_create(
                name=name, defaults={"role": role, "quote": quote, "order": i, "is_active": True}
            )
        self.stdout.write(self.style.SUCCESS(f"✔ {len(TESTIMONIALS)} testimonials"))

    # ── Mark a couple of existing offerings as featured ──────────
    def seed_featured_offerings(self):
        try:
            from enrollment.models import Offering
        except ImportError:
            return
        offerings = list(Offering.objects.filter(is_active=True).order_by("order")[:2])
        if not offerings:
            self.stdout.write(
                self.style.WARNING(
                    "↷ لا توجد تخصصات — شغّل 'python manage.py seed_enrollment' أولا لعرض شريط 'تكوينات هذا الموسم'."
                )
            )
            return
        for offering in offerings:
            offering.is_featured = True
            offering.save(update_fields=["is_featured"])
        self.stdout.write(self.style.SUCCESS(f"✔ {len(offerings)} offering(s) marked as featured"))

    # ── Sample approved comment + answered enquiry (specialty_detail page) ──
    def seed_comments_and_enquiries(self):
        try:
            from enrollment.models import Comment, Enquiry, Offering
        except ImportError:
            return
        offering = Offering.objects.filter(is_active=True).order_by("order").first()
        if not offering:
            return
        Comment.objects.get_or_create(
            offering=offering, name="خالد بومدين", email="khaled@example.com",
            defaults={"rating": 5, "text": "تكوين رائع وأطر متمكنون، أنصح به بشدة.", "is_approved": True},
        )
        Enquiry.objects.get_or_create(
            offering=offering, name="ياسمين عمراوي", phone="0550000000",
            defaults={
                "email": "yasmine@example.com",
                "question": "هل التسجيل مفتوح للمترشحين من ولايات أخرى؟",
                "answer": "نعم، التسجيل مفتوح لكل الولايات، ويمكن استكمال الإجراءات عن بعد.",
                "is_answered": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"✔ sample comment + answered enquiry on {offering.code}"))

    # ── Sample enrollment (Client + Participant + Enrollment) ───
    # Gives the admin dashboard / seats_taken counters something to show.
    def seed_sample_enrollment(self):
        try:
            from enrollment.models import Client, Enrollment, Offering, Participant
        except ImportError:
            return
        offering = Offering.objects.filter(is_active=True).order_by("order").first()
        if not offering:
            return
        client, _ = Client.objects.get_or_create(
            phone="0555123456",
            defaults={
                "client_type": "individual",
                "full_name": "سميرة حمداني",
                "email": "samira.test@example.com",
                "wilaya": "سطيف",
                "source": "web",
            },
        )
        participant, _ = Participant.objects.get_or_create(
            client=client, full_name=client.full_name,
            defaults={"phone": client.phone, "email": client.email},
        )
        Enrollment.objects.get_or_create(
            participant=participant, offering=offering,
            defaults={"client": client, "status": "accepted", "motivation": "بيانات تجريبية لأغراض الاختبار."},
        )
        self.stdout.write(self.style.SUCCESS(f"✔ sample accepted enrollment on {offering.code}"))
