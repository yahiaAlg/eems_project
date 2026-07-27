from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from pages.models import Branch, SiteSettings

from .forms import CommentForm, EnquiryForm, GeneralEnquiryForm, IndividualSubscribeForm
from .models import Client, Enrollment, FormationSession, Offering, Participant


def catalog(request):
    session_slug = request.GET.get("session") or ""
    branch_id = request.GET.get("branch") or ""
    level = request.GET.get("level") or ""
    query = request.GET.get("q") or ""

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
    if query:
        offerings = offerings.filter(
            Q(title__icontains=query) | Q(code__icontains=query) | Q(branch_label__icontains=query)
        )

    context = {
        "settings": SiteSettings.load(),
        "sessions": FormationSession.objects.filter(is_active=True),
        "branches": Branch.objects.filter(is_active=True),
        "offerings": offerings,
        "selected_session": session_slug,
        "selected_branch": int(branch_id) if branch_id.isdigit() else None,
        "selected_level": int(level) if level.isdigit() else None,
        "query": query,
    }
    return render(request, "enrollment/catalog.html", context)


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
    }
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

    context = {"settings": SiteSettings.load(), "form": form, "offering": offering}
    return render(request, "enrollment/subscribe.html", context)


def subscribe_success(request):
    context = {"settings": SiteSettings.load()}
    return render(request, "enrollment/subscribe_success.html", context)
