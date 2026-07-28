from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import redirect, render
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from .models import (
    SiteSettings,
    HeroStat,
    MissionCard,
    CarouselImage,
    Branch,
    Specialty,
    TrainingSession,
    SocialLink,
    InternalApp,
    NavLink,
    SiteVisitor,
    Partner,
    ProcessStep,
    Testimonial,
    NewsletterSubscriber,
    AboutPage,
    AboutValue,
    Milestone,
    FAQCategory,
    FAQItem,
    ContactPageSettings,
    ContactMessage,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton admin: always edits the same row, no add/delete."""

    fieldsets = (
        (
            "الهوية",
            {"fields": ("site_name", "site_full_name", "logo", "browser_title")},
        ),
        (
            "الهيرو",
            {
                "fields": (
                    "hero_badge_text",
                    "hero_title_line1",
                    "hero_title_line2",
                    "hero_title_accent",
                    "hero_description",
                    "hero_image",
                    "hero_cta_primary_text",
                    "hero_cta_primary_url",
                    "hero_cta_secondary_text",
                    "hero_cta_secondary_url",
                )
            },
        ),
        (
            "التكوينات (مقدمة القسم)",
            {
                "fields": (
                    "formations_label",
                    "formations_title",
                    "formations_description",
                )
            },
        ),
        (
            "الفيديو",
            {
                "fields": (
                    "video_label",
                    "video_title",
                    "video_description",
                    "video_youtube_embed_url",
                )
            },
        ),
        ("المعرض", {"fields": ("gallery_label", "gallery_title")}),
        (
            "الموقع/الخريطة",
            {"fields": ("map_label", "map_title", "map_description", "map_embed_url")},
        ),
        ("الاتصال", {"fields": ("address", "phone", "email", "working_hours")}),
        (
            "التذييل",
            {
                "fields": (
                    "footer_description",
                    "footer_copyright",
                    "footer_location_text",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.load()
        from django.shortcuts import redirect

        return redirect("admin:pages_sitesettings_change", obj.pk)


@admin.register(HeroStat)
class HeroStatAdmin(admin.ModelAdmin):
    list_display = ("value", "label", "order")
    list_editable = ("order",)


@admin.register(MissionCard)
class MissionCardAdmin(admin.ModelAdmin):
    list_display = ("title", "color", "icon_class", "order")
    list_editable = ("order",)


@admin.register(CarouselImage)
class CarouselImageAdmin(admin.ModelAdmin):
    list_display = ("caption", "image", "order", "is_active")
    list_editable = ("order", "is_active")


class SpecialtyInline(admin.TabularInline):
    model = Specialty
    extra = 1
    fields = ("code", "name")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name_ar",
        "name_fr",
        "color",
        "order",
        "is_active",
        "specialty_count",
    )
    list_editable = ("order", "is_active")
    search_fields = ("code", "name_ar", "name_fr")
    inlines = [SpecialtyInline]

    def specialty_count(self, obj):
        return obj.specialties.count()

    specialty_count.short_description = "عدد التخصصات"


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "branch")
    list_filter = ("branch",)
    search_fields = ("code", "name")
    autocomplete_fields = ("branch",)


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "start_date",
        "duration_text",
        "seats",
        "status",
        "is_active",
        "order",
    )
    list_editable = ("order", "is_active")
    list_filter = ("status", "is_active")
    date_hierarchy = "start_date"


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("platform", "url", "order")
    list_editable = ("order",)


@admin.register(InternalApp)
class InternalAppAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subtitle",
        "url",
        "color",
        "show_in_navbar",
        "show_in_hero",
        "show_in_footer",
        "order",
    )
    list_editable = ("order",)


@admin.register(NavLink)
class NavLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "url", "order")
    list_editable = ("order",)


@admin.register(SiteVisitor)
class SiteVisitorAdmin(admin.ModelAdmin):
    list_display = ("date", "ip_hash_short")
    date_hierarchy = "date"
    change_list_template = "admin/pages/sitevisitor/change_list.html"

    def ip_hash_short(self, obj):
        return obj.ip_hash

    ip_hash_short.short_description = "IP (مجهول)"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from datetime import date

        today = date.today()
        extra_context = extra_context or {}
        extra_context["visitor_today"] = SiteVisitor.objects.filter(date=today).count()
        extra_context["visitor_month"] = SiteVisitor.objects.filter(
            date__year=today.year, date__month=today.month
        ).count()
        extra_context["visitor_total"] = SiteVisitor.objects.count()
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = ("title", "icon_class", "order")
    list_editable = ("order",)


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at")
    search_fields = ("email",)

    def has_add_permission(self, request):
        return False


# ──────────────────────────────────────────────────────────────────
#  About page
# ──────────────────────────────────────────────────────────────────
@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    fieldsets = (
        ("الهيرو", {"fields": ("hero_label", "hero_title", "hero_description", "hero_image")}),
        ("قصتنا", {"fields": ("story_label", "story_title", "story_body", "story_image")}),
        ("القيم (مقدمة القسم)", {"fields": ("values_label", "values_title")}),
        ("المسار الزمني (مقدمة القسم)", {"fields": ("timeline_label", "timeline_title")}),
    )

    def has_add_permission(self, request):
        return not AboutPage.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = AboutPage.load()
        return redirect("admin:pages_aboutpage_change", obj.pk)


@admin.register(AboutValue)
class AboutValueAdmin(admin.ModelAdmin):
    list_display = ("title", "icon_class", "order")
    list_editable = ("order",)


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("year", "title", "order")
    list_editable = ("order",)


# ──────────────────────────────────────────────────────────────────
#  FAQ
# ──────────────────────────────────────────────────────────────────
class FAQItemInline(admin.TabularInline):
    model = FAQItem
    extra = 1
    fields = ("question", "answer", "order", "is_active")


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "item_count")
    list_editable = ("order",)
    inlines = [FAQItemInline]

    def item_count(self, obj):
        return obj.items.count()

    item_count.short_description = "عدد الأسئلة"


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "order", "is_active")
    list_filter = ("category", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("question", "answer")


# ──────────────────────────────────────────────────────────────────
#  Contact
# ──────────────────────────────────────────────────────────────────
@admin.register(ContactPageSettings)
class ContactPageSettingsAdmin(admin.ModelAdmin):
    fields = ("label", "title", "description")

    def has_add_permission(self, request):
        return not ContactPageSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = ContactPageSettings.load()
        return redirect("admin:pages_contactpagesettings_change", obj.pk)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "status_badge", "created_at")
    list_filter = ("status", "subject", "created_at")
    search_fields = ("name", "email", "message")
    readonly_fields = ("name", "email", "phone", "subject", "message", "created_at")
    actions = ["mark_as_read", "mark_as_replied"]
    date_hierarchy = "created_at"

    def status_badge(self, obj):
        colors = {"new": "#f59e0b", "read": "#3b82f6", "replied": "#10b981"}
        return format_html(
            '<span style="background:{}22;color:{};padding:2px 10px;border-radius:100px;'
            'font-size:12px;font-weight:700;">{}</span>',
            colors.get(obj.status, "#94a3b8"),
            colors.get(obj.status, "#64748b"),
            obj.get_status_display(),
        )

    status_badge.short_description = "الحالة"

    def mark_as_read(self, request, queryset):
        queryset.update(status=ContactMessage.STATUS_READ)

    mark_as_read.short_description = "وضع علامة: مقروءة"

    def mark_as_replied(self, request, queryset):
        queryset.update(status=ContactMessage.STATUS_REPLIED)

    mark_as_replied.short_description = "وضع علامة: تم الرد"

    def has_add_permission(self, request):
        return False


# ──────────────────────────────────────────────────────────────────
#  User management — nicer columns/filters on top of Django's built-in
#  auth.User admin (already registered by django.contrib.auth).
# ──────────────────────────────────────────────────────────────────
User = get_user_model()
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username", "email", "first_name", "last_name",
        "is_staff", "is_active", "last_login", "date_joined",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("-date_joined",)


# ──────────────────────────────────────────────────────────────────
#  Global dashboard — stats & analytics across the whole site
#  (visitors, contact messages, newsletter growth, enrollments, users)
#  Attached to the SiteSettings admin (the site's natural settings hub).
# ──────────────────────────────────────────────────────────────────
_orig_get_urls = SiteSettingsAdmin.get_urls


def _dashboard_get_urls(self):
    custom = [
        path(
            "dashboard/",
            self.admin_site.admin_view(_site_dashboard_view),
            name="pages_site_dashboard",
        ),
    ]
    return custom + _orig_get_urls(self)


SiteSettingsAdmin.get_urls = _dashboard_get_urls


def _site_dashboard_view(request):
    from enrollment.models import Enrollment, Client

    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=29)

    visitors_qs = SiteVisitor.objects.filter(date__gte=thirty_days_ago)
    visitors_daily = list(
        visitors_qs.values("date").annotate(count=Count("id")).order_by("date")
    )

    newsletter_qs = NewsletterSubscriber.objects.filter(
        created_at__date__gte=thirty_days_ago
    )
    newsletter_daily = list(
        newsletter_qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    contact_by_status = list(
        ContactMessage.objects.values("status").annotate(count=Count("id")).order_by()
    )
    contact_by_subject = list(
        ContactMessage.objects.values("subject").annotate(count=Count("id")).order_by("-count")
    )

    enrollment_by_status = list(
        Enrollment.objects.values("status").annotate(count=Count("id")).order_by()
    )

    users_qs = User.objects.all()

    context = dict(
        admin.site.each_context(request),
        title="لوحة الإحصائيات والتحليلات",
        # KPI cards
        visitors_today=SiteVisitor.objects.filter(date=today).count(),
        visitors_month=SiteVisitor.objects.filter(
            date__year=today.year, date__month=today.month
        ).count(),
        visitors_total=SiteVisitor.objects.count(),
        newsletter_total=NewsletterSubscriber.objects.count(),
        contact_new=ContactMessage.objects.filter(status="new").count(),
        contact_total=ContactMessage.objects.count(),
        enrollments_total=Enrollment.objects.count(),
        enrollments_pending=Enrollment.objects.filter(status="pending").count(),
        users_total=users_qs.count(),
        users_staff=users_qs.filter(is_staff=True).count(),
        users_active=users_qs.filter(is_active=True).count(),
        clients_total=Client.objects.count(),
        # Chart data (JSON-serialisable lists of dicts)
        visitors_daily=visitors_daily,
        newsletter_daily=newsletter_daily,
        contact_by_status=contact_by_status,
        contact_by_subject=contact_by_subject,
        enrollment_by_status=enrollment_by_status,
        recent_users=users_qs.order_by("-date_joined")[:8],
        recent_messages=ContactMessage.objects.all()[:8],
    )
    return render(request, "admin/pages/dashboard.html", context)
