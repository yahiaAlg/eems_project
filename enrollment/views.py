from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from pages.forms import NewsletterForm
from pages.models import Branch, InternalApp, NavLink, SiteSettings, SocialLink
from pages.views import _visitor_stats

from .forms import CommentForm, EnquiryForm, GeneralEnquiryForm, IndividualSubscribeForm
from .models import Client, Enrollment, Formateur, FormationSession, Offering, Participant


def _shared_chrome_context():
    """Context needed by the site-wide pages/partials/_navbar.html and _footer.html."""
    return {
        "social_links": SocialLink.objects.all(),
        "internal_apps": InternalApp.objects.all(),
        "nav_links": NavLink.objects.all(),
        "newsletter_form": NewsletterForm(),
        "visitor_stats": _visitor_stats(),
    }


def catalog(request):
    session_slug = request.GET.get("session") or ""
    branch_id = request.GET.get("branch") or ""
    level = request.GET.get("level") or ""
    formateur_slug = request.GET.get("formateur") or ""
    query = request.GET.get("q") or ""

    offerings = (
        Offering.objects.filter(is_active=True, session__is_active=True)
        .select_related("session", "specialty__branch", "formateur")
    )
    if session_slug:
        offerings = offerings.filter(session__slug=session_slug)
    if branch_id:
        offerings = offerings.filter(specialty__branch_id=branch_id)
    if level:
        offerings = offerings.filter(qualification_level=level)
    if formateur_slug:
        offerings = offerings.filter(formateur__slug=formateur_slug)
    if query:
        offerings = offerings.filter(
            Q(title__icontains=query) | Q(code__icontains=query) | Q(branch_label__icontains=query)
        )

    context = {
        "settings": SiteSettings.load(),
        "sessions": FormationSession.objects.filter(is_active=True),
        "branches": Branch.objects.filter(is_active=True),
        "formateurs": Formateur.objects.filter(is_active=True, offerings__isnull=False).distinct(),
        "offerings": offerings,
        "selected_session": session_slug,
        "selected_branch": int(branch_id) if branch_id.isdigit() else None,
        "selected_level": int(level) if level.isdigit() else None,
        "selected_formateur": formateur_slug,
        "query": query,
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/catalog.html", context)


def formateur_detail(request, slug):
    formateur = get_object_or_404(Formateur, slug=slug, is_active=True)
    offerings = (
        formateur.offerings.filter(is_active=True, session__is_active=True)
        .select_related("session", "specialty__branch")
    )
    context = {
        "settings": SiteSettings.load(),
        "formateur": formateur,
        "offerings": offerings,
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/formateur_detail.html", context)


def formateur_cv_print(request, slug):
    """Auto-generated, print-optimized CV — built live from the formateur's
    current profile data (no PDF library, no stored file: plain HTML with
    print CSS). Only reachable when the formateur is on 'auto' CV mode;
    'custom' mode formateurs serve their uploaded file directly instead."""
    formateur = get_object_or_404(Formateur, slug=slug, is_active=True)
    context = {
        "formateur": formateur,
        "bio_text": formateur.bio or "نبذة تعريفية غير متوفرة بعد.",
        "settings": SiteSettings.load(),
    }
    return render(request, "enrollment/documents/cv_placeholder.html", context)


def general_enquiry(request):
    """General 'talk to an advisor' request, not tied to a specific offering."""
    if request.method == "POST":
        form = GeneralEnquiryForm(request.POST)
        if form.is_valid():
            enquiry = form.save(commit=False)
            enquiry.offering = None
            enquiry.save()
            messages.success(
                request,
                "تم استلام طلبكم، سيتواصل معكم أحد مستشارينا في أقرب وقت ممكن.",
            )
        else:
            messages.error(request, "الرجاء التحقق من المعلومات المدخلة.")
    return redirect(request.META.get("HTTP_REFERER") or "pages:home")


def specialty_detail(request, session_slug, code):
    offering = get_object_or_404(
        Offering, session__slug=session_slug, code=code, is_active=True,
    )

    comment_form = CommentForm()
    enquiry_form = EnquiryForm()

    if request.method == "POST" and request.POST.get("form_type") == "comment":
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.offering = offering
            comment.save()
            messages.success(
                request,
                "شكرا لك! تم استلام تعليقك وسيظهر بعد مراجعته من طرف فريقنا.",
            )
            return redirect(offering.get_absolute_url() + "#comments")

    elif request.method == "POST" and request.POST.get("form_type") == "enquiry":
        enquiry_form = EnquiryForm(request.POST)
        if enquiry_form.is_valid():
            enquiry = enquiry_form.save(commit=False)
            enquiry.offering = offering
            enquiry.save()
            messages.success(
                request,
                "تم استلام استفساركم، سيتواصل معكم فريقنا في أقرب وقت ممكن.",
            )
            return redirect(offering.get_absolute_url() + "#enquiry")

    context = {
        "settings": SiteSettings.load(),
        "offering": offering,
        "comments": offering.approved_comments,
        "comment_form": comment_form,
        "enquiry_form": enquiry_form,
        "related_offerings": Offering.objects.filter(
            is_active=True, session=offering.session,
        ).exclude(pk=offering.pk)[:3],
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/specialty_detail.html", context)


def fiche_technique_print(request, session_slug, code):
    """Auto-generated, print-optimized fiche technique — built live from
    the offering's current data (no PDF library, no stored file: plain
    HTML with print CSS). Only reachable when the offering is on 'auto'
    mode; 'custom' mode offerings serve their uploaded file directly."""
    offering = get_object_or_404(
        Offering, session__slug=session_slug, code=code, is_active=True,
    )
    context = {
        "offering": offering,
        "qualification_level": offering.get_qualification_level_display(),
        "certificate_type": offering.get_certificate_type_display(),
        "entry_level": offering.get_entry_level_display(),
        "description_text": offering.description or "تعريف مفصل للتخصص متوفر قريبا.",
        "settings": SiteSettings.load(),
    }
    return render(request, "enrollment/documents/fiche_technique_placeholder.html", context)


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
                address=data.get("address", ""),
                full_name=data["full_name"],
                birth_date=data.get("birth_date"),
                gender=data.get("gender", ""),
                education_level=data.get("education_level", ""),
                source=data.get("source") or "web",
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
            motivation_lines = [data.get("motivation", "").strip()]
            extra = []
            if data.get("employment_status"):
                extra.append(
                    "الوضعية المهنية: "
                    + dict(form.fields["employment_status"].choices).get(data["employment_status"], "")
                )
            if data.get("preferred_contact_time"):
                extra.append(
                    "الوقت المفضل للاتصال: "
                    + dict(form.fields["preferred_contact_time"].choices).get(data["preferred_contact_time"], "")
                )
            if extra:
                motivation_lines.append("\n".join(extra))
            Enrollment.objects.create(
                client=client,
                participant=participant,
                offering=offering,
                motivation="\n\n".join(line for line in motivation_lines if line),
            )
            return redirect("enrollment:subscribe_success")
    else:
        form = IndividualSubscribeForm()

    context = {"settings": SiteSettings.load(), "form": form, "offering": offering, **_shared_chrome_context()}
    return render(request, "enrollment/subscribe.html", context)


def subscribe_success(request):
    context = {"settings": SiteSettings.load()}
    return render(request, "enrollment/subscribe_success.html", context)
