from django.core.validators import FileExtensionValidator
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify

# Allowed extensions for admin-uploaded "custom" documents (CV / fiche
# technique / certificates) — no PDF-generation library is used anywhere
# in this app; when a real PDF is wanted, the admin uploads one here.
CUSTOM_DOCUMENT_EXTENSIONS = ["pdf", "doc", "docx", "jpg", "jpeg", "png", "webp"]


def attachment_kind(filename):
    """Classify an uploaded file by extension, for icon/label purposes."""
    ext = filename.rsplit(".", 1)[-1].lower() if filename and "." in filename else ""
    if ext == "pdf":
        return "pdf"
    if ext in ("doc", "docx"):
        return "doc"
    if ext in ("jpg", "jpeg", "png", "webp", "gif"):
        return "image"
    if ext in ("html", "htm"):
        return "html"
    return "file"


ATTACHMENT_ICONS = {
    "pdf": "mdi:file-pdf-box",
    "doc": "mdi:file-word-box",
    "image": "mdi:file-image-outline",
    "html": "mdi:file-document-outline",
    "file": "mdi:paperclip",
}


class AttachmentBase(models.Model):
    """Shared behaviour for optional admin-uploaded PDF/image/HTML attachments
    (fiche technique documents, formateur certificates, ...)."""

    title = models.CharField("العنوان", max_length=150, blank=True)
    order = models.PositiveIntegerField("الترتيب", default=0)
    uploaded_at = models.DateTimeField("تاريخ الإضافة", auto_now_add=True)

    class Meta:
        abstract = True

    @property
    def kind(self):
        return attachment_kind(self.file.name) if self.file else "file"

    @property
    def is_pdf(self):
        return self.kind == "pdf"

    @property
    def is_image(self):
        return self.kind == "image"

    @property
    def is_html(self):
        return self.kind == "html"

    @property
    def is_doc(self):
        return self.kind == "doc"

    @property
    def icon(self):
        return ATTACHMENT_ICONS[self.kind]

    @property
    def action_icon(self):
        # HTML documents are viewed/printed in a new tab, not "downloaded"
        return "mdi:printer-outline" if self.is_html else "mdi:download-outline"

    @property
    def meta_label(self):
        if self.is_html:
            return "معاينة وطباعة (Print / Save as PDF)"
        if not self.file:
            return ""
        from django.template.defaultfilters import filesizeformat

        try:
            return filesizeformat(self.file.size)
        except (OSError, ValueError):
            return ""

    @property
    def display_title(self):
        import os

        return self.title or (os.path.basename(self.file.name) if self.file else "ملف")


CV_MODES = [
    ("auto", "توليد تلقائي — نموذج قابل للطباعة يُبنى من بيانات الملف الشخصي"),
    ("custom", "رفع ملف مخصص (PDF / Word / صورة)"),
]


class Formateur(models.Model):
    """A trainer/instructor — optionally linked to one or more Offerings."""

    full_name = models.CharField("الاسم الكامل", max_length=150)
    slug = models.SlugField("المعرف (slug)", unique=True, blank=True)
    title = models.CharField(
        "الصفة المهنية",
        max_length=150,
        blank=True,
        help_text="مثال: خبير HSE معتمد — 12 سنة خبرة ميدانية",
    )
    photo = models.ImageField(
        "الصورة الشخصية",
        upload_to="enrollment/formateurs/",
        blank=True,
        null=True,
    )
    bio = models.TextField("نبذة تعريفية", blank=True)
    years_experience = models.PositiveSmallIntegerField(
        "سنوات الخبرة",
        null=True,
        blank=True,
    )
    email = models.EmailField("البريد الإلكتروني", blank=True)
    linkedin_url = models.URLField("رابط LinkedIn", blank=True)
    cv_mode = models.CharField(
        "نمط السيرة الذاتية",
        max_length=10,
        choices=CV_MODES,
        default="auto",
        help_text=(
            "توليد تلقائي: يُبنى نموذج CV قابل للطباعة من بيانات هذه الصفحة "
            "(النبذة، المسار المهني...) تلقائيا وفوريا. مخصص: يُستعمل الملف "
            "المرفوع أدناه بدل النموذج التلقائي."
        ),
    )
    cv_file = models.FileField(
        "ملف CV مخصص",
        upload_to="enrollment/formateurs/cv/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(CUSTOM_DOCUMENT_EXTENSIONS)],
        help_text="PDF / Word / صورة — يُستعمل فقط عند اختيار النمط «مخصص» أعلاه.",
    )
    is_active = models.BooleanField("مفعّل (يظهر على الموقع)", default=True)
    order = models.PositiveIntegerField("الترتيب", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "full_name"]
        verbose_name = "مكوّن"
        verbose_name_plural = "👤 المكوّنون (الأساتذة)"

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.full_name, allow_unicode=True) or "formateur"
            slug = base
            i = 1
            while Formateur.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("enrollment:formateur_detail", args=[self.slug])

    @property
    def active_offerings(self):
        return self.offerings.filter(is_active=True, session__is_active=True)

    @property
    def cv_is_custom(self):
        return self.cv_mode == "custom" and bool(self.cv_file)

    @property
    def cv_url(self):
        if self.cv_is_custom:
            return self.cv_file.url
        return reverse("enrollment:formateur_cv", args=[self.slug])

    @property
    def cv_kind(self):
        return attachment_kind(self.cv_file.name) if self.cv_is_custom else "html"

    @property
    def cv_icon(self):
        return ATTACHMENT_ICONS[self.cv_kind]

    @property
    def cv_action_label(self):
        return "تحميل السيرة الذاتية (CV)" if self.cv_is_custom else "معاينة CV وطباعته"

    @property
    def cv_action_icon(self):
        return "mdi:download-outline" if self.cv_is_custom else "mdi:printer-outline"


class FormateurCertificate(AttachmentBase):
    """An optional certificate/credential attachment (PDF or image) shown
    on the formateur's public profile page — diploma, accreditation, etc."""

    formateur = models.ForeignKey(
        Formateur,
        on_delete=models.CASCADE,
        related_name="certificates",
        verbose_name="المكوّن",
    )
    issuer = models.CharField("الجهة المانحة", max_length=150, blank=True)
    date_obtained = models.DateField("تاريخ الحصول عليها", null=True, blank=True)
    file = models.FileField(
        "ملف الشهادة (PDF / Word / صورة)",
        upload_to="enrollment/formateurs/certificates/",
        validators=[FileExtensionValidator(CUSTOM_DOCUMENT_EXTENSIONS)],
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "شهادة / اعتماد"
        verbose_name_plural = "🎓 الشهادات والاعتمادات"

    def __str__(self):
        return self.display_title or f"شهادة #{self.pk} — {self.formateur.full_name}"


class FormateurCareerEntry(models.Model):
    """One entry in the formateur's professional timeline (Udemy-style bio 'parcours')."""

    formateur = models.ForeignKey(
        Formateur,
        on_delete=models.CASCADE,
        related_name="career_entries",
        verbose_name="المكوّن",
    )
    role_title = models.CharField("المنصب / الوظيفة", max_length=150)
    organization = models.CharField("الجهة / المؤسسة", max_length=150, blank=True)
    start_year = models.PositiveSmallIntegerField("سنة البداية", null=True, blank=True)
    end_year = models.PositiveSmallIntegerField(
        "سنة النهاية",
        null=True,
        blank=True,
        help_text="اتركه فارغا إن كان المنصب ساريا حاليا.",
    )
    description = models.TextField("وصف مختصر", blank=True)
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "-start_year"]
        verbose_name = "محطة مهنية"
        verbose_name_plural = "🧭 المسار المهني (Parcours)"

    def __str__(self):
        return f"{self.role_title} — {self.organization}"

    @property
    def period_label(self):
        if self.start_year and self.end_year:
            return f"{self.start_year} – {self.end_year}"
        if self.start_year and not self.end_year:
            return f"{self.start_year} – حاليا"
        return ""


class FormationSession(models.Model):
    """A recurring intake, e.g. 'دورة سبتمبر 2025'."""

    name = models.CharField("اسم الدورة", max_length=120)
    slug = models.SlugField("المعرف (slug)", unique=True)

    start_date = models.DateField("تاريخ الانطلاق", null=True, blank=True)
    registration_deadline = models.DateField("آخر أجل للتسجيل", null=True, blank=True)
    is_active = models.BooleanField("مفتوحة للتسجيل", default=True)
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["-start_date", "order"]
        verbose_name = "دورة تكوينية"
        verbose_name_plural = "الدورات التكوينية"

    def __str__(self):
        return self.name


QUALIFICATION_LEVELS = [
    (1, "1 - شهادة تكوين مهني متخصص (ش.م.ت.م)"),
    (2, "2 - شهادة الكفاءة المهنية (ش.ك.م)"),
    (3, "3 - شهادة التحكم المهني (ش.ت.م)"),
    (4, "4 - شهادة تقني (ش.ت)"),
    (5, "5 - شهادة تقني سامي (ش.ت.س)"),
]

CERT_TYPES = [
    ("qualification", "شهادة تأهيل مهني"),
    ("cfpm", "شهادة تكوين مهني متخصص"),
    ("cap", "شهادة الكفاءة المهنية"),
    ("bpm", "شهادة التحكم المهني"),
    ("tech", "شهادة تقني"),
    ("tech_sup", "شهادة تقني سامي"),
]

ENTRY_LEVELS = [
    ("none", "بدون مستوى / محو أمية منتهي"),
    ("middle4", "4 متوسط"),
    ("sec1", "1 ثانوي"),
    ("sec2", "2 ثانوي"),
    ("sec3", "3 ثانوي"),
]


FICHE_TECHNIQUE_MODES = [
    ("auto", "توليد تلقائي — نموذج قابل للطباعة يُبنى من بيانات هذا التخصص"),
    ("custom", "رفع ملف مخصص (PDF / Word / صورة)"),
]


class Offering(models.Model):
    """A specialty as taught within a given session — carries pricing/seat data."""

    session = models.ForeignKey(
        FormationSession,
        on_delete=models.CASCADE,
        related_name="offerings",
        verbose_name="الدورة",
    )
    specialty = models.ForeignKey(
        "pages.Specialty",
        on_delete=models.PROTECT,
        related_name="offerings",
        null=True,
        blank=True,
        verbose_name="التخصص (مدونة الشعب)",
    )
    formateur = models.ForeignKey(
        Formateur,
        on_delete=models.SET_NULL,
        related_name="offerings",
        null=True,
        blank=True,
        verbose_name="المكوّن (اختياري)",
    )
    code = models.CharField("رمز الاختصاص", max_length=20, help_text="مثال: TAG0701")
    title = models.CharField("عنوان التخصص", max_length=150)
    branch_label = models.CharField("الشعبة", max_length=100, blank=True)
    qualification_level = models.PositiveSmallIntegerField(
        "مستوى التأهيل",
        choices=QUALIFICATION_LEVELS,
        null=True,
        blank=True,
    )
    certificate_type = models.CharField(
        "الشهادة المسلمة",
        max_length=20,
        choices=CERT_TYPES,
        blank=True,
    )
    entry_level = models.CharField(
        "مستوى الدخول",
        max_length=20,
        choices=ENTRY_LEVELS,
        blank=True,
    )
    duration_months = models.PositiveSmallIntegerField("مدة التكوين (أشهر)")
    monthly_fee = models.DecimalField(
        "القيمة الشهرية (دج)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    total_fee = models.DecimalField(
        "القيمة الإجمالية (دج)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    seats_available = models.PositiveSmallIntegerField("قدرة الاستيعاب", default=0)
    description = models.TextField("تعريف التخصص", blank=True)
    main_tasks = models.TextField(
        "المهام الأساسية",
        blank=True,
        help_text="سطر واحد لكل مهمة",
    )
    objectives = models.TextField(
        "أهداف التكوين",
        blank=True,
        help_text="سطر واحد لكل هدف — يظهر ضمن الملف التقني.",
    )
    program_outline = models.TextField(
        "برنامج التكوين (المحاور)",
        blank=True,
        help_text="سطر واحد لكل محور/وحدة — يظهر ضمن الملف التقني.",
    )
    prerequisites = models.TextField(
        "الشروط المسبقة",
        blank=True,
        help_text="سطر واحد لكل شرط — يظهر ضمن الملف التقني.",
    )
    fiche_technique_mode = models.CharField(
        "نمط الملف التقني",
        max_length=10,
        choices=FICHE_TECHNIQUE_MODES,
        default="auto",
        help_text=(
            "توليد تلقائي: يُبنى نموذج قابل للطباعة من الحقول أعلاه (الوصف، الأهداف، "
            "البرنامج...) تلقائيا وفوريا. مخصص: يُستعمل الملف المرفوع أدناه بدل النموذج التلقائي."
        ),
    )
    fiche_technique_file = models.FileField(
        "ملف الملف التقني المخصص",
        upload_to="enrollment/offerings/fiche_technique_custom/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(CUSTOM_DOCUMENT_EXTENSIONS)],
        help_text="PDF / Word / صورة — يُستعمل فقط عند اختيار النمط «مخصص» أعلاه.",
    )
    image = models.ImageField(
        "صورة (ملف مرفوع)",
        upload_to="enrollment/offerings/",
        blank=True,
        null=True,
    )
    poster_url = models.URLField(
        "رابط صورة الملصق (بطاقة العرض)",
        blank=True,
        help_text="يُستعمل إن لم يتم رفع صورة أعلاه. يمكن استعمال رابط من خدمة صور مجانية.",
    )
    background_url = models.URLField(
        "رابط صورة الخلفية (صفحة التفاصيل)",
        blank=True,
        help_text="تُعرض كخلفية لرأس صفحة التخصص.",
    )
    video_url = models.URLField(
        "رابط فيديو تعريفي (YouTube)",
        blank=True,
        help_text="ألصق رابط فيديو يوتيوب ترويجي لهذا التخصص (اختياري).",
    )
    is_active = models.BooleanField("معروضة على الموقع", default=True)
    is_featured = models.BooleanField(
        "تخصص مميز (يظهر في الصفحة الرئيسية)", default=False
    )
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "code"]
        unique_together = ("session", "code")
        verbose_name = "عرض تكوين"
        verbose_name_plural = "عروض التكوين"

    def __str__(self):
        return f"{self.code} — {self.title} ({self.session})"

    @property
    def seats_taken(self):
        return self.enrollments.filter(
            status__in=["pending", "contacted", "accepted", "confirmed"],
        ).count()

    @property
    def seats_remaining(self):
        return max(self.seats_available - self.seats_taken, 0)

    @property
    def fill_rate(self):
        if not self.seats_available:
            return 0
        return min(round(100 * self.seats_taken / self.seats_available), 100)

    @property
    def tasks_list(self):
        return [line.strip() for line in self.main_tasks.splitlines() if line.strip()]

    @property
    def objectives_list(self):
        return [line.strip() for line in self.objectives.splitlines() if line.strip()]

    @property
    def program_outline_list(self):
        return [
            line.strip() for line in self.program_outline.splitlines() if line.strip()
        ]

    @property
    def prerequisites_list(self):
        return [
            line.strip() for line in self.prerequisites.splitlines() if line.strip()
        ]

    @property
    def has_fiche_technique_extras(self):
        return bool(
            self.objectives_list or self.program_outline_list or self.prerequisites_list
        )

    @property
    def fiche_technique_is_custom(self):
        return self.fiche_technique_mode == "custom" and bool(self.fiche_technique_file)

    @property
    def fiche_technique_url(self):
        if self.fiche_technique_is_custom:
            return self.fiche_technique_file.url
        return reverse(
            "enrollment:fiche_technique", args=[self.session.slug, self.code]
        )

    @property
    def fiche_technique_kind(self):
        return (
            attachment_kind(self.fiche_technique_file.name)
            if self.fiche_technique_is_custom
            else "html"
        )

    @property
    def fiche_technique_icon(self):
        return ATTACHMENT_ICONS[self.fiche_technique_kind]

    @property
    def fiche_technique_action_label(self):
        return (
            "تحميل الملف التقني"
            if self.fiche_technique_is_custom
            else "معاينة الفيشة وطباعتها"
        )

    @property
    def fiche_technique_action_icon(self):
        return (
            "mdi:download-outline"
            if self.fiche_technique_is_custom
            else "mdi:printer-outline"
        )

    @property
    def approved_comments(self):
        return self.comments.filter(is_approved=True)

    @property
    def average_rating(self):
        approved = list(self.approved_comments)
        if not approved:
            return 0
        return round(sum(c.rating for c in approved) / len(approved), 1)

    @property
    def comments_count(self):
        return self.approved_comments.count()

    def get_absolute_url(self):
        return reverse("enrollment:detail", args=[self.session.slug, self.code])

    @property
    def poster_src(self):
        """Best available poster image: uploaded file > custom URL > free placeholder API."""
        if self.image:
            return self.image.url
        if self.poster_url:
            return self.poster_url
        return f"https://picsum.photos/seed/{self.code}/700/500"

    @property
    def background_src(self):
        """Best available background image for the detail-page hero."""
        if self.background_url:
            return self.background_url
        if self.image:
            return self.image.url
        return f"https://picsum.photos/seed/{self.code}-bg/1600/900"

    @property
    def youtube_embed_id(self):
        """Extract the YouTube video id from common URL formats."""
        import re

        if not self.video_url:
            return ""
        match = re.search(
            r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([\w-]{11})",
            self.video_url,
        )
        return match.group(1) if match else ""


class OfferingImage(models.Model):
    """A secondary gallery image for an Offering's detail page (shown as a
    thumbnail strip + lightbox, underneath the main poster image)."""

    offering = models.ForeignKey(
        Offering,
        on_delete=models.CASCADE,
        related_name="gallery_images",
        verbose_name="التخصص",
    )
    image = models.ImageField("الصورة", upload_to="enrollment/offerings/gallery/")
    caption = models.CharField("تعليق (اختياري)", max_length=150, blank=True)
    order = models.PositiveIntegerField("الترتيب", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "صورة إضافية"
        verbose_name_plural = "🖼️ معرض الصور (صور إضافية)"

    def __str__(self):
        return self.caption or f"صورة #{self.pk} — {self.offering.code}"


class OfferingAttachment(AttachmentBase):
    """A supplementary downloadable document for the offering (program
    brochure, referential excerpt, schedule graphic, ...) — a PDF, Word
    or image uploaded by the admin. Shown as a piece-jointe list on the
    offering's detail page, in addition to the primary fiche technique
    (Offering.fiche_technique_mode / fiche_technique_file, see above)
    and separate from the visual gallery/slider."""

    offering = models.ForeignKey(
        Offering,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="التخصص",
    )
    file = models.FileField(
        "الملف (PDF / Word / صورة)",
        upload_to="enrollment/offerings/fiche_technique/",
        validators=[FileExtensionValidator(CUSTOM_DOCUMENT_EXTENSIONS)],
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "وثيقة مرفقة (مرفق إضافي)"
        verbose_name_plural = "📎 مرفقات إضافية للتخصص"

    def __str__(self):
        return self.display_title or f"مرفق #{self.pk} — {self.offering.code}"


SOURCE_CHOICES = [
    ("web", "الموقع الإلكتروني"),
    ("facebook", "فيسبوك"),
    ("instagram", "إنستغرام"),
    ("qr", "QR Code"),
    ("phone", "اتصال هاتفي"),
    ("walkin", "حضور مباشر"),
]

STATUS_CHOICES = [
    ("pending", "قيد الدراسة"),
    ("contacted", "تم التواصل"),
    ("accepted", "مقبول"),
    ("confirmed", "مؤكد من طرف المشترك"),
    ("waitlisted", "قائمة انتظار"),
    ("rejected", "مرفوض"),
    ("cancelled", "ملغى من طرف المشترك"),
]

GENDER_CHOICES = [("m", "ذكر"), ("f", "أنثى")]

CLIENT_TYPE_CHOICES = [
    ("individual", "فرد (خاص)"),
    ("enterprise", "مؤسسة"),
]

# Auth-account status for a Client (see `accounts` app — Phase 1 of TODO.md).
# A Client only gets a linked django.contrib.auth.User once they register;
# walk-in/legacy clients created by staff without a login default to
# "active" so they are never accidentally blocked from anything that
# checks this field.
ACCOUNT_STATUS_CHOICES = [
    ("pending", "قيد المراجعة"),
    ("active", "نشط"),
    ("rejected", "مرفوض"),
]


class Client(models.Model):
    """The subscriber: either a private individual, or an enterprise sending participants."""

    client_type = models.CharField(
        "نوع الزبون",
        max_length=20,
        choices=CLIENT_TYPE_CHOICES,
        default="individual",
    )

    # --- shared contact fields ---
    phone = models.CharField("رقم الهاتف", max_length=20)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    wilaya = models.CharField("الولاية", max_length=60, blank=True, default="سطيف")
    address = models.CharField("العنوان", max_length=255, blank=True)

    # --- individual-only fields ---
    full_name = models.CharField("الاسم واللقب", max_length=150, blank=True)
    birth_date = models.DateField("تاريخ الميلاد", null=True, blank=True)
    gender = models.CharField("الجنس", max_length=1, choices=GENDER_CHOICES, blank=True)
    education_level = models.CharField("المستوى الدراسي", max_length=100, blank=True)

    # --- enterprise-only fields ---
    company_name = models.CharField("اسم المؤسسة", max_length=200, blank=True)
    trade_register_number = models.CharField(
        "رقم السجل التجاري", max_length=60, blank=True
    )
    sector = models.CharField("قطاع النشاط", max_length=120, blank=True)
    responsible_name = models.CharField(
        "الشخص المسؤول عن التنسيق",
        max_length=150,
        blank=True,
    )
    responsible_position = models.CharField("منصب المسؤول", max_length=100, blank=True)

    source = models.CharField(
        "مصدر التسجيل",
        max_length=20,
        choices=SOURCE_CHOICES,
        default="web",
    )

    # --- account fields (Phase 1 — Auth Foundation, see accounts app) ---
    is_vip = models.BooleanField(
        "زبون VIP",
        default=False,
        help_text="يُفعَّل فقط من طرف الإدارة أو المحاسب.",
    )
    account_status = models.CharField(
        "حالة الحساب",
        max_length=10,
        choices=ACCOUNT_STATUS_CHOICES,
        default="active",
        help_text="pending: بانتظار موافقة الإدارة — active: مفعّل — rejected: مرفوض.",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client",
        verbose_name="حساب الدخول",
        help_text=(
            "يُربط تلقائيا عند التسجيل عبر النموذج العمومي (المرحلة 1.3). "
            "فارغ لزبائن الحضور المباشر/الإدخال اليدوي القدامى الذين لا "
            "يملكون حساب دخول."
        ),
    )

    created_at = models.DateTimeField("تاريخ التسجيل", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "زبون (مشترك)"
        verbose_name_plural = "الزبائن (المشتركون)"

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.company_name if self.client_type == "enterprise" else self.full_name

    @property
    def is_enterprise(self):
        return self.client_type == "enterprise"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.client_type == "individual" and not self.full_name:
            raise ValidationError("الاسم الكامل مطلوب بالنسبة للأفراد.")
        if self.client_type == "enterprise" and not self.company_name:
            raise ValidationError("اسم المؤسسة مطلوب بالنسبة للمؤسسات.")


class Participant(models.Model):
    """A person actually attending the training. For an individual client, there is
    exactly one participant (the client themselves). For an enterprise client, this
    is one of possibly many employees sent to the training."""

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="participants",
        verbose_name="الزبون",
    )
    full_name = models.CharField("الاسم واللقب", max_length=150)
    phone = models.CharField("رقم الهاتف", max_length=20, blank=True)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    birth_date = models.DateField("تاريخ الميلاد", null=True, blank=True)
    gender = models.CharField("الجنس", max_length=1, choices=GENDER_CHOICES, blank=True)
    education_level = models.CharField("المستوى الدراسي", max_length=100, blank=True)
    position = models.CharField(
        "المنصب داخل المؤسسة",
        max_length=100,
        blank=True,
        help_text="يُستعمل فقط عندما يكون الزبون مؤسسة",
    )

    class Meta:
        ordering = ["full_name"]
        verbose_name = "مشارك"
        verbose_name_plural = "المشاركون"

    def __str__(self):
        return self.full_name


class Enrollment(models.Model):
    """One participant's registration in one offering."""

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="الزبون",
    )
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="المشارك",
    )
    offering = models.ForeignKey(
        Offering,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="التخصص المطلوب",
    )
    motivation = models.TextField("ملاحظات / دافع الترشح", blank=True)
    status = models.CharField(
        "الحالة",
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="عولجت من طرف",
    )
    confirmed_at = models.DateTimeField("تاريخ التأكيد", null=True, blank=True)
    cancelled_at = models.DateTimeField("تاريخ الإلغاء", null=True, blank=True)
    created_at = models.DateTimeField("تاريخ التسجيل", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("participant", "offering")
        verbose_name = "تسجيل"
        verbose_name_plural = "التسجيلات"

    def __str__(self):
        return f"{self.participant} → {self.offering.code}"

    @property
    def can_confirm(self):
        """Self-service confirmation is only offered while the subscriber
        hasn't already confirmed or cancelled it themselves."""
        return self.status not in ("confirmed", "cancelled")

    @property
    def can_cancel(self):
        """Once confirmed, an enrollment is locked and can no longer be
        self-cancelled from the client dashboard."""
        return self.status not in ("confirmed", "cancelled")


class EnrollmentNote(models.Model):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    text = models.TextField("ملاحظة")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "ملاحظة متابعة"
        verbose_name_plural = "ملاحظات المتابعة"

    def __str__(self):
        return f"note on enrollment #{self.enrollment_id}"


RATING_CHOICES = [(i, "★" * i) for i in range(1, 6)]


class Comment(models.Model):
    """A public review/comment left by a visitor on a specific offering (moderated)."""

    offering = models.ForeignKey(
        Offering,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="التخصص",
    )
    name = models.CharField("الاسم", max_length=120)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    rating = models.PositiveSmallIntegerField(
        "التقييم",
        choices=RATING_CHOICES,
        default=5,
    )
    text = models.TextField("التعليق")
    is_approved = models.BooleanField("موافق عليه (يظهر في الموقع)", default=False)
    created_at = models.DateTimeField("تاريخ النشر", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "تعليق"
        verbose_name_plural = "تعليقات الزوار"

    def __str__(self):
        return f"{self.name} — {self.offering.code} ({self.rating}★)"


class Enquiry(models.Model):
    """A public question about an offering (or a general enquiry), answered by staff."""

    offering = models.ForeignKey(
        Offering,
        on_delete=models.CASCADE,
        related_name="enquiries",
        verbose_name="التخصص",
        null=True,
        blank=True,
    )
    name = models.CharField("الاسم", max_length=120)
    phone = models.CharField("الهاتف", max_length=20, blank=True)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    question = models.TextField("السؤال / الاستفسار")
    answer = models.TextField("الرد", blank=True)
    is_answered = models.BooleanField("تمت الإجابة", default=False)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="أجاب عليه",
    )
    created_at = models.DateTimeField("تاريخ الإرسال", auto_now_add=True)
    answered_at = models.DateTimeField("تاريخ الرد", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "استفسار"
        verbose_name_plural = "استفسارات الزوار"

    def __str__(self):
        return f"{self.name}: {self.question[:40]}"
