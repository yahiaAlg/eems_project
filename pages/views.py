from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from datetime import date

from .forms import NewsletterForm
from .models import (
    SiteSettings, HeroStat, MissionCard, CarouselImage,
    Branch, Specialty, TrainingSession, SocialLink, InternalApp, NavLink,
    SiteVisitor, Partner, ProcessStep, Testimonial,
)


@never_cache
def home(request):
    settings_obj = SiteSettings.load()
    today = date.today()

    # Live counters instead of hardcoded numbers.
    from enrollment.models import Offering, Enrollment
    live_counters = {
        "branches": Branch.objects.filter(is_active=True).count(),
        "specialties": Specialty.objects.count(),
        "offerings": Offering.objects.filter(is_active=True).count(),
        "enrolled": Enrollment.objects.filter(status="accepted").count(),
    }
    featured_offerings = (
        Offering.objects.filter(is_active=True, is_featured=True, session__is_active=True)
        .select_related("session")[:6]
    )

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
        "live_counters": live_counters,
        "featured_offerings": featured_offerings,
        "partners": Partner.objects.filter(is_active=True),
        "process_steps": ProcessStep.objects.all(),
        "testimonials": Testimonial.objects.filter(is_active=True),
        "newsletter_form": NewsletterForm(),
    }
    return render(request, "pages/home.html", context)


@never_cache
def newsletter_subscribe(request):
    if request.method == "POST":
        form = NewsletterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "شكرا لاشتراكك في نشرتنا الإخبارية!")
        else:
            messages.error(request, "الرجاء إدخال بريد إلكتروني صالح.")
    return redirect(request.META.get("HTTP_REFERER") or "pages:home")

@never_cache
def robots(request):
    return render(request, "pages/robots.txt", context={})
    
    
    
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
