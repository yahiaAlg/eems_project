from django.core.validators import FileExtensionValidator, MinValueValidator
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

# Group/enterprise pricing basis (TODO 3.1) — how a VIP client's cart line
# for a given Offering is priced: by the number of training days, or by the
# number of participants sent. Reused as-is by `CartItem.billing_basis`
# (Phase 4) and downstream by `ProformaInvoice`/`QuoteRequest` line items
# (Phase 5/6), so it is defined once here rather than per-model.
BILLING_BASIS_CHOICES = [
    ("per_day", "حسب عدد أيام التكوين"),
    ("per_participant", "حسب عدد المشاركين"),
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
        help_text="مسار التسجيل الفردي (تكوين تأهيلي طويل المدى بالأشهر).",
    )
    total_fee = models.DecimalField(
        "القيمة الإجمالية (دج)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="مسار التسجيل الفردي (تكوين تأهيلي طويل المدى بالأشهر).",
    )

    # --- group/enterprise pricing (TODO 3.1) ---
    # A distinct pricing dimension from monthly_fee/total_fee above: those
    # price an *individual* candidate's long qualification program (billed
    # by the month, see `duration_months`). Enterprise/VIP clients instead
    # book short group trainings for a variable number of employees, priced
    # either by the day (flat group rate, e.g. an on-site session billed per
    # day regardless of headcount) or by the participant (per-seat rate,
    # e.g. a per-person course fee) — the billing basis a VIP client will
    # choose per cart line in Phase 4 (`CartItem.billing_basis`, same
    # `BILLING_BASIS_CHOICES`). Both are optional and independent of each
    # other and of monthly_fee/total_fee; an offering can carry any
    # combination that applies to it.
    price_per_day = models.DecimalField(
        "السعر لليوم الواحد (دج)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="مسار الزبائن VIP/المؤسسات — فوترة جماعية بالسعر لكل يوم تكوين.",
    )
    price_per_participant = models.DecimalField(
        "السعر للمشارك الواحد (دج)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="مسار الزبائن VIP/المؤسسات — فوترة بالسعر لكل مشارك.",
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
    def has_group_pricing(self):
        """True if this offering can be booked via the VIP/enterprise group
        pricing path (TODO 3.1) — i.e. it carries at least one of the two
        group billing bases, independent of the individual monthly_fee/
        total_fee pricing."""
        return bool(self.price_per_day or self.price_per_participant)

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

# Enterprise legal/accounting fields (TODO 2.1) that must be filled in
# before an enterprise VIP client can submit a Phase 5 "Request Proforma"
# — the validation gate implemented in TODO 2.3 (`Client.missing_legal_fields`).
# Non-VIP enterprises are unaffected: their Phase 5 flow is "Request Quote",
# priced afterwards by an accountant, so no legal info is needed up front.
ENTERPRISE_LEGAL_REQUIRED_FIELDS = [
    ("trade_register_number", "رقم السجل التجاري (RC)"),
    ("forme_juridique", "الشكل القانوني"),
    ("nif", "رقم التعريف الجبائي (NIF)"),
    ("nis", "رقم التعريف الإحصائي (NIS)"),
    ("article_imposition", "رقم المادة الجبائية"),
    ("rib", "رقم الحساب البنكي (RIB)"),
    ("address", "العنوان"),
    ("postal_code", "الرمز البريدي"),
    ("city", "البلدية / المدينة"),
    ("main_contact_name", "المسؤول عن الفوترة (الاسم)"),
    ("main_contact_phone", "المسؤول عن الفوترة (الهاتف)"),
    ("main_contact_email", "المسؤول عن الفوترة (البريد الإلكتروني)"),
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
        "رقم السجل التجاري (RC)",
        max_length=60,
        blank=True,
        help_text="رقم السجل التجاري — يُستعمل أيضا كمرجع RC في المستخرجات المحاسبية.",
    )
    sector = models.CharField("قطاع النشاط", max_length=120, blank=True)
    responsible_name = models.CharField(
        "الشخص المسؤول عن التنسيق",
        max_length=150,
        blank=True,
    )
    responsible_position = models.CharField("منصب المسؤول", max_length=100, blank=True)

    # --- enterprise legal/accounting fields (TODO 2.1) ---
    # Cross-checked against the accounting-export column set
    # (`revenus_par_client`): legal form, tax identifiers, bank details and
    # a distinct billing contact, on top of the coordination contact above
    # (`responsible_name`/`responsible_position`, which is about who
    # coordinates the training logistics day-to-day, not who is billed).
    forme_juridique = models.CharField(
        "الشكل القانوني",
        max_length=100,
        blank=True,
        help_text="مثال: SARL، SPA، EURL، مؤسسة فردية...",
    )
    nif = models.CharField(
        "رقم التعريف الجبائي (NIF)", max_length=30, blank=True
    )
    nis = models.CharField(
        "رقم التعريف الإحصائي (NIS)", max_length=30, blank=True
    )
    article_imposition = models.CharField(
        "رقم المادة الجبائية (Article d'imposition)", max_length=30, blank=True
    )
    rib = models.CharField(
        "رقم الحساب البنكي (RIB)",
        max_length=30,
        blank=True,
        help_text="20 رقما — يُستعمل في إعداد الفواتير/الحوالات.",
    )
    tva_exempt = models.BooleanField(
        "معفى من الرسم على القيمة المضافة (TVA)", default=False
    )
    postal_code = models.CharField("الرمز البريدي", max_length=10, blank=True)
    city = models.CharField("البلدية / المدينة", max_length=100, blank=True)
    website = models.URLField("الموقع الإلكتروني", blank=True)

    # Distinct billing/legal contact — separate from `responsible_name`/
    # `responsible_position` above, which is the day-to-day training
    # coordination contact and may be a different person entirely.
    main_contact_name = models.CharField(
        "الشخص المسؤول عن الفوترة (الاسم)", max_length=150, blank=True
    )
    main_contact_phone = models.CharField(
        "الشخص المسؤول عن الفوترة (الهاتف)", max_length=20, blank=True
    )
    main_contact_email = models.EmailField(
        "الشخص المسؤول عن الفوترة (البريد الإلكتروني)", blank=True
    )

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

    @property
    def missing_legal_fields(self):
        """Labels of required enterprise legal/accounting fields (TODO 2.1)
        that are still blank on this client. Always empty for individuals —
        the Phase 5 proforma gate (TODO 2.3) only concerns enterprises."""
        if not self.is_enterprise:
            return []
        return [
            label
            for field_name, label in ENTERPRISE_LEGAL_REQUIRED_FIELDS
            if not str(getattr(self, field_name) or "").strip()
        ]

    @property
    def has_complete_legal_info(self):
        return not self.missing_legal_fields

    @property
    def needs_legal_info_for_proforma(self):
        """TODO 2.3 gate: True when this client is a VIP enterprise (the
        only client type/tier that can submit a Phase 5 "Request Proforma")
        and its legal profile is still incomplete. Phase 5's proforma view
        must check this and block submission — showing a prompt linking to
        the profile page — until it is False."""
        return self.is_vip and self.is_enterprise and not self.has_complete_legal_info

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


# --- Cart & Cart items (TODO 4.1) ---------------------------------------
# One active `Cart` per `Client`, holding queued `CartItem` lines before
# checkout (Phase 5 branches VIP clients into a "Request Proforma" flow and
# non-VIP clients into a "Request Quote" flow — see TODO.md Phase 5). A
# client keeps a single row per client+status="active" (enforced below by
# a partial unique constraint); once checked out (TODO 5.4) the cart is
# expected to be flipped to "converted" rather than deleted, so its items
# remain available as a historical snapshot, and a fresh "active" cart can
# be created for the client afterwards.
CART_STATUS_CHOICES = [
    ("active", "نشطة"),
    ("converted", "تم تحويلها إلى طلب"),
]


class Cart(models.Model):
    """A client's shopping cart of queued formations, pending checkout."""

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name="الزبون",
    )
    status = models.CharField(
        "الحالة",
        max_length=10,
        choices=CART_STATUS_CHOICES,
        default="active",
    )
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "سلة"
        verbose_name_plural = "السلال"
        constraints = [
            models.UniqueConstraint(
                fields=["client"],
                condition=models.Q(status="active"),
                name="unique_active_cart_per_client",
            ),
        ]

    def __str__(self):
        return f"سلة {self.client.display_name} — {self.get_status_display()}"

    @property
    def is_active(self):
        return self.status == "active"

    @property
    def items_count(self):
        return self.items.count()

    @classmethod
    def get_active_for_client(cls, client):
        """Return `client`'s active cart, creating an empty one on first use.
        The only place a `Cart` row should ever be fetched/created from, so
        the "one active cart per client" rule (enforced by the constraint
        above) is respected consistently everywhere (TODO 4.2/4.3)."""
        cart, _ = cls.objects.get_or_create(client=client, status="active")
        return cart

    @property
    def subtotal(self):
        """TODO 4.3 — sum of every line's `CartItem.line_total`, skipping
        lines that aren't priced yet (missing billing_basis, or an
        offering missing the corresponding group price). Returns None
        when nothing in the cart is priced, so the template can show a
        "not priced yet" note instead of a misleading 0. Same visibility
        note as `CartItem.line_total`: this is a raw figure, callers must
        still gate its display behind the Phase 3 VIP-only rule."""
        total = None
        for item in self.items.all():
            line = item.line_total
            if line is None:
                continue
            total = (total or 0) + line
        return total


class CartItem(models.Model):
    """A single queued formation line within a `Cart`.

    `billing_basis` and `trainer` are the VIP/enterprise group-pricing
    fields introduced in TODO 3.1/`BILLING_BASIS_CHOICES` — a non-VIP
    client's cart lines are expected to leave both blank/null (their
    Phase 5 path is "Request Quote": offering + participant_count only,
    no trainer, no price — see TODO 5.3). Choosing a trainer is only ever
    meant to be reachable for VIP carts; `clean()` below is a last-resort
    safety net, the actual enforcement belongs in the form/view layer
    (TODO 4.1/4.2/4.3), which must never render or accept a trainer choice
    for a non-VIP client's cart in the first place.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="السلة",
    )
    offering = models.ForeignKey(
        Offering,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="التخصص",
    )
    participant_count = models.PositiveSmallIntegerField(
        "عدد المشاركين",
        default=1,
        validators=[MinValueValidator(1)],
    )
    billing_basis = models.CharField(
        "أساس الفوترة",
        max_length=20,
        choices=BILLING_BASIS_CHOICES,
        blank=True,
        help_text="يُضبط فقط لسلال الزبائن VIP — يبقى فارغا لغير ذلك (مسار طلب عرض السعر).",
    )
    trainer = models.ForeignKey(
        Formateur,
        on_delete=models.SET_NULL,
        related_name="cart_items",
        null=True,
        blank=True,
        verbose_name="المكوّن (اختياري — VIP فقط)",
        help_text="لا يُعرض ولا يُسمح باختياره إلا في سلال الزبائن VIP.",
    )
    notes = models.TextField("ملاحظات", blank=True)
    created_at = models.DateTimeField("تاريخ الإضافة", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "عنصر في السلة"
        verbose_name_plural = "عناصر السلة"

    def __str__(self):
        return f"{self.offering.code} × {self.participant_count} — {self.cart}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.trainer_id and not self.cart.client.is_vip:
            raise ValidationError(
                "اختيار المكوّن متاح فقط ضمن سلال الزبائن VIP."
            )

    # --- pricing (TODO 4.3) --------------------------------------------
    # There is no stored "number of training days" anywhere on `Offering`
    # (`duration_months` only applies to the unrelated individual monthly
    # qualification path) or on `CartItem`, so a `per_day` line is priced
    # as the flat group rate `Offering.price_per_day` itself — consistent
    # with that field's help text ("فوترة جماعية... بالسعر لكل يوم تكوين")
    # describing an on-site session billed per day regardless of
    # headcount. Only `per_participant` scales with `participant_count`.
    # Both properties return None (never 0) when no price applies yet, so
    # templates can distinguish "not priced" from "free" and the caller
    # decides how to render that — this is purely a figure, not a
    # visibility rule: callers must still gate display behind the Phase 3
    # `can_view_price` (VIP-only) check themselves.
    @property
    def unit_price(self):
        if self.billing_basis == "per_participant":
            return self.offering.price_per_participant
        if self.billing_basis == "per_day":
            return self.offering.price_per_day
        return None

    @property
    def line_total(self):
        price = self.unit_price
        if price is None:
            return None
        if self.billing_basis == "per_participant":
            return price * self.participant_count
        return price


# --- Wishlist (TODO 4.4) -------------------------------------------------
# A much lighter bookmark than `CartItem`: just "I might book this later",
# no participant_count/billing_basis/trainer to configure yet. The
# "move to cart" action on the Wishlist page converts one into a real
# `CartItem` in the client's active cart (`Cart.get_active_for_client`,
# TODO 4.1) and drops the bookmark.
class WishlistItem(models.Model):
    """One offering a client has saved for later."""

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
        verbose_name="الزبون",
    )
    offering = models.ForeignKey(
        Offering,
        on_delete=models.CASCADE,
        related_name="wishlisted_by",
        verbose_name="التخصص",
    )
    created_at = models.DateTimeField("تاريخ الإضافة", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("client", "offering")
        verbose_name = "عنصر في قائمة الرغبات"
        verbose_name_plural = "قائمة الرغبات"

    def __str__(self):
        return f"{self.offering.code} — {self.client.display_name}"


# --- Proforma Invoice (TODO 5.2, VIP) ------------------------------------
# The persisted result of the "Request Proforma" checkout action (TODO 5.1)
# on a VIP client's cart: a frozen snapshot of the cart at submission time
# (so later edits to `Offering` pricing or `Formateur` records never change
# a document that has already been sent) plus the optional bon-de-commande
# upload. No PDF-generation library is used anywhere in this app (no
# ReportLab, WeasyPrint...): `get_absolute_url`/`enrollment:proforma_print`
# below points at a dedicated view that renders plain HTML with
# print-specific CSS (@media print rules) — the client's own browser
# handles "print" or "save as PDF", exactly like `Offering.fiche_technique_url`
# and `Formateur.cv_url` already do (see `fiche_technique_print`/
# `formateur_cv_print` above and `enrollment/documents/*.html`).
PROFORMA_STATUS_CHOICES = [
    ("pending", "قيد المراجعة"),
    ("confirmed", "مؤكدة"),
    ("cancelled", "ملغاة"),
]


def proforma_bon_de_commande_path(instance, filename):
    return f"proforma_invoices/{instance.client_id}/{filename}"


class ProformaInvoice(models.Model):
    """A VIP client's proforma request (TODO 5.1/5.2), with its cart lines
    frozen onto `ProformaInvoiceItem` rows at creation time. `reference` is
    a short human-readable number shown on the printable page and in
    'My Purchases'; it can't be filled in before the first save (it needs
    the auto `pk`), so `save()` below fills it in on first save only."""

    reference = models.CharField(
        "المرجع", max_length=30, unique=True, blank=True, editable=False
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="proforma_invoices",
        verbose_name="الزبون",
    )
    status = models.CharField(
        "الحالة",
        max_length=10,
        choices=PROFORMA_STATUS_CHOICES,
        default="pending",
    )
    bon_de_commande = models.FileField(
        "بون دي كوماند",
        upload_to=proforma_bon_de_commande_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png", "webp"])],
    )
    bon_de_commande_original_name = models.CharField(
        "الاسم الأصلي للملف", max_length=255, blank=True
    )
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "فاتورة أولية (بروفورما)"
        verbose_name_plural = "🧾 الفواتير الأولية (بروفورما)"

    def __str__(self):
        return self.reference or f"بروفورما #{self.pk}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.reference:
            self.reference = f"PRO-{self.created_at:%Y}-{self.pk:05d}"
            super().save(update_fields=["reference"])

    def get_absolute_url(self):
        return reverse("enrollment:proforma_print", args=[self.pk])

    @property
    def subtotal(self):
        """Same "None means not priced, not free" convention as
        `Cart.subtotal`/`CartItem.line_total` — still a raw figure, callers
        must gate its display behind the Phase 3 VIP-only rule themselves."""
        total = None
        for item in self.items.all():
            if item.line_total is None:
                continue
            total = (total or 0) + item.line_total
        return total


class ProformaInvoiceItem(models.Model):
    """One frozen cart line on a `ProformaInvoice`. `offering`/`trainer`
    stay as real foreign keys (so the printable page can still link back
    to them), but every display value that must never change after the
    fact — title, code, session, trainer name, billing basis, quantity,
    unit price, line total — is copied onto this row at creation time.
    `offering` uses PROTECT (unlike `CartItem.offering`'s CASCADE) since an
    Offering must never be deletable out from under an already-issued
    invoice line."""

    invoice = models.ForeignKey(
        ProformaInvoice,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="الفاتورة الأولية",
    )
    offering = models.ForeignKey(
        Offering,
        on_delete=models.PROTECT,
        related_name="proforma_items",
        verbose_name="التخصص",
    )
    offering_code = models.CharField("رمز التخصص", max_length=20)
    offering_title = models.CharField("عنوان التخصص", max_length=150)
    session_name = models.CharField("الدورة", max_length=120, blank=True)
    trainer = models.ForeignKey(
        Formateur,
        on_delete=models.SET_NULL,
        related_name="proforma_items",
        null=True,
        blank=True,
        verbose_name="المكوّن",
    )
    trainer_name = models.CharField("اسم المكوّن", max_length=150, blank=True)
    billing_basis = models.CharField(
        "أساس الفوترة", max_length=20, choices=BILLING_BASIS_CHOICES
    )
    participant_count = models.PositiveSmallIntegerField(
        "عدد المشاركين", default=1, validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(
        "سعر الوحدة (دج)", max_digits=10, decimal_places=2, null=True, blank=True
    )
    line_total = models.DecimalField(
        "المجموع (دج)", max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "بند في الفاتورة الأولية"
        verbose_name_plural = "بنود الفاتورة الأولية"

    def __str__(self):
        return f"{self.offering_code} × {self.participant_count} — {self.invoice}"

    @classmethod
    def snapshot_from_cart_item(cls, invoice, cart_item):
        """Build (unsaved) a frozen line from a live `CartItem` — the sole
        place this copy happens, so `ProformaInvoice` creation (TODO 5.2)
        stays consistent wherever it's triggered from."""
        return cls(
            invoice=invoice,
            offering=cart_item.offering,
            offering_code=cart_item.offering.code,
            offering_title=cart_item.offering.title,
            session_name=cart_item.offering.session.name,
            trainer=cart_item.trainer,
            trainer_name=cart_item.trainer.full_name if cart_item.trainer else "",
            billing_basis=cart_item.billing_basis,
            participant_count=cart_item.participant_count,
            unit_price=cart_item.unit_price,
            line_total=cart_item.line_total,
        )


# --- Quote Request (TODO 5.3, non-VIP) -----------------------------------
# The non-VIP counterpart to `ProformaInvoice` (TODO 5.1/5.2): a snapshot
# of the client's cart at submission time, but deliberately thinner — no
# `trainer`, no price, no bon-de-commande attachment, since none of those
# are ever shown or accepted on the non-VIP "Request Quote" action (only
# VIP carts carry a billing basis/trainer to begin with, see
# `CartItem`/Phase 4). Pricing is added later by an accountant per line
# (`CustomTariff`, Phase 6), hence `status` starting at "pending" and
# moving through "priced"/"approved" (TODO 6.3) rather than being fixed
# at creation like a VIP proforma.
QUOTE_STATUS_CHOICES = [
    ("pending", "قيد المراجعة"),
    ("priced", "تم التسعير"),
    ("approved", "معتمدة"),
    ("cancelled", "ملغاة"),
]


class QuoteRequest(models.Model):
    """A non-VIP client's 'Request Quote' checkout (TODO 5.3), with its
    cart lines frozen onto `QuoteRequestItem` rows at creation time. Same
    `reference` auto-numbering convention as `ProformaInvoice.reference`
    (see that model's docstring) but with its own "QUO-" prefix."""

    reference = models.CharField(
        "المرجع", max_length=30, unique=True, blank=True, editable=False
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="quote_requests",
        verbose_name="الزبون",
    )
    status = models.CharField(
        "الحالة",
        max_length=10,
        choices=QUOTE_STATUS_CHOICES,
        default="pending",
    )
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "طلب عرض سعر"
        verbose_name_plural = "📋 طلبات عروض الأسعار"

    def __str__(self):
        return self.reference or f"عرض سعر #{self.pk}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.reference:
            self.reference = f"QUO-{self.created_at:%Y}-{self.pk:05d}"
            super().save(update_fields=["reference"])

    @property
    def is_priced(self):
        """TODO 6.2 — True once every line carries a tariff (unit_price +
        billing_basis), i.e. the accountant has finished pricing this
        quote and it's ready to move to `status="priced"` (TODO 6.3)."""
        items = list(self.items.all())
        return bool(items) and all(item.is_priced for item in items)

    @property
    def subtotal(self):
        """Same "None means not priced, not free" convention as
        `Cart.subtotal`/`ProformaInvoice.subtotal` — a raw figure only;
        this quote's items have no VIP-only visibility rule of their own
        (the client only sees a price here once the accountant sets one),
        but callers rendering it elsewhere should still consider context."""
        total = None
        for item in self.items.all():
            if item.line_total is None:
                continue
            total = (total or 0) + item.line_total
        return total


class QuoteRequestItem(models.Model):
    """One frozen cart line on a `QuoteRequest` — offering + participant
    count only at creation time (TODO 5.3: "no trainer, no price").

    `unit_price`/`billing_basis` (TODO 6.2) are deliberately **not** set
    at creation — they start blank/null and are filled in later, per
    line, by an admin or accountant (see `enrollment.admin`'s
    `QuoteRequestItemInline`, restricted to the "Accountant" group's
    `change_quoterequestitem` permission from TODO 6.1). This is the
    "CustomTariff" the TODO describes, kept as plain fields on this model
    rather than a separate table since a tariff is always exactly
    one-per-line and never reused across quotes/lines."""

    quote = models.ForeignKey(
        QuoteRequest,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="طلب عرض السعر",
    )
    offering = models.ForeignKey(
        Offering,
        on_delete=models.PROTECT,
        related_name="quote_items",
        verbose_name="التخصص",
    )
    offering_code = models.CharField("رمز التخصص", max_length=20)
    offering_title = models.CharField("عنوان التخصص", max_length=150)
    session_name = models.CharField("الدورة", max_length=120, blank=True)
    participant_count = models.PositiveSmallIntegerField(
        "عدد المشاركين", default=1, validators=[MinValueValidator(1)]
    )
    billing_basis = models.CharField(
        "أساس الفوترة",
        max_length=20,
        choices=BILLING_BASIS_CHOICES,
        blank=True,
        help_text="يضبطه المحاسب/الإدارة عند التسعير — فارغ إلى حين ذلك.",
    )
    unit_price = models.DecimalField(
        "سعر الوحدة (دج)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="التعريفة المخصّصة لهذا البند (يضبطها المحاسب/الإدارة).",
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "بند في طلب عرض السعر"
        verbose_name_plural = "بنود طلب عرض السعر"

    def __str__(self):
        return f"{self.offering_code} × {self.participant_count} — {self.quote}"

    @classmethod
    def snapshot_from_cart_item(cls, quote, cart_item):
        """Build (unsaved) a frozen line from a live `CartItem` — mirrors
        `ProformaInvoiceItem.snapshot_from_cart_item` but drops the
        trainer/pricing fields, since those aren't known yet on the
        non-VIP path (TODO 5.3) — `unit_price`/`billing_basis` are filled
        in afterwards by the accountant (TODO 6.2)."""
        return cls(
            quote=quote,
            offering=cart_item.offering,
            offering_code=cart_item.offering.code,
            offering_title=cart_item.offering.title,
            session_name=cart_item.offering.session.name,
            participant_count=cart_item.participant_count,
        )

    # --- tariff (TODO 6.2) ----------------------------------------------
    # Same "per_day is a flat group rate, per_participant scales with
    # headcount" convention as `CartItem.line_total`, except here both
    # `billing_basis` and `unit_price` are the accountant's own tariff
    # entry for this line rather than derived from `Offering` — this is
    # exactly what lets it "override/define the price that VIP users
    # would otherwise see as the base price" per the TODO.
    @property
    def is_priced(self):
        return bool(self.billing_basis) and self.unit_price is not None

    @property
    def line_total(self):
        if not self.is_priced:
            return None
        if self.billing_basis == "per_participant":
            return self.unit_price * self.participant_count
        return self.unit_price


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
