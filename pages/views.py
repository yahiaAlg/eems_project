from django.shortcuts import render

from .models import (
    SiteSettings, HeroStat, MissionCard, CarouselImage,
    Branch, Specialty, TrainingSession, SocialLink, InternalApp, NavLink,
)


def home(request):
    settings_obj = SiteSettings.load()
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
    }
    return render(request, "pages/home.html", context)


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
