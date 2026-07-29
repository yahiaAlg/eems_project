"""
Seed the About and FAQ pages with realistic content, plus tasteful
generated placeholder photography for AboutPage.hero_image / story_image
(brand-colored gradient + soft glow + geometric mark — no external
image files needed, no more grey empty-box icons).

Idempotent: safe to run multiple times.

Usage:
    python manage.py seed_about_faq
"""

import io
import math

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from pages.models import AboutPage, AboutValue, FAQCategory, FAQItem, Milestone

NAVY = (15, 23, 42)
NAVY_MID = (30, 41, 59)
ACCENT = (245, 158, 11)

ABOUT_VALUES = [
    ("bi bi-shield-check", "الجدية والمصداقية",
     "نلتزم بأعلى معايير الجودة في كل برامجنا التكوينية، مع متابعة صارمة لمحتوى الدروس ومؤهلات الأطر المكوّنة."),
    ("bi bi-people", "القرب من المتربص",
     "نضع المتربص في قلب اهتمامنا، من الاستقبال إلى التوجيه المهني بعد التخرج، عبر مرافقة فردية ومستمرة."),
    ("bi bi-graph-up-arrow", "التحسين المستمر",
     "نراجع برامجنا دوريا وفق تطورات سوق الشغل ومعايير QSE الدولية لضمان تكوين يواكب احتياجات المؤسسات."),
    ("bi bi-award", "الاعتماد والشهادات",
     "شهاداتنا معترف بها وتُسلَّم وفق كناسة التكوين المهني، مما يمنح خريجينا قيمة مضافة حقيقية في سوق العمل."),
]

MILESTONES = [
    ("2016", "الانطلاقة", "تأسيس مؤسسة التميز للإدارة والسلامة بسطيف بفرعين مهنيين فقط، بطاقم من 4 مكوّنين."),
    ("2018", "الاعتماد الرسمي", "حصول المؤسسة على الاعتماد الرسمي من وزارة التكوين والتعليم المهنيين."),
    ("2020", "التوسع الرقمي", "إطلاق منصة التسجيل الإلكتروني وأول دفعة تكوين عن بعد في مجال HSE."),
    ("2022", "شراكات دولية", "عقد شراكات تكوينية مع هيئات دولية معتمدة في مجال الصحة والسلامة (IOSH, NEBOSH)."),
    ("2025", "23 فرعا مهنيا", "بلوغ المؤسسة 23 فرعا مهنيا وأكثر من 500 تخصص، بخبرة تراكمية تفوق 15 سنة."),
]

FAQ_DATA = [
    ("bi bi-clipboard-check", "التسجيل والترشح", [
        ("كيف يمكنني التسجيل في أحد التكوينات؟",
         "يمكنك التسجيل مباشرة عبر الموقع من صفحة التخصصات: اختر التخصص المناسب، ثم اضغط على زر «التفاصيل والتسجيل» واملأ استمارة الترشح. سيتواصل معك فريقنا خلال 48 ساعة عمل لتأكيد ترشحك."),
        ("ما هي الوثائق المطلوبة للتسجيل؟",
         "بطاقة التعريف الوطنية، آخر شهادة متحصل عليها، وصورتان شمسيتان. قد تُطلب وثائق إضافية حسب طبيعة التخصص (مثل شهادة طبية لبعض تخصصات BTP)."),
        ("هل يمكنني التسجيل إذا كنت من ولاية أخرى؟",
         "نعم، التسجيل مفتوح لكل المترشحين من مختلف الولايات، ويمكن إتمام إجراءات الترشح الأولية عن بعد قبل الحضور الفعلي عند بداية الدورة."),
        ("متى يبدأ الموسم التكويني الجديد؟",
         "لدينا دورات تنطلق بشكل دوري خلال السنة (سبتمبر، جانفي، أفريل). تفاصيل كل دورة وتواريخ الانطلاق متوفرة في صفحة كل تخصص."),
    ]),
    ("bi bi-cash-coin", "الرسوم والدفع", [
        ("هل يمكن تقسيط رسوم التكوين؟",
         "نعم، تتوفر معظم تخصصاتنا على صيغة الدفع الشهري بالإضافة إلى صيغة الدفع الكلي المخفّض. التفاصيل الدقيقة لكل تخصص متوفرة في بطاقته التقنية."),
        ("هل هناك رسوم تسجيل غير قابلة للاسترجاع؟",
         "لا توجد رسوم تسجيل مسبقة. تُدفع الرسوم فقط بعد تأكيد القبول النهائي في التكوين."),
        ("ما هي طرق الدفع المتاحة؟",
         "الدفع نقدا أو بشيك على مستوى المؤسسة، بالإضافة إلى تسهيلات خاصة للمؤسسات الشريكة والمجموعات."),
    ]),
    ("bi bi-mortarboard", "التكوين والشهادات", [
        ("هل الشهادات المسلَّمة معترف بها رسميا؟",
         "نعم، جميع شهاداتنا معتمدة من وزارة التكوين والتعليم المهنيين، وبعض التخصصات تتوج بشهادات دولية إضافية (IOSH, NEBOSH, ISO)."),
        ("ما الفرق بين مستويات التكوين المتوفرة؟",
         "نقترح عدة مستويات دخول (ابتدائي، متوسط، ثانوي، جامعي) بحسب كل تخصص، موضّحة بدقة في البطاقة التقنية الخاصة بكل تكوين."),
        ("هل يوجد تكوين تطبيقي أم نظري فقط؟",
         "أغلب تخصصاتنا تجمع بين الجانب النظري والتطبيقي، مع فترات تربص ميداني لدى مؤسسات شريكة حسب طبيعة التخصص."),
    ]),
    ("bi bi-headset", "الدعم والتواصل", [
        ("كيف أتواصل مع فريق الدعم؟",
         "يمكنكم التواصل معنا عبر صفحة «الاتصال والوصول»، أو عبر الهاتف والبريد الإلكتروني الموضّحين في أسفل كل صفحة، أو عبر صفحاتنا على مواقع التواصل الاجتماعي."),
        ("هل يمكنني طرح سؤال خاص حول تخصص معيّن؟",
         "بالتأكيد، كل صفحة تخصص تحتوي نموذج استفسار مباشر أسفل تفاصيل التكوين، وسيجيبكم فريقنا في أقرب وقت ممكن."),
    ]),
]


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _placeholder_photo(caption, size=(1000, 700), seed=0):
    """Generate a tasteful brand-colored placeholder photo: diagonal
    navy gradient, a soft amber glow, a faint grid, and a centered
    geometric mark + caption — entirely offline, no external assets."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    w, h = size
    img = Image.new("RGB", size, NAVY)
    px = img.load()
    for y in range(h):
        t = y / h
        row_color = _lerp(NAVY, NAVY_MID, t)
        for x in range(0, w, 4):  # step 4 for speed, fine for a soft gradient
            px[x, y] = row_color
            if x + 1 < w: px[x + 1, y] = row_color
            if x + 2 < w: px[x + 2, y] = row_color
            if x + 3 < w: px[x + 3, y] = row_color

    # Soft amber glow, top-right
    glow = Image.new("L", size, 0)
    gdraw = ImageDraw.Draw(glow)
    gx, gy, gr = int(w * 0.82) + seed * 15, int(h * 0.18), int(w * 0.38)
    gdraw.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(80))
    amber_layer = Image.new("RGB", size, ACCENT)
    img = Image.composite(amber_layer, img, glow)

    draw = ImageDraw.Draw(img)
    # Faint grid
    step = 40
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=(255, 255, 255, 10))
    for gy2 in range(0, h, step):
        draw.line([(0, gy2), (w, gy2)], fill=(255, 255, 255, 10))
    grid_overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    gdraw2 = ImageDraw.Draw(grid_overlay)
    for x in range(0, w, step):
        gdraw2.line([(x, 0), (x, h)], fill=(255, 255, 255, 8))
    for gy2 in range(0, h, step):
        gdraw2.line([(0, gy2), (w, gy2)], fill=(255, 255, 255, 8))
    img = Image.alpha_composite(img.convert("RGBA"), grid_overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Centered geometric "shield" mark
    cx, cy = w // 2, int(h * 0.42)
    r = int(min(w, h) * 0.16)
    ring_color = (255, 255, 255)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ring_color, width=4)
    draw.ellipse([cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14], outline=ACCENT, width=3)
    # simple checkmark inside
    draw.line([(cx - r * 0.35, cy), (cx - r * 0.08, cy + r * 0.3), (cx + r * 0.4, cy - r * 0.35)],
              fill=ACCENT, width=8, joint="curve")

    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except OSError:
        font_big = ImageFont.load_default()
        font_small = font_big

    label = "EEMS"
    bbox = draw.textbbox((0, 0), label, font=font_big)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw / 2, cy + r + 26), label, fill=(255, 255, 255), font=font_big)

    if caption:
        bbox2 = draw.textbbox((0, 0), caption, font=font_small)
        cw = bbox2[2] - bbox2[0]
        draw.text((cx - cw / 2, cy + r + 70), caption, fill=(255, 255, 255, 180), font=font_small)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=87)
    return ContentFile(buf.getvalue(), name=f"placeholder-{caption or 'about'}-{seed}.jpg")


class Command(BaseCommand):
    help = "Seed About page (hero/story/values/timeline) and FAQ (categories + items) with realistic content."

    @transaction.atomic
    def handle(self, *args, **options):
        self.seed_about()
        self.seed_faq()
        self.stdout.write(self.style.SUCCESS("✔ About + FAQ content seeded."))

    def seed_about(self):
        about = AboutPage.load()
        if not about.hero_description:
            about.hero_description = (
                "منذ سنة 2016، تُكوّن مؤسسة التميز للإدارة والسلامة (EEMS) الآلاف من المسيرين "
                "والمشرفين في مجالات الصحة والسلامة والبيئة (HSE) والتقنية والتسيير، بخبرة ميدانية "
                "واعتماد رسمي من وزارة التكوين والتعليم المهنيين."
            )
        if not about.story_body:
            about.story_body = (
                "انطلقت مؤسسة التميز للإدارة والسلامة من فكرة بسيطة: تكوين مهني حقيقي، قريب من "
                "احتياجات سوق الشغل، بأطر ذوي خبرة ميدانية وليس فقط أكاديمية.\n\n"
                "بدأنا بفرعين مهنيين فقط سنة 2016، واليوم نفتخر بتقديم أكثر من 500 تخصص موزعة على "
                "23 فرعا مهنيا، ومرافقة آلاف المتربصين نحو الاندماج المهني الناجح.\n\n"
                "نواصل اليوم استثمارنا في تطوير برامجنا البيداغوجية وتكوين مكوّنينا وفق أحدث "
                "المعايير الدولية في مجال QSE، لضمان تكوين يواكب تطلعات المتربصين والمؤسسات على حد سواء."
            )
        if not about.hero_image:
            about.hero_image.save("about-hero.jpg", _placeholder_photo("من نحن", seed=1), save=False)
        if not about.story_image:
            about.story_image.save("about-story.jpg", _placeholder_photo("قصتنا", seed=2), save=False)
        about.save()
        self.stdout.write(self.style.SUCCESS("✔ AboutPage hero/story content"))

        for i, (icon, title, text) in enumerate(ABOUT_VALUES, start=1):
            AboutValue.objects.update_or_create(
                title=title, defaults={"icon_class": icon, "text": text, "order": i}
            )
        self.stdout.write(self.style.SUCCESS(f"✔ {len(ABOUT_VALUES)} about values"))

        for i, (year, title, text) in enumerate(MILESTONES, start=1):
            Milestone.objects.update_or_create(
                year=year, title=title, defaults={"text": text, "order": i}
            )
        self.stdout.write(self.style.SUCCESS(f"✔ {len(MILESTONES)} milestones"))

    def seed_faq(self):
        total_items = 0
        for i, (icon, cat_name, items) in enumerate(FAQ_DATA, start=1):
            category, _ = FAQCategory.objects.update_or_create(
                name=cat_name, defaults={"icon_class": icon, "order": i}
            )
            for j, (question, answer) in enumerate(items, start=1):
                FAQItem.objects.update_or_create(
                    category=category, question=question,
                    defaults={"answer": answer, "order": j, "is_active": True},
                )
                total_items += 1
        self.stdout.write(self.style.SUCCESS(f"✔ {len(FAQ_DATA)} FAQ categories, {total_items} questions"))
