from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from pages.models import Branch, SiteSettings

from .forms import IndividualSubscribeForm
from .models import Client, Enrollment, FormationSession, Offering, Participant


def catalog(request):
    session_slug = request.GET.get("session") or ""
    branch_id = request.GET.get("branch") or ""
    level = request.GET.get("level") or ""

    offerings = (
        Offering.objects.filter(is_active=True, session__is_active=True)
        .select_related("session", "specialty__branch")
    )
    if session_slug:
        offerings = offerings.filter(session__slug=session_slug)
    if branch_id:
        offerings = offerings.filter(specialty__branch_id=branch_id)
    if level:
        offerings = offerings.filter(qualification_level=level)

    context = {
        "settings": SiteSettings.load(),
        "sessions": FormationSession.objects.filter(is_active=True),
        "branches": Branch.objects.filter(is_active=True),
        "offerings": offerings,
        "selected_session": session_slug,
        "selected_branch": int(branch_id) if branch_id.isdigit() else None,
        "selected_level": int(level) if level.isdigit() else None,
    }
    return render(request, "enrollment/catalog.html", context)


def specialty_detail(request, session_slug, code):
    offering = get_object_or_404(
        Offering, session__slug=session_slug, code=code, is_active=True,
    )
    context = {"settings": SiteSettings.load(), "offering": offering}
    return render(request, "enrollment/specialty_detail.html", context)


def subscribe(request, session_slug, code):
    offering = get_object_or_404(
        Offering, session__slug=session_slug, code=code, is_active=True,
    )

    if offering.seats_remaining <= 0:
        messages.warning(request, "تنبيه: اكتملت المقاعد المتاحة لهذا التخصص، يمكنكم التسجيل في قائمة الانتظار.")

    if request.method == "POST":
        form = IndividualSubscribeForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            client = Client.objects.create(
                client_type="individual",
                phone=data["phone"],
                email=data.get("email", ""),
                wilaya=data.get("wilaya") or "سطيف",
                full_name=data["full_name"],
                birth_date=data.get("birth_date"),
                gender=data.get("gender", ""),
                education_level=data.get("education_level", ""),
                source="web",
            )
            participant = Participant.objects.create(
                client=client,
                full_name=client.full_name,
                phone=client.phone,
                email=client.email,
                birth_date=client.birth_date,
                gender=client.gender,
                education_level=client.education_level,
            )
            Enrollment.objects.create(
                client=client,
                participant=participant,
                offering=offering,
                motivation=data.get("motivation", ""),
            )
            return redirect("enrollment:subscribe_success")
    else:
        form = IndividualSubscribeForm()

    context = {"settings": SiteSettings.load(), "form": form, "offering": offering}
    return render(request, "enrollment/subscribe.html", context)


def subscribe_success(request):
    context = {"settings": SiteSettings.load()}
    return render(request, "enrollment/subscribe_success.html", context)
