from django.db import models
from django.conf import settings
from django.urls import reverse


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


class Offering(models.Model):
    """A specialty as taught within a given session — carries pricing/seat data."""

    session = models.ForeignKey(
        FormationSession, on_delete=models.CASCADE, related_name="offerings",
        verbose_name="الدورة",
    )
    specialty = models.ForeignKey(
        "pages.Specialty", on_delete=models.PROTECT, related_name="offerings",
        null=True, blank=True, verbose_name="التخصص (مدونة الشعب)",
    )
    code = models.CharField("رمز الاختصاص", max_length=20, help_text="مثال: TAG0701")
    title = models.CharField("عنوان التخصص", max_length=150)
    branch_label = models.CharField("الشعبة", max_length=100, blank=True)
    qualification_level = models.PositiveSmallIntegerField(
        "مستوى التأهيل", choices=QUALIFICATION_LEVELS, null=True, blank=True,
    )
    certificate_type = models.CharField(
        "الشهادة المسلمة", max_length=20, choices=CERT_TYPES, blank=True,
    )
    entry_level = models.CharField(
        "مستوى الدخول", max_length=20, choices=ENTRY_LEVELS, blank=True,
    )
    duration_months = models.PositiveSmallIntegerField("مدة التكوين (أشهر)")
    monthly_fee = models.DecimalField(
        "القيمة الشهرية (دج)", max_digits=10, decimal_places=2, null=True, blank=True,
    )
    total_fee = models.DecimalField(
        "القيمة الإجمالية (دج)", max_digits=10, decimal_places=2, null=True, blank=True,
    )
    seats_available = models.PositiveSmallIntegerField("قدرة الاستيعاب", default=0)
    description = models.TextField("تعريف التخصص", blank=True)
    main_tasks = models.TextField(
        "المهام الأساسية", blank=True, help_text="سطر واحد لكل مهمة",
    )
    image = models.ImageField(
        "صورة (ملف مرفوع)", upload_to="enrollment/offerings/", blank=True, null=True,
    )
    poster_url = models.URLField(
        "رابط صورة الملصق (بطاقة العرض)", blank=True,
        help_text="يُستعمل إن لم يتم رفع صورة أعلاه. يمكن استعمال رابط من خدمة صور مجانية.",
    )
    background_url = models.URLField(
        "رابط صورة الخلفية (صفحة التفاصيل)", blank=True,
        help_text="تُعرض كخلفية لرأس صفحة التخصص.",
    )
    video_url = models.URLField(
        "رابط فيديو تعريفي (YouTube)", blank=True,
        help_text="ألصق رابط فيديو يوتيوب ترويجي لهذا التخصص (اختياري).",
    )
    is_active = models.BooleanField("معروضة على الموقع", default=True)
    is_featured = models.BooleanField("تخصص مميز (يظهر في الصفحة الرئيسية)", default=False)
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
        return self.enrollments.filter(status__in=["pending", "contacted", "accepted"]).count()

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
    ("waitlisted", "قائمة انتظار"),
    ("rejected", "مرفوض"),
]

GENDER_CHOICES = [("m", "ذكر"), ("f", "أنثى")]

CLIENT_TYPE_CHOICES = [
    ("individual", "فرد (خاص)"),
    ("enterprise", "مؤسسة"),
]


class Client(models.Model):
    """The subscriber: either a private individual, or an enterprise sending participants."""

    client_type = models.CharField(
        "نوع الزبون", max_length=20, choices=CLIENT_TYPE_CHOICES, default="individual",
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
    trade_register_number = models.CharField("رقم السجل التجاري", max_length=60, blank=True)
    sector = models.CharField("قطاع النشاط", max_length=120, blank=True)
    responsible_name = models.CharField(
        "الشخص المسؤول عن التنسيق", max_length=150, blank=True,
    )
    responsible_position = models.CharField("منصب المسؤول", max_length=100, blank=True)

    source = models.CharField(
        "مصدر التسجيل", max_length=20, choices=SOURCE_CHOICES, default="web",
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
        Client, on_delete=models.CASCADE, related_name="participants",
        verbose_name="الزبون",
    )
    full_name = models.CharField("الاسم واللقب", max_length=150)
    phone = models.CharField("رقم الهاتف", max_length=20, blank=True)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    birth_date = models.DateField("تاريخ الميلاد", null=True, blank=True)
    gender = models.CharField("الجنس", max_length=1, choices=GENDER_CHOICES, blank=True)
    education_level = models.CharField("المستوى الدراسي", max_length=100, blank=True)
    position = models.CharField(
        "المنصب داخل المؤسسة", max_length=100, blank=True,
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
        Client, on_delete=models.CASCADE, related_name="enrollments",
        verbose_name="الزبون",
    )
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="enrollments",
        verbose_name="المشارك",
    )
    offering = models.ForeignKey(
        Offering, on_delete=models.CASCADE, related_name="enrollments",
        verbose_name="التخصص المطلوب",
    )
    motivation = models.TextField("ملاحظات / دافع الترشح", blank=True)
    status = models.CharField(
        "الحالة", max_length=20, choices=STATUS_CHOICES, default="pending",
    )
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="عولجت من طرف",
    )
    created_at = models.DateTimeField("تاريخ التسجيل", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("participant", "offering")
        verbose_name = "تسجيل"
        verbose_name_plural = "التسجيلات"

    def __str__(self):
        return f"{self.participant} → {self.offering.code}"


class EnrollmentNote(models.Model):
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
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
        Offering, on_delete=models.CASCADE, related_name="comments",
        verbose_name="التخصص",
    )
    name = models.CharField("الاسم", max_length=120)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    rating = models.PositiveSmallIntegerField(
        "التقييم", choices=RATING_CHOICES, default=5,
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
        Offering, on_delete=models.CASCADE, related_name="enquiries",
        verbose_name="التخصص", null=True, blank=True,
    )
    name = models.CharField("الاسم", max_length=120)
    phone = models.CharField("الهاتف", max_length=20, blank=True)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    question = models.TextField("السؤال / الاستفسار")
    answer = models.TextField("الرد", blank=True)
    is_answered = models.BooleanField("تمت الإجابة", default=False)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
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
