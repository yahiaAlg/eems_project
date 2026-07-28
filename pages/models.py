import hashlib

from django.db import models


# ──────────────────────────────────────────────────────────────────
#  Site visitor counter — unique visits tracked by hashed IP + date
# ──────────────────────────────────────────────────────────────────
class SiteVisitor(models.Model):
    ip_hash = models.CharField("هاش IP", max_length=64, db_index=True)
    date = models.DateField("التاريخ", db_index=True)

    class Meta:
        unique_together = ("ip_hash", "date")
        ordering = ["-date"]
        verbose_name = "زيارة"
        verbose_name_plural = "📈 إحصائيات الزوار"

    def __str__(self):
        return str(self.date)

    @classmethod
    def record(cls, request):
        """Hash the visitor IP and record one visit per IP per day."""
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = (
            forwarded.split(",")[0].strip()
            if forwarded
            else request.META.get("REMOTE_ADDR", "0.0.0.0")
        )
        if isinstance(ip, bytes):
            ip = ip.decode("utf-8", errors="ignore")
        ip_hash = ip.encode()
        from datetime import date

        cls.objects.get_or_create(ip_hash=ip_hash, date=date.today())


# ──────────────────────────────────────────────────────────────────
#  Base singleton — used for models that must have exactly ONE row
#  (editable through Django admin like a settings page, never a list)
# ──────────────────────────────────────────────────────────────────
class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Singleton rows can't be deleted from the admin.
        pass

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


# ──────────────────────────────────────────────────────────────────
#  SiteSettings — singleton: identity, hero, video, map, contact, footer
# ──────────────────────────────────────────────────────────────────
class SiteSettings(SingletonModel):
    # Identity
    site_name = models.CharField("اسم المؤسسة", max_length=120, default="إيمس")
    site_full_name = models.CharField(
        "الاسم الكامل", max_length=200, default="مؤسسة التميز للإدارة والأمن"
    )
    logo = models.ImageField("الشعار", upload_to="site/", blank=True, null=True)
    browser_title = models.CharField(
        "عنوان المتصفح", max_length=200, default="إيمس — مؤسسة التميز للإدارة والأمن"
    )

    # Hero section
    hero_badge_text = models.CharField(
        "شارة الهيرو",
        max_length=150,
        blank=True,
        default="معتمدة من وزارة التكوين والتعليم المهنيين",
    )
    hero_title_line1 = models.CharField(
        "العنوان - السطر 1", max_length=150, default="مؤسسة التميز"
    )
    hero_title_line2 = models.CharField(
        "العنوان - السطر 2", max_length=150, default="للإدارة"
    )
    hero_title_accent = models.CharField(
        "العنوان - الكلمة المميزة", max_length=150, default="والأمن"
    )
    hero_description = models.TextField("وصف الهيرو", blank=True)
    hero_image = models.ImageField(
        "صورة الهيرو", upload_to="site/", blank=True, null=True
    )
    hero_cta_primary_text = models.CharField(
        "زر أساسي - نص", max_length=80, default="اطّلع على تكويناتنا"
    )
    hero_cta_primary_url = models.CharField(
        "زر أساسي - رابط", max_length=200, default="#formations"
    )
    hero_cta_secondary_text = models.CharField(
        "زر ثانوي - نص", max_length=80, default="التصنيف الرسمي"
    )
    hero_cta_secondary_url = models.CharField(
        "زر ثانوي - رابط", max_length=200, default="nomenclature/"
    )

    # Section intros (reused across the page)
    formations_label = models.CharField(
        "التكوينات - تسمية", max_length=100, default="الكتالوج الرسمي 2019"
    )
    formations_title = models.CharField(
        "التكوينات - عنوان", max_length=150, default="23 فرعا مهنيا"
    )
    formations_description = models.TextField("التكوينات - وصف", blank=True)

    # Video section
    video_label = models.CharField("الفيديو - تسمية", max_length=100, default="اكتشف")
    video_title = models.CharField(
        "الفيديو - عنوان", max_length=150, default="المسير العملي"
    )
    video_description = models.TextField("الفيديو - وصف", blank=True)
    video_youtube_embed_url = models.URLField(
        "رابط يوتيوب (embed)",
        blank=True,
        default="https://www.youtube.com/embed/1h4-kRB8OjA?si=6XjJKFKHlIqeWta_",
    )

    # Gallery / carousel intro
    gallery_label = models.CharField(
        "المعرض - تسمية", max_length=100, default="معرض الصور"
    )
    gallery_title = models.CharField(
        "المعرض - عنوان", max_length=150, default="مرحبا بكم في إيمس"
    )

    # Map section
    map_label = models.CharField("الموقع - تسمية", max_length=100, default="الموقع")
    map_title = models.CharField("الموقع - عنوان", max_length=150, default="كيف تجدنا")
    map_description = models.TextField("الموقع - وصف", blank=True)
    map_embed_url = models.URLField(
        "رابط خريطة Google (embed)", blank=True, max_length=500
    )

    # Contact / info strip
    address = models.CharField("العنوان", max_length=255, blank=True)
    phone = models.CharField("الهاتف", max_length=50, blank=True)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    working_hours = models.CharField("أوقات العمل", max_length=150, blank=True)

    # Footer
    footer_description = models.TextField("وصف التذييل", blank=True)
    footer_copyright = models.CharField(
        "حقوق النشر",
        max_length=200,
        default="© 2025 إيمس — مؤسسة التميز للإدارة والأمن — جميع الحقوق محفوظة.",
    )
    footer_location_text = models.CharField(
        "موقع التذييل", max_length=150, blank=True, default="سطيف، الجزائر"
    )

    class Meta:
        verbose_name = "إعدادات الموقع"
        verbose_name_plural = "⚙️ إعدادات الموقع"

    def __str__(self):
        return "إعدادات الموقع"


# ──────────────────────────────────────────────────────────────────
#  Hero statistics  (15 فرعا / +500 تخصصا / +15 سنوات خبرة)
# ──────────────────────────────────────────────────────────────────
class HeroStat(models.Model):
    value = models.CharField("القيمة", max_length=30, help_text="مثال: 15 أو +500")
    label = models.CharField("التسمية", max_length=80, help_text="مثال: فرعا")
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "إحصائية"
        verbose_name_plural = "📊 إحصائيات الصفحة الرئيسية"

    def __str__(self):
        return f"{self.value} {self.label}"


# ──────────────────────────────────────────────────────────────────
#  Mission / Vision / Compétences cards
# ──────────────────────────────────────────────────────────────────
class MissionCard(models.Model):
    COLOR_CHOICES = [
        ("amber", "أصفر (amber)"),
        ("green", "أخضر (green)"),
        ("blue", "أزرق (blue)"),
    ]
    icon_class = models.CharField(
        "أيقونة Bootstrap",
        max_length=60,
        default="bi bi-bullseye",
        help_text="مثال: bi bi-bullseye",
    )
    color = models.CharField(
        "اللون", max_length=20, choices=COLOR_CHOICES, default="amber"
    )
    title = models.CharField("العنوان", max_length=100)
    text = models.TextField("النص")
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "بطاقة هوية"
        verbose_name_plural = "🪪 بطاقات الهوية المؤسسية (مهمتنا/رؤيتنا/كفاءاتنا)"

    def __str__(self):
        return self.title


# ──────────────────────────────────────────────────────────────────
#  Carousel / photo gallery
# ──────────────────────────────────────────────────────────────────
class CarouselImage(models.Model):
    image = models.ImageField("الصورة", upload_to="carousel/")
    caption = models.CharField("التعليق (alt)", max_length=150, blank=True)
    order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("مفعّلة", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "صورة"
        verbose_name_plural = "🖼️ معرض الصور (Carousel)"

    def __str__(self):
        return self.caption or f"صورة #{self.pk}"


# ──────────────────────────────────────────────────────────────────
#  Catalogue: professional Branches & Specialties (official 2019 nomenclature)
# ──────────────────────────────────────────────────────────────────
class Branch(models.Model):
    code = models.CharField("الرمز", max_length=10, unique=True)
    name_ar = models.CharField("الاسم بالعربية", max_length=150)
    name_fr = models.CharField("الاسم بالفرنسية", max_length=150, blank=True)
    color = models.CharField("اللون (hex)", max_length=10, default="#0f172a")
    order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("مفعّل", default=True)

    class Meta:
        ordering = ["order", "code"]
        verbose_name = "فرع مهني"
        verbose_name_plural = "📚 الفروع المهنية"

    def __str__(self):
        return f"{self.code} — {self.name_ar}"


class Specialty(models.Model):
    code = models.CharField("الرمز", max_length=12, unique=True)
    name = models.CharField("اسم التخصص", max_length=255)
    branch = models.ForeignKey(
        Branch,
        verbose_name="الفرع المهني",
        related_name="specialties",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ["branch__order", "code"]
        verbose_name = "تخصص"
        verbose_name_plural = "🗂️ التخصصات (الكتالوج الرسمي 2019)"

    def __str__(self):
        return f"{self.code} — {self.name}"


# ──────────────────────────────────────────────────────────────────
#  Upcoming training sessions
# ──────────────────────────────────────────────────────────────────
class TrainingSession(models.Model):
    STATUS_PLANNED = "planned"
    STATUS_OPEN = "open"
    STATUS_CHOICES = [
        (STATUS_PLANNED, "مبرمجة"),
        (STATUS_OPEN, "التسجيل مفتوح"),
    ]

    title = models.CharField("عنوان الدورة", max_length=200)
    start_date = models.DateField("تاريخ الانطلاق")
    duration_text = models.CharField("المدة", max_length=50, help_text="مثال: 5 أيام")
    seats = models.PositiveIntegerField("عدد المقاعد")
    status = models.CharField(
        "الحالة", max_length=10, choices=STATUS_CHOICES, default=STATUS_PLANNED
    )
    branch = models.ForeignKey(
        Branch,
        verbose_name="الفرع المهني",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sessions",
    )
    is_active = models.BooleanField("مفعّلة (تظهر في الصفحة)", default=True)
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "start_date"]
        verbose_name = "دورة قادمة"
        verbose_name_plural = "🗓️ الدورات القادمة"

    def __str__(self):
        return f"{self.title} ({self.start_date:%d/%m})"


# ──────────────────────────────────────────────────────────────────
#  Social links (footer)
# ──────────────────────────────────────────────────────────────────
class SocialLink(models.Model):
    PLATFORM_CHOICES = [
        ("facebook", "Facebook"),
        ("linkedin", "LinkedIn"),
        ("instagram", "Instagram"),
        ("whatsapp", "WhatsApp"),
        ("twitter", "Twitter / X"),
        ("telegram", "Telegram"),
        ("snapchat", "Snapchat"),
        ("youtube", "YouTube"),
        ("email", "Email"),
        ("other", "أخرى"),
    ]
    # Bootstrap-icon fallback (used if no static PNG icon is found for the platform)
    ICONS = {
        "facebook": "bi bi-facebook",
        "linkedin": "bi bi-linkedin",
        "instagram": "bi bi-instagram",
        "whatsapp": "bi bi-whatsapp",
        "twitter": "bi bi-twitter-x",
        "telegram": "bi bi-telegram",
        "snapchat": "bi bi-snapchat",
        "youtube": "bi bi-youtube",
        "email": "bi bi-envelope-fill",
        "other": "bi bi-link-45deg",
    }
    # Real brand-icon PNGs shipped in pages/static/pages/images/ — these stay as
    # static files (not admin-uploaded content), referenced directly by name.
    STATIC_ICONS = {
        "facebook": "pages/images/Face.png",
        "linkedin": "pages/images/Link.png",
        "instagram": "pages/images/Inst.png",
        "whatsapp": "pages/images/Wats.png",
        "twitter": "pages/images/Twit.png",
        "telegram": "pages/images/Teleg.png",
        "snapchat": "pages/images/Snap.png",
    }

    platform = models.CharField("المنصة", max_length=20, choices=PLATFORM_CHOICES)
    url = models.CharField("الرابط", max_length=255)
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "رابط اجتماعي"
        verbose_name_plural = "🔗 الروابط الاجتماعية"

    @property
    def icon_class(self):
        return self.ICONS.get(self.platform, "bi bi-link-45deg")

    @property
    def static_icon(self):
        """Static path (relative, for {% static %}) of the brand PNG icon, or None."""
        return self.STATIC_ICONS.get(self.platform)

    def __str__(self):
        return self.get_platform_display()


# ──────────────────────────────────────────────────────────────────
#  Internal apps (pedagogy, billing, nomenclature...) — navbar/hero/footer
# ──────────────────────────────────────────────────────────────────
class InternalApp(models.Model):
    COLOR_CHOICES = [
        ("amber", "أصفر (amber)"),
        ("teal", "أخضر مائي (teal)"),
        ("blue", "أزرق (blue)"),
    ]
    title = models.CharField("العنوان", max_length=100)
    subtitle = models.CharField("العنوان الفرعي", max_length=150, blank=True)
    icon_class = models.CharField(
        "أيقونة Bootstrap", max_length=60, default="bi bi-app"
    )
    url = models.CharField("الرابط", max_length=255)
    color = models.CharField(
        "اللون", max_length=20, choices=COLOR_CHOICES, default="amber"
    )
    open_in_new_tab = models.BooleanField("فتح في نافذة جديدة", default=True)
    show_in_navbar = models.BooleanField("إظهار في شريط التصفح", default=True)
    show_in_hero = models.BooleanField("إظهار في الهيرو", default=True)
    show_in_footer = models.BooleanField("إظهار في التذييل", default=True)
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "تطبيق داخلي"
        verbose_name_plural = "🧩 التطبيقات الداخلية"

    def __str__(self):
        return self.title


# ──────────────────────────────────────────────────────────────────
#  Footer quick navigation links (التصفح)
# ──────────────────────────────────────────────────────────────────
class NavLink(models.Model):
    label = models.CharField("التسمية", max_length=100)
    url = models.CharField("الرابط", max_length=255)
    icon_class = models.CharField(
        "أيقونة Bootstrap", max_length=60, default="bi bi-chevron-left"
    )
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "رابط تصفح"
        verbose_name_plural = "🧭 روابط التصفح (التذييل)"

    def __str__(self):
        return self.label


# ──────────────────────────────────────────────────────────────────
#  Partner / accreditation logos (trust strip)
# ──────────────────────────────────────────────────────────────────
class Partner(models.Model):
    name = models.CharField("الاسم", max_length=120)
    logo = models.ImageField("الشعار", upload_to="partners/")
    url = models.URLField("الرابط", blank=True)
    order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("مفعّل", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "شريك / جهة اعتماد"
        verbose_name_plural = "🤝 الشركاء وجهات الاعتماد"

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────────────────────────
#  "How we work" process steps
# ──────────────────────────────────────────────────────────────────
class ProcessStep(models.Model):
    icon_class = models.CharField(
        "أيقونة Bootstrap", max_length=60, default="bi bi-1-circle"
    )
    title = models.CharField("العنوان", max_length=100)
    description = models.TextField("الوصف", blank=True)
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "خطوة"
        verbose_name_plural = "🪜 كيف نعمل (خطوات التسجيل)"

    def __str__(self):
        return self.title


# ──────────────────────────────────────────────────────────────────
#  Testimonials / success stories
# ──────────────────────────────────────────────────────────────────
class Testimonial(models.Model):
    name = models.CharField("الاسم", max_length=120)
    role = models.CharField("الصفة / المؤسسة", max_length=150, blank=True)
    photo = models.ImageField("الصورة", upload_to="testimonials/", blank=True, null=True)
    quote = models.TextField("الشهادة")
    order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("مفعّلة", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "شهادة نجاح"
        verbose_name_plural = "💬 شهادات النجاح"

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────────────────────────
#  Newsletter subscribers
# ──────────────────────────────────────────────────────────────────
class NewsletterSubscriber(models.Model):
    email = models.EmailField("البريد الإلكتروني", unique=True)
    created_at = models.DateTimeField("تاريخ الاشتراك", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "مشترك في النشرة"
        verbose_name_plural = "📩 المشتركون في النشرة الإخبارية"

    def __str__(self):
        return self.email


# ──────────────────────────────────────────────────────────────────
#  About page — singleton hero/story + repeatable values & milestones
# ──────────────────────────────────────────────────────────────────
class AboutPage(SingletonModel):
    hero_label = models.CharField(
        "شارة الصفحة", max_length=100, blank=True, default="من نحن"
    )
    hero_title = models.CharField(
        "عنوان الصفحة", max_length=200, default="قصة مؤسسة التميز للإدارة والأمن"
    )
    hero_description = models.TextField("وصف مختصر", blank=True)
    hero_image = models.ImageField(
        "صورة الصفحة", upload_to="site/about/", blank=True, null=True
    )

    story_label = models.CharField(
        "قصتنا - تسمية", max_length=100, blank=True, default="قصتنا"
    )
    story_title = models.CharField(
        "قصتنا - عنوان", max_length=200, blank=True, default="كيف بدأنا"
    )
    story_body = models.TextField("قصتنا - نص", blank=True)
    story_image = models.ImageField(
        "قصتنا - صورة", upload_to="site/about/", blank=True, null=True
    )

    values_label = models.CharField(
        "القيم - تسمية", max_length=100, blank=True, default="قيمنا"
    )
    values_title = models.CharField(
        "القيم - عنوان", max_length=200, blank=True, default="ما الذي يميزنا"
    )

    timeline_label = models.CharField(
        "المسار الزمني - تسمية", max_length=100, blank=True, default="مسارنا"
    )
    timeline_title = models.CharField(
        "المسار الزمني - عنوان", max_length=200, blank=True, default="محطات بارزة"
    )

    class Meta:
        verbose_name = "صفحة من نحن"
        verbose_name_plural = "📖 صفحة من نحن"

    def __str__(self):
        return "صفحة من نحن"


class AboutValue(models.Model):
    icon_class = models.CharField(
        "أيقونة Bootstrap", max_length=60, default="bi bi-gem"
    )
    title = models.CharField("العنوان", max_length=100)
    text = models.TextField("النص")
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "قيمة"
        verbose_name_plural = "💎 قيم المؤسسة (صفحة من نحن)"

    def __str__(self):
        return self.title


class Milestone(models.Model):
    year = models.CharField("السنة", max_length=20)
    title = models.CharField("العنوان", max_length=150)
    text = models.TextField("النص", blank=True)
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "year"]
        verbose_name = "محطة"
        verbose_name_plural = "🏁 المسار الزمني (صفحة من نحن)"

    def __str__(self):
        return f"{self.year} — {self.title}"


# ──────────────────────────────────────────────────────────────────
#  FAQ page — categories + items
# ──────────────────────────────────────────────────────────────────
class FAQCategory(models.Model):
    name = models.CharField("اسم الفئة", max_length=120)
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "فئة أسئلة"
        verbose_name_plural = "🗂️ فئات الأسئلة الشائعة"

    def __str__(self):
        return self.name


class FAQItem(models.Model):
    category = models.ForeignKey(
        FAQCategory,
        verbose_name="الفئة",
        related_name="items",
        on_delete=models.CASCADE,
    )
    question = models.CharField("السؤال", max_length=255)
    answer = models.TextField("الجواب")
    order = models.PositiveIntegerField("الترتيب", default=0)
    is_active = models.BooleanField("مفعّل", default=True)

    class Meta:
        ordering = ["category__order", "order", "id"]
        verbose_name = "سؤال شائع"
        verbose_name_plural = "❓ الأسئلة الشائعة"

    def __str__(self):
        return self.question


# ──────────────────────────────────────────────────────────────────
#  Contact page — intro singleton + incoming messages
# ──────────────────────────────────────────────────────────────────
class ContactPageSettings(SingletonModel):
    label = models.CharField(
        "تسمية", max_length=100, blank=True, default="تواصل معنا"
    )
    title = models.CharField(
        "عنوان", max_length=200, blank=True, default="نحن هنا لمساعدتك"
    )
    description = models.TextField("وصف", blank=True)

    class Meta:
        verbose_name = "إعدادات صفحة الاتصال"
        verbose_name_plural = "☎️ إعدادات صفحة الاتصال"

    def __str__(self):
        return "إعدادات صفحة الاتصال"


class ContactMessage(models.Model):
    SUBJECT_CHOICES = [
        ("info", "طلب معلومات عن التكوينات"),
        ("enrollment", "استفسار حول التسجيل"),
        ("partnership", "شراكة / تعاون"),
        ("complaint", "شكوى / ملاحظة"),
        ("other", "أخرى"),
    ]
    STATUS_NEW = "new"
    STATUS_READ = "read"
    STATUS_REPLIED = "replied"
    STATUS_CHOICES = [
        (STATUS_NEW, "جديدة"),
        (STATUS_READ, "مقروءة"),
        (STATUS_REPLIED, "تم الرد"),
    ]

    name = models.CharField("الاسم الكامل", max_length=150)
    email = models.EmailField("البريد الإلكتروني")
    phone = models.CharField("الهاتف", max_length=50, blank=True)
    subject = models.CharField(
        "الموضوع", max_length=20, choices=SUBJECT_CHOICES, default="info"
    )
    message = models.TextField("الرسالة")
    status = models.CharField(
        "الحالة", max_length=10, choices=STATUS_CHOICES, default=STATUS_NEW
    )
    created_at = models.DateTimeField("تاريخ الإرسال", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "رسالة تواصل"
        verbose_name_plural = "✉️ رسائل التواصل"

    def __str__(self):
        return f"{self.name} — {self.get_subject_display()}"
