from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from pages.emails import send_branded_mail
from pages.forms import NewsletterForm
from pages.models import (
    Branch,
    InternalApp,
    NavLink,
    SiteSettings,
    SocialLink,
    Specialty,
)
from pages.views import _visitor_stats

from .forms import (
    CommentForm,
    DashboardLoginForm,
    EnquiryForm,
    GeneralEnquiryForm,
    IndividualSubscribeForm,
)
from .models import (
    Client,
    Enrollment,
    Formateur,
    FormationSession,
    Offering,
    Participant,
)

CLIENT_PHONE_SESSION_KEY = "client_phone"


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
    specialty_code = request.GET.get("specialty") or ""
    query = request.GET.get("q") or ""

    offerings = Offering.objects.filter(
        is_active=True, session__is_active=True
    ).select_related("session", "specialty__branch", "formateur")
    if session_slug:
        offerings = offerings.filter(session__slug=session_slug)
    if branch_id:
        offerings = offerings.filter(specialty__branch_id=branch_id)
    if level:
        offerings = offerings.filter(qualification_level=level)
    if formateur_slug:
        offerings = offerings.filter(formateur__slug=formateur_slug)
    if specialty_code:
        offerings = offerings.filter(specialty__code=specialty_code)
    if query:
        offerings = offerings.filter(
            Q(title__icontains=query)
            | Q(code__icontains=query)
            | Q(branch_label__icontains=query)
        )

    context = {
        "settings": SiteSettings.load(),
        "sessions": FormationSession.objects.filter(is_active=True),
        "branches": Branch.objects.filter(is_active=True),
        "formateurs": Formateur.objects.filter(
            is_active=True, offerings__isnull=False
        ).distinct(),
        "offerings": offerings,
        "selected_session": session_slug,
        "selected_branch": int(branch_id) if branch_id.isdigit() else None,
        "selected_level": int(level) if level.isdigit() else None,
        "selected_formateur": formateur_slug,
        "selected_specialty": specialty_code,
        "query": query,
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/catalog.html", context)


def formateur_detail(request, slug):
    formateur = get_object_or_404(Formateur, slug=slug, is_active=True)
    offerings = formateur.offerings.filter(
        is_active=True, session__is_active=True
    ).select_related("session", "specialty__branch")
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
        Offering,
        session__slug=session_slug,
        code=code,
        is_active=True,
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
            is_active=True,
            session=offering.session,
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
        Offering,
        session__slug=session_slug,
        code=code,
        is_active=True,
    )
    context = {
        "offering": offering,
        "qualification_level": offering.get_qualification_level_display(),
        "certificate_type": offering.get_certificate_type_display(),
        "entry_level": offering.get_entry_level_display(),
        "description_text": offering.description or "تعريف مفصل للتخصص متوفر قريبا.",
        "settings": SiteSettings.load(),
    }
    return render(
        request, "enrollment/documents/fiche_technique_placeholder.html", context
    )


def subscribe(request, session_slug, code):
    offering = get_object_or_404(
        Offering,
        session__slug=session_slug,
        code=code,
        is_active=True,
    )

    if offering.seats_remaining <= 0:
        messages.warning(
            request,
            "تنبيه: اكتملت المقاعد المتاحة لهذا التخصص، يمكنكم التسجيل في قائمة الانتظار.",
        )

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
                    + dict(form.fields["employment_status"].choices).get(
                        data["employment_status"], ""
                    )
                )
            if data.get("preferred_contact_time"):
                extra.append(
                    "الوقت المفضل للاتصال: "
                    + dict(form.fields["preferred_contact_time"].choices).get(
                        data["preferred_contact_time"], ""
                    )
                )
            if extra:
                motivation_lines.append("\n".join(extra))
            Enrollment.objects.create(
                client=client,
                participant=participant,
                offering=offering,
                motivation="\n\n".join(line for line in motivation_lines if line),
            )
            # Log the client into their self-service space (no password —
            # the phone they just typed is their identity) and send them
            # straight to their dashboard instead of a static thank-you page.
            request.session[CLIENT_PHONE_SESSION_KEY] = client.phone
            messages.success(
                request,
                "تم استلام طلب تسجيلكم بنجاح. يمكنكم متابعة حالته وتأكيده من مساحتي أدناه.",
            )
            return redirect("enrollment:dashboard")
    else:
        form = IndividualSubscribeForm()

    context = {
        "settings": SiteSettings.load(),
        "form": form,
        "offering": offering,
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/subscribe.html", context)


def subscribe_success(request):
    context = {"settings": SiteSettings.load()}
    return render(request, "enrollment/subscribe_success.html", context)


def subscribe_general(request):
    """Branch-first entry point for 'التسجيل الإلكتروني': pick a branch,
    then a specialty (AJAX, scoped to specialties that actually have an
    open offering), then a training (AJAX), then continue into the normal
    per-offering subscribe form above."""
    branches = (
        Branch.objects.filter(
            is_active=True,
            specialties__offerings__is_active=True,
            specialties__offerings__session__is_active=True,
        )
        .distinct()
        .order_by("order", "code")
    )
    context = {
        "settings": SiteSettings.load(),
        "branches": branches,
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/subscribe_general.html", context)


def ajax_specialties_for_branch(request):
    """GET ?branch=<id> -> [{code, name}] — only specialties of this branch
    that currently have at least one open offering (not the full ~500-entry
    nomenclature, which pages:SpecialtyViewSet already serves elsewhere)."""
    branch_id = request.GET.get("branch") or ""
    specialties = (
        Specialty.objects.filter(
            branch_id=branch_id,
            offerings__is_active=True,
            offerings__session__is_active=True,
        )
        .distinct()
        .order_by("code")
    )
    data = [{"code": sp.code, "name": sp.name} for sp in specialties]
    return JsonResponse({"results": data})


def ajax_offerings_for_specialty(request):
    """GET ?specialty=<code> -> open offerings/trainings for that specialty,
    each carrying the URL of its per-offering subscribe form."""
    specialty_code = request.GET.get("specialty") or ""
    offerings = (
        Offering.objects.filter(
            specialty__code=specialty_code,
            is_active=True,
            session__is_active=True,
        )
        .select_related("session")
        .order_by("session__order", "code")
    )
    data = [
        {
            "code": o.code,
            "title": o.title,
            "session_name": o.session.name,
            "seats_remaining": o.seats_remaining,
            "subscribe_url": reverse(
                "enrollment:subscribe", args=[o.session.slug, o.code]
            ),
        }
        for o in offerings
    ]
    return JsonResponse({"results": data})


def _dashboard_phone(request):
    return request.session.get(CLIENT_PHONE_SESSION_KEY)


def dashboard_login(request):
    """Return access to 'مساحتي' with just the phone number or email used
    at subscription time — there is no password anywhere in this flow."""
    if request.method == "POST":
        form = DashboardLoginForm(request.POST)
        if form.is_valid():
            method = form.cleaned_data.get("login_method") or "phone"
            if method == "email":
                email = form.cleaned_data["email"]
                client = Client.objects.filter(email__iexact=email).first()
                error_field = "email"
                error_msg = "لم نجد أي تسجيل بهذا البريد الإلكتروني. تأكد منه أو سجّل في تكوين أولا."
            else:
                phone = form.cleaned_data["phone"]
                client = Client.objects.filter(phone=phone).first()
                error_field = "phone"
                error_msg = (
                    "لم نجد أي تسجيل بهذا الرقم. تأكد من الرقم أو سجّل في تكوين أولا."
                )

            if client:
                # The dashboard/confirm/cancel views all key off the phone
                # number, so a client found via email is logged in the
                # same way as one found via phone.
                request.session[CLIENT_PHONE_SESSION_KEY] = client.phone
                return redirect("enrollment:dashboard")
            form.add_error(error_field, error_msg)
    else:
        form = DashboardLoginForm()

    context = {
        "settings": SiteSettings.load(),
        "form": form,
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/dashboard_login.html", context)


def dashboard_logout(request):
    request.session.pop(CLIENT_PHONE_SESSION_KEY, None)
    messages.success(request, "تم تسجيل خروجك من مساحتي.")
    return redirect("pages:home")


def dashboard(request):
    """'مساحتي' — the subscriber's own dashboard: every enrollment tied to
    the phone number in their session, with self-service confirm/cancel."""
    phone = _dashboard_phone(request)
    if not phone:
        return redirect("enrollment:dashboard_login")

    enrollments = (
        Enrollment.objects.filter(client__phone=phone)
        .select_related(
            "offering__session", "offering__specialty__branch", "participant", "client"
        )
        .order_by("-created_at")
    )
    context = {
        "settings": SiteSettings.load(),
        "phone": phone,
        "enrollments": enrollments,
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/dashboard.html", context)


@require_POST
def dashboard_confirm(request, pk):
    phone = _dashboard_phone(request)
    if not phone:
        return redirect("enrollment:dashboard_login")

    enrollment = get_object_or_404(Enrollment, pk=pk, client__phone=phone)
    if enrollment.can_confirm:
        enrollment.status = "confirmed"
        enrollment.confirmed_at = timezone.now()
        enrollment.save(update_fields=["status", "confirmed_at", "updated_at"])
        if enrollment.client.email:
            send_branded_mail(
                template="emails/enrollment_confirmed.html",
                subject="تأكيد تسجيلك — إيمس",
                to=[enrollment.client.email],
                context={
                    "client_name": enrollment.client.display_name,
                    "participant_name": enrollment.participant.full_name,
                    "offering_title": enrollment.offering.title,
                    "offering_code": enrollment.offering.code,
                    "session_name": enrollment.offering.session.name,
                },
            )
        messages.success(
            request, "تم تأكيد تسجيلك بنجاح. لم يعد بالإمكان إلغاؤه بعد الآن."
        )
    else:
        messages.warning(request, "لا يمكن تأكيد هذا التسجيل في وضعه الحالي.")
    return redirect("enrollment:dashboard")


@require_POST
def dashboard_cancel(request, pk):
    phone = _dashboard_phone(request)
    if not phone:
        return redirect("enrollment:dashboard_login")

    enrollment = get_object_or_404(Enrollment, pk=pk, client__phone=phone)
    if enrollment.can_cancel:
        enrollment.status = "cancelled"
        enrollment.cancelled_at = timezone.now()
        enrollment.save(update_fields=["status", "cancelled_at", "updated_at"])
        messages.success(request, "تم إلغاء تسجيلك.")
    else:
        messages.warning(request, "لا يمكن إلغاء تسجيل تم تأكيده مسبقا.")
    return redirect("enrollment:dashboard")
