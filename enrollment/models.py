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
        "صورة", upload_to="enrollment/offerings/", blank=True, null=True,
    )
    is_active = models.BooleanField("معروضة على الموقع", default=True)
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

    def get_absolute_url(self):
        return reverse("enrollment:detail", args=[self.session.slug, self.code])


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
