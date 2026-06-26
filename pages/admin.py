from django.contrib import admin
from .models import (
    SiteSettings, HeroStat, MissionCard, CarouselImage,
    Branch, Specialty, TrainingSession,
    SocialLink, InternalApp, NavLink,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton admin: always edits the same row, no add/delete."""
    fieldsets = (
        ("الهوية", {"fields": ("site_name", "site_full_name", "logo", "browser_title")}),
        ("الهيرو", {"fields": (
            "hero_badge_text", "hero_title_line1", "hero_title_line2", "hero_title_accent",
            "hero_description", "hero_image", "hero_cta_primary_text", "hero_cta_primary_url",
            "hero_cta_secondary_text", "hero_cta_secondary_url",
        )}),
        ("التكوينات (مقدمة القسم)", {"fields": ("formations_label", "formations_title", "formations_description")}),
        ("الفيديو", {"fields": ("video_label", "video_title", "video_description", "video_youtube_embed_url")}),
        ("المعرض", {"fields": ("gallery_label", "gallery_title")}),
        ("الموقع/الخريطة", {"fields": ("map_label", "map_title", "map_description", "map_embed_url")}),
        ("الاتصال", {"fields": ("address", "phone", "email", "working_hours")}),
        ("التذييل", {"fields": ("footer_description", "footer_copyright", "footer_location_text")}),
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
    list_display = ("code", "name_ar", "name_fr", "color", "order", "is_active", "specialty_count")
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
    list_display = ("title", "start_date", "duration_text", "seats", "status", "is_active", "order")
    list_editable = ("order", "is_active")
    list_filter = ("status", "is_active")
    date_hierarchy = "start_date"


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("platform", "url", "order")
    list_editable = ("order",)


@admin.register(InternalApp)
class InternalAppAdmin(admin.ModelAdmin):
    list_display = ("title", "subtitle", "url", "color", "show_in_navbar", "show_in_hero", "show_in_footer", "order")
    list_editable = ("order",)


@admin.register(NavLink)
class NavLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "url", "order")
    list_editable = ("order",)
