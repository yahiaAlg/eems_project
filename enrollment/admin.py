from datetime import timedelta

from django.contrib import admin
from django.db.models import Count
from django.shortcuts import render
from django.urls import path
from django.utils import timezone

from django.utils.html import format_html

from .models import (
    Client,
    Enrollment,
    EnrollmentNote,
    Formateur,
    FormateurCareerEntry,
    FormateurCertificate,
    FormationSession,
    Offering,
    OfferingAttachment,
    OfferingImage,
    Participant,
)


class OfferingImageInline(admin.TabularInline):
    model = OfferingImage
    extra = 1
    fields = ("image", "thumb", "caption", "order")
    readonly_fields = ("thumb",)

    def thumb(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="height:56px;border-radius:6px;">', obj.image.url
            )
        return "—"

    thumb.short_description = "معاينة"


class OfferingAttachmentInline(admin.TabularInline):
    model = OfferingAttachment
    extra = 1
    fields = ("file", "title", "kind_display", "order")
    readonly_fields = ("kind_display",)
    verbose_name = "مرفق إضافي"
    verbose_name_plural = "📎 مرفقات إضافية (PDF / Word / صور، اختياري) — بالإضافة إلى الملف التقني الرسمية أعلاه"

    def kind_display(self, obj):
        if not obj.pk or not obj.file:
            return "—"
        labels = {"pdf": "PDF", "doc": "Word", "image": "صورة", "file": "ملف"}
        icons = {"pdf": "📄", "doc": "📝", "image": "🖼️", "file": "📎"}
        return format_html(
            "{} {}", icons.get(obj.kind, "📎"), labels.get(obj.kind, "ملف")
        )

    kind_display.short_description = "النوع"


class FormateurCertificateInline(admin.TabularInline):
    model = FormateurCertificate
    extra = 0
    fields = ("file", "title", "issuer", "date_obtained", "order")
    verbose_name = "شهادة / اعتماد"
    verbose_name_plural = "🎓 الشهادات والاعتمادات (PDF أو صور، اختياري)"


class FormateurCareerEntryInline(admin.TabularInline):
    model = FormateurCareerEntry
    extra = 0
    fields = (
        "role_title",
        "organization",
        "start_year",
        "end_year",
        "description",
        "order",
    )
    verbose_name = "محطة مهنية"
    verbose_name_plural = "🧭 المسار المهني (اختياري)"


@admin.register(Formateur)
class FormateurAdmin(admin.ModelAdmin):
    list_display = (
        "thumb",
        "full_name",
        "title",
        "years_experience",
        "offering_count",
        "is_active",
        "order",
    )
    list_editable = ("is_active", "order")
    search_fields = ("full_name", "title")
    prepopulated_fields = {"slug": ("full_name",)}
    inlines = [FormateurCareerEntryInline, FormateurCertificateInline]
    fieldsets = (
        (
            "الهوية",
            {"fields": ("full_name", "slug", "title", "photo", "years_experience")},
        ),
        ("النبذة والتواصل", {"fields": ("bio", "email", "linkedin_url")}),
        (
            "السيرة الذاتية (CV)",
            {
                "fields": ("cv_mode", "cv_file"),
                "description": (
                    "توليد تلقائي (الافتراضي): يُبنى نموذج CV قابل للطباعة تلقائيا من بيانات "
                    "هذه الصفحة (لا حاجة لرفع أي ملف). مخصص: يُستبدل بالملف المرفوع في الحقل أدناه "
                    "(PDF / Word / صورة)."
                ),
            },
        ),
        ("الحالة", {"fields": ("is_active", "order")}),
    )

    def offering_count(self, obj):
        return obj.offerings.count()

    offering_count.short_description = "عدد التكوينات"

    def thumb(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">',
                obj.photo.url,
            )
        return "—"

    thumb.short_description = ""


@admin.register(FormationSession)
class FormationSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "registration_deadline", "is_active", "order")
    list_editable = ("is_active", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Offering)
class OfferingAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "session",
        "qualification_level",
        "duration_months",
        "monthly_fee",
        "seats_display",
        "is_active",
        "is_featured",
        "order",
    )
    list_editable = ("is_active", "is_featured", "order")
    list_filter = ("session", "qualification_level", "is_active", "is_featured")
    search_fields = ("code", "title")
    autocomplete_fields = ("specialty", "formateur")
    inlines = [OfferingImageInline, OfferingAttachmentInline]
    fieldsets = (
        (
            "معلومات عامة",
            {
                "fields": (
                    "session",
                    "specialty",
                    "formateur",
                    "code",
                    "title",
                    "branch_label",
                    "qualification_level",
                    "certificate_type",
                    "entry_level",
                    "duration_months",
                    "monthly_fee",
                    "total_fee",
                    "seats_available",
                )
            },
        ),
        ("المحتوى", {"fields": ("description", "main_tasks")}),
        (
            "📋 الملف التقني — تفاصيل إضافية",
            {
                "fields": ("objectives", "program_outline", "prerequisites"),
                "description": "حقول اختيارية، سطر واحد لكل عنصر — تُعرض ضمن الملف التقني إن مُلئت.",
            },
        ),
        (
            "📄 الملف التقني — نمط الوثيقة",
            {
                "fields": ("fiche_technique_mode", "fiche_technique_file"),
                "description": (
                    "توليد تلقائي (الافتراضي): تُبنى فيشة تقنية قابلة للطباعة تلقائيا من الحقول "
                    "أعلاه (لا حاجة لرفع أي ملف). مخصص: تُستبدل بالملف المرفوع في الحقل أدناه "
                    "(PDF / Word / صورة)."
                ),
            },
        ),
        (
            "الوسائط (صور وفيديو)",
            {
                "fields": ("image", "poster_url", "background_url", "video_url"),
                "description": (
                    "الصورة المرفوعة لها الأولوية دائما. إن لم تُرفع صورة، يمكن "
                    "الاكتفاء بروابط poster_url / background_url من أي خدمة صور "
                    "مجانية (مثل picsum.photos أو unsplash). في غياب كل شيء تُولّد "
                    "صورة عشوائية تلقائيا حسب رمز التخصص."
                ),
            },
        ),
        ("العرض على الموقع", {"fields": ("is_active", "is_featured", "order")}),
    )

    def seats_display(self, obj):
        return f"{obj.seats_taken} / {obj.seats_available} ({obj.fill_rate}%)"

    seats_display.short_description = "المقاعد المشغولة"


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    fields = ("full_name", "phone", "email", "position")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "client_type",
        "phone",
        "email",
        "wilaya",
        "participant_count",
        "enrollment_count",
        "source",
        "created_at",
    )
    list_filter = ("client_type", "source", "wilaya")
    search_fields = (
        "full_name",
        "company_name",
        "phone",
        "email",
        "trade_register_number",
    )
    date_hierarchy = "created_at"
    inlines = [ParticipantInline]

    fieldsets = (
        ("نوع الزبون", {"fields": ("client_type", "source")}),
        ("معلومات الاتصال", {"fields": ("phone", "email", "wilaya", "address")}),
        (
            "بيانات الفرد",
            {
                "fields": ("full_name", "birth_date", "gender", "education_level"),
                "description": "تُملأ فقط عندما يكون نوع الزبون «فرد (خاص)».",
            },
        ),
        (
            "بيانات المؤسسة",
            {
                "fields": (
                    "company_name",
                    "trade_register_number",
                    "sector",
                    "responsible_name",
                    "responsible_position",
                ),
                "description": "تُملأ فقط عندما يكون نوع الزبون «مؤسسة».",
            },
        ),
    )

    def participant_count(self, obj):
        return obj.participants.count()

    participant_count.short_description = "عدد المشاركين"

    def enrollment_count(self, obj):
        return obj.enrollments.count()

    enrollment_count.short_description = "عدد التسجيلات"


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("full_name", "client", "phone", "position")
    list_filter = ("client__client_type",)
    search_fields = (
        "full_name",
        "phone",
        "email",
        "client__company_name",
        "client__full_name",
    )
    autocomplete_fields = ("client",)


class EnrollmentNoteInline(admin.TabularInline):
    model = EnrollmentNote
    extra = 0
    readonly_fields = ("author", "created_at")
    fields = ("text", "author", "created_at")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "participant",
        "client_type_display",
        "client_link",
        "offering",
        "status",
        "created_at",
    )
    list_editable = ("status",)
    list_filter = (
        "status",
        "client__client_type",
        "client__source",
        "offering__session",
        "offering",
    )
    search_fields = (
        "participant__full_name",
        "participant__phone",
        "client__full_name",
        "client__company_name",
        "client__phone",
    )
    date_hierarchy = "created_at"
    autocomplete_fields = ("client", "participant", "offering")
    inlines = [EnrollmentNoteInline]
    change_list_template = "admin/enrollment/enrollment_changelist.html"
    actions = ["mark_accepted", "mark_rejected", "mark_contacted"]

    def client_type_display(self, obj):
        return obj.client.get_client_type_display()

    client_type_display.short_description = "نوع الزبون"

    def client_link(self, obj):
        return obj.client.display_name

    client_link.short_description = "الزبون"

    def changelist_view(self, request, extra_context=None):
        today = timezone.now().date()
        qs = Enrollment.objects.all()
        extra_context = extra_context or {}
        extra_context.update(
            enr_today=qs.filter(created_at__date=today).count(),
            enr_month=qs.filter(
                created_at__year=today.year, created_at__month=today.month
            ).count(),
            enr_total=qs.count(),
            enr_pending=qs.filter(status="pending").count(),
        )
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        custom = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="enrollment_enrollment_dashboard",
            ),
        ]
        return custom + super().get_urls()

    def dashboard_view(self, request):
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        qs = Enrollment.objects.all()
        clients = Client.objects.all()

        by_status = list(qs.values("status").annotate(count=Count("id")).order_by())
        by_source = list(
            clients.values("source").annotate(count=Count("id")).order_by()
        )
        by_client_type = list(
            clients.values("client_type").annotate(count=Count("id")).order_by()
        )
        by_offering = list(
            qs.values("offering__code", "offering__title")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        daily_last_week = list(
            qs.filter(created_at__date__gte=week_ago)
            .values("created_at__date")
            .annotate(count=Count("id"))
            .order_by("created_at__date")
        )

        context = dict(
            self.admin_site.each_context(request),
            title="لوحة إحصائيات التسجيلات",
            total=qs.count(),
            today_count=qs.filter(created_at__date=today).count(),
            month_count=qs.filter(
                created_at__year=today.year, created_at__month=today.month
            ).count(),
            pending_count=qs.filter(status="pending").count(),
            enterprise_count=clients.filter(client_type="enterprise").count(),
            individual_count=clients.filter(client_type="individual").count(),
            by_status=by_status,
            by_source=by_source,
            by_client_type=by_client_type,
            by_offering=by_offering,
            daily_last_week=daily_last_week,
            offerings=Offering.objects.filter(is_active=True).select_related("session"),
        )
        return render(request, "admin/enrollment/dashboard.html", context)

    @admin.action(description="وضع الحالة: مقبول")
    def mark_accepted(self, request, queryset):
        queryset.update(status="accepted")

    @admin.action(description="وضع الحالة: مرفوض")
    def mark_rejected(self, request, queryset):
        queryset.update(status="rejected")

    @admin.action(description="وضع الحالة: تم التواصل")
    def mark_contacted(self, request, queryset):
        queryset.update(status="contacted")


# Add this import to the top of enrollment/admin.py:
#   from .models import Comment, Enquiry
#
# Then append the two ModelAdmins below to enrollment/admin.py.

from django.contrib import admin

from .models import Comment, Enquiry


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("name", "offering", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "offering__session")
    search_fields = ("name", "email", "text", "offering__code", "offering__title")
    list_editable = ("is_approved",)
    autocomplete_fields = ("offering",)
    actions = ["approve_comments", "unapprove_comments"]

    @admin.action(description="✔ الموافقة على التعليقات المحددة")
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description="✘ إلغاء الموافقة على التعليقات المحددة")
    def unapprove_comments(self, request, queryset):
        queryset.update(is_approved=False)


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "offering", "phone", "is_answered", "created_at")
    list_filter = ("is_answered", "offering__session")
    search_fields = ("name", "email", "phone", "question", "offering__code")
    fields = (
        "name",
        "phone",
        "email",
        "offering",
        "question",
        "answer",
        "is_answered",
        "answered_by",
        "created_at",
        "answered_at",
    )
    readonly_fields = ("created_at",)

    def save_model(self, request, obj, form, change):
        from django.utils import timezone

        if obj.answer and not obj.answered_at:
            obj.is_answered = True
            obj.answered_at = timezone.now()
            obj.answered_by = request.user
        super().save_model(request, obj, form, change)
