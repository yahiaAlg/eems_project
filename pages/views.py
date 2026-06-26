from django.shortcuts import render
from django.views.decorators.cache import never_cache
from datetime import date

from .models import (
    SiteSettings, HeroStat, MissionCard, CarouselImage,
    Branch, Specialty, TrainingSession, SocialLink, InternalApp, NavLink,
    SiteVisitor,
)


@never_cache
def home(request):
    settings_obj = SiteSettings.load()
    today = date.today()
    context = {
        "settings": settings_obj,
        "hero_stats": HeroStat.objects.all(),
        "mission_cards": MissionCard.objects.all(),
        "carousel_images": CarouselImage.objects.filter(is_active=True),
        "branches": Branch.objects.filter(is_active=True),
        "sessions": TrainingSession.objects.filter(is_active=True),
        "social_links": SocialLink.objects.all(),
        "internal_apps": InternalApp.objects.all(),
        "nav_links": NavLink.objects.all(),
        "visitor_stats": {
            "today": SiteVisitor.objects.filter(date=today).count(),
            "month": SiteVisitor.objects.filter(date__year=today.year, date__month=today.month).count(),
            "total": SiteVisitor.objects.count(),
        },
    }
    return render(request, "pages/home.html", context)


@never_cache
def nomenclature(request):
    specialties = (
        Specialty.objects.select_related("branch")
        .order_by("branch__order", "code")
    )
    # Same row shape the original static page used: [code, name, branch_name, branch_code]
    # NOTE: keep this a plain Python list — it goes through the `json_script`
    # template filter, which serializes it itself. Pre-serializing it here
    # (e.g. with json.dumps) would double-encode it into a JSON *string*,
    # so `JSON.parse()` in the browser would yield a string back instead of
    # an array, and the table would silently render empty.
    data = [[s.code, s.name, s.branch.name_ar, s.branch.code] for s in specialties]
    context = {
        "settings": SiteSettings.load(),
        "branches": Branch.objects.filter(is_active=True),
        "total_count": specialties.count(),
        "specialties_data": data,
    }
    return render(request, "pages/nomenclature.html", context)
