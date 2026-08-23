from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from datetime import date

from .forms import NewsletterForm, ContactForm
from .emails import send_branded_mail
from .models import (
    SiteSettings, HeroStat, MissionCard, CarouselImage,
    Branch, Specialty, TrainingSession, SocialLink, InternalApp, NavLink,
    SiteVisitor, Partner, ProcessStep, Testimonial,
    AboutPage, AboutValue, Milestone,
    FAQCategory,
    ContactPageSettings, ContactMessage,
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
            subscriber = form.save()
            send_branded_mail(
                template="emails/newsletter_confirmation.html",
                subject="مرحبا بك في نشرة إيمس الإخبارية",
                to=[subscriber.email],
                context={"email": subscriber.email},
            )
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
    # Row shape: [code, name, branch_name, branch_code, branch_id]. branch_id
    # is what the catalog's ?branch= filter expects (Branch.pk), branch_code
    # only drives the #ANCHOR deep-link below.
    # NOTE: keep this a plain Python list — it goes through the `json_script`
    # template filter, which serializes it itself. Pre-serializing it here
    # (e.g. with json.dumps) would double-encode it into a JSON *string*,
    # so `JSON.parse()` in the browser would yield a string back instead of
    # an array, and the table would silently render empty.
    data = [
        [s.code, s.name, s.branch.name_ar, s.branch.code, s.branch_id]
        for s in specialties
    ]
    context = {
        "settings": SiteSettings.load(),
        "branches": Branch.objects.filter(is_active=True),
        "total_count": specialties.count(),
        "specialties_data": data,
        "social_links": SocialLink.objects.all(),
        "internal_apps": InternalApp.objects.all(),
        "nav_links": NavLink.objects.all(),
        "newsletter_form": NewsletterForm(),
        "visitor_stats": _visitor_stats(),
    }
    return render(request, "pages/nomenclature.html", context)


@never_cache
def about(request):
    context = {
        "settings": SiteSettings.load(),
        "about": AboutPage.load(),
        "values": AboutValue.objects.all(),
        "milestones": Milestone.objects.all(),
        "mission_cards": MissionCard.objects.all(),
        "social_links": SocialLink.objects.all(),
        "internal_apps": InternalApp.objects.all(),
        "nav_links": NavLink.objects.all(),
        "partners": Partner.objects.filter(is_active=True),
        "testimonials": Testimonial.objects.filter(is_active=True),
        "newsletter_form": NewsletterForm(),
        "visitor_stats": _visitor_stats(),
    }
    return render(request, "pages/about.html", context)


@never_cache
def faq(request):
    categories = FAQCategory.objects.prefetch_related("items")
    total_items = sum(cat.items.count() for cat in categories)
    context = {
        "settings": SiteSettings.load(),
        "categories": categories,
        "total_items": total_items,
        "social_links": SocialLink.objects.all(),
        "internal_apps": InternalApp.objects.all(),
        "nav_links": NavLink.objects.all(),
        "newsletter_form": NewsletterForm(),
        "visitor_stats": _visitor_stats(),
    }
    return render(request, "pages/faq.html", context)


@never_cache
def contact(request):
    settings_obj = SiteSettings.load()
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_message = form.save()

            # Auto-reply to the visitor.
            send_branded_mail(
                template="emails/contact_user_confirmation.html",
                subject="استلمنا رسالتك — إيمس",
                to=[contact_message.email],
                context={
                    "name": contact_message.name,
                    "subject_label": contact_message.get_subject_display(),
                    "message": contact_message.message,
                },
            )
            # Notify support inbox.
            if settings_obj.email:
                send_branded_mail(
                    template="emails/contact_admin_notification.html",
                    subject=f"رسالة تواصل جديدة: {contact_message.name}",
                    to=[settings_obj.email],
                    reply_to=contact_message.email,
                    context={
                        "name": contact_message.name,
                        "email": contact_message.email,
                        "phone": contact_message.phone,
                        "subject_label": contact_message.get_subject_display(),
                        "message": contact_message.message,
                    },
                )
            messages.success(request, "شكرا لتواصلك معنا! سنرد عليك في أقرب وقت ممكن.")
            return redirect("pages:contact")
        else:
            messages.error(request, "الرجاء التحقق من الحقول المدخلة.")
    else:
        form = ContactForm()

    context = {
        "settings": settings_obj,
        "contact_page": ContactPageSettings.load(),
        "form": form,
        "social_links": SocialLink.objects.all(),
        "internal_apps": InternalApp.objects.all(),
        "nav_links": NavLink.objects.all(),
        "newsletter_form": NewsletterForm(),
        "visitor_stats": _visitor_stats(),
    }
    return render(request, "pages/contact.html", context)


def _visitor_stats():
    today = date.today()
    return {
        "today": SiteVisitor.objects.filter(date=today).count(),
        "month": SiteVisitor.objects.filter(date__year=today.year, date__month=today.month).count(),
        "total": SiteVisitor.objects.count(),
    }
