from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
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
    BonDeCommandeUploadForm,
    CartItemUpdateForm,
    ClientProfileForm,
    CommentForm,
    EnquiryForm,
    GeneralEnquiryForm,
    IndividualSubscribeForm,
    ProformaLineConfirmForm,
)
from .models import (
    Cart,
    CartItem,
    Client,
    Enrollment,
    Formateur,
    FormationSession,
    Offering,
    Participant,
    ProformaInvoice,
    ProformaInvoiceItem,
    QuoteRequest,
    QuoteRequestItem,
    WishlistItem,
)


def _shared_chrome_context():
    """Context needed by the site-wide pages/partials/_navbar.html and _footer.html."""
    return {
        "social_links": SocialLink.objects.all(),
        "internal_apps": InternalApp.objects.all(),
        "nav_links": NavLink.objects.all(),
        "newsletter_form": NewsletterForm(),
        "visitor_stats": _visitor_stats(),
    }


def _can_view_prices(request):
    """TODO 3.2 pricing-visibility rule: only a logged-in VIP client may see
    any price figure anywhere on the site — anonymous visitors and non-VIP
    clients must not see prices at all (fully absent from the rendered
    HTML, never merely blurred/hidden with CSS). Reused as-is everywhere
    else prices could leak (TODO 3.3: catalog cards, cart, checkout,
    order-history/proforma pages)."""
    if not request.user.is_authenticated:
        return False
    client = getattr(request.user, "client", None)
    return bool(client and client.is_vip)


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

    wishlisted_offering_ids = set()
    catalog_client = getattr(request.user, "client", None)
    if catalog_client is not None:
        # TODO 4.4 — lets the catalog cards render a filled/outline heart
        # per offering without a query per card.
        wishlisted_offering_ids = set(
            WishlistItem.objects.filter(client=catalog_client).values_list(
                "offering_id", flat=True
            )
        )

    context = {
        "settings": SiteSettings.load(),
        "sessions": FormationSession.objects.filter(is_active=True),
        "branches": Branch.objects.filter(is_active=True),
        "formateurs": Formateur.objects.filter(
            is_active=True, offerings__isnull=False
        ).distinct(),
        "offerings": offerings,
        "can_view_price": _can_view_prices(request),
        "wishlisted_offering_ids": wishlisted_offering_ids,
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
        "can_view_price": _can_view_prices(request),
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

    detail_client = getattr(request.user, "client", None)
    is_wishlisted = bool(
        detail_client
        and WishlistItem.objects.filter(
            client=detail_client, offering=offering
        ).exists()
    )

    context = {
        "settings": SiteSettings.load(),
        "offering": offering,
        "comments": offering.approved_comments,
        "comment_form": comment_form,
        "enquiry_form": enquiry_form,
        "can_view_price": _can_view_prices(request),
        "is_wishlisted": is_wishlisted,
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
        "can_view_price": _can_view_prices(request),
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
            # This quick-subscribe path creates a Client with no linked
            # User (mon-espace now requires a real account, see TODO
            # 1.8), so there's no self-service space to send them to yet —
            # land on the static thank-you page instead.
            messages.success(
                request,
                "تم استلام طلب تسجيلكم بنجاح. سيتواصل معكم فريقنا لتأكيد التسجيل.",
            )
            return redirect("enrollment:subscribe_success")
    else:
        form = IndividualSubscribeForm()

    context = {
        "settings": SiteSettings.load(),
        "form": form,
        "offering": offering,
        "can_view_price": _can_view_prices(request),
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/subscribe.html", context)


def subscribe_success(request):
    context = {"settings": SiteSettings.load()}
    return render(request, "enrollment/subscribe_success.html", context)


def _safe_next_url(request, fallback):
    """Resolve a trusted redirect target from POST/GET 'next', falling back
    to `fallback` if it's missing or points off-site (same check Django's
    own LoginView uses for its 'next' param)."""
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return fallback


@login_required
@require_POST
def add_to_cart(request, session_slug, code):
    """TODO 4.2 — the new entry point that replaces the old single-offering
    `subscribe` flow's buttons on the catalog/specialty-detail pages: queues
    an offering into the logged-in client's active `Cart` (TODO 4.1) instead
    of registering immediately, so several formations can be queued before
    checkout (Phase 5). The old `subscribe` URL/view above is left untouched
    and keeps working directly for backward compatibility."""
    offering = get_object_or_404(
        Offering,
        session__slug=session_slug,
        code=code,
        is_active=True,
    )
    fallback = offering.get_absolute_url()
    client = getattr(request.user, "client", None)
    if client is None:
        messages.info(
            request,
            "لا يوجد حساب زبون مرتبط بحسابك بعد. تواصل مع الإدارة إذا كنت تعتقد أن هذا خطأ.",
        )
        return redirect(_safe_next_url(request, fallback))

    cart = Cart.get_active_for_client(client)
    item, created = CartItem.objects.get_or_create(cart=cart, offering=offering)
    if created:
        messages.success(
            request, f"تمت إضافة «{offering.title}» إلى سلتك."
        )
    else:
        messages.info(
            request, f"«{offering.title}» موجود بالفعل في سلتك."
        )
    return redirect(_safe_next_url(request, fallback))


@login_required
@require_POST
def toggle_wishlist(request, session_slug, code):
    """TODO 4.4 — the "Save for later" button on the catalog/specialty-
    detail pages: a single endpoint that both saves and un-saves an
    offering, so the same button works whether the heart is being filled
    or emptied (mirrors `add_to_cart`'s idempotent get_or_create above)."""
    offering = get_object_or_404(
        Offering,
        session__slug=session_slug,
        code=code,
        is_active=True,
    )
    fallback = offering.get_absolute_url()
    client = getattr(request.user, "client", None)
    if client is None:
        messages.info(
            request,
            "لا يوجد حساب زبون مرتبط بحسابك بعد. تواصل مع الإدارة إذا كنت تعتقد أن هذا خطأ.",
        )
        return redirect(_safe_next_url(request, fallback))

    item, created = WishlistItem.objects.get_or_create(client=client, offering=offering)
    if created:
        messages.success(
            request, f"تمت إضافة «{offering.title}» إلى قائمة رغباتك."
        )
    else:
        item.delete()
        messages.info(
            request, f"تمت إزالة «{offering.title}» من قائمة رغباتك."
        )
    return redirect(_safe_next_url(request, fallback))


@login_required
def cart(request):
    """TODO 4.3 — the client's cart page: list every queued line, an inline
    form per line to edit the participant count (and, VIP-only, the
    billing basis + trainer), a remove action, and a subtotal/total that
    only renders for VIP clients (Phase 3 pricing-visibility rule)."""
    client = getattr(request.user, "client", None)
    if client is None:
        messages.info(
            request,
            "لا يوجد حساب زبون مرتبط بحسابك بعد. تواصل مع الإدارة إذا كنت تعتقد أن هذا خطأ.",
        )
        return redirect("pages:home")

    active_cart = Cart.get_active_for_client(client)
    items = list(
        active_cart.items.select_related(
            "offering__session", "offering__specialty__branch", "trainer"
        )
    )
    # Paired up front (instead of a pk-keyed dict) so the template can do a
    # plain `{% for item, form in items_with_forms %}` — Django templates
    # have no clean way to look a dict value up by a variable key.
    items_with_forms = [
        (
            item,
            CartItemUpdateForm(
                instance=item, is_vip=client.is_vip, prefix=f"item{item.pk}"
            ),
        )
        for item in items
    ]

    context = {
        "settings": SiteSettings.load(),
        "client": client,
        "cart": active_cart,
        "items_with_forms": items_with_forms,
        "can_view_price": _can_view_prices(request),
        "active_tab": "cart",
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/cart.html", context)


@login_required
@require_POST
def cart_update_item(request, item_id):
    client = getattr(request.user, "client", None)
    item = get_object_or_404(
        CartItem, pk=item_id, cart__client=client, cart__status="active"
    )
    form = CartItemUpdateForm(
        request.POST, instance=item, is_vip=client.is_vip, prefix=f"item{item.pk}"
    )
    if form.is_valid():
        form.save()
        messages.success(request, "تم تحديث السلة.")
    else:
        messages.error(request, "تعذر تحديث هذا العنصر، تحقق من القيم المدخلة.")
    return redirect("enrollment:cart")


@login_required
@require_POST
def cart_remove_item(request, item_id):
    client = getattr(request.user, "client", None)
    item = get_object_or_404(
        CartItem, pk=item_id, cart__client=client, cart__status="active"
    )
    title = item.offering.title
    item.delete()
    messages.success(request, f"تمت إزالة «{title}» من سلتك.")
    return redirect("enrollment:cart")


@login_required
def request_proforma(request):
    """'طلب فاتورة أولية' — TODO 5.1 (VIP): the "Request Proforma" action
    on the cart. Confirms (and requires) the billing basis per line —
    already editable inline on the cart page itself (TODO 4.3), but a
    request can't be sent until every line actually has one — shows the
    trainer already chosen per line read-only (trainer selection itself
    stays on the cart page, TODO 4.1), and accepts an optional "bon de
    commande" (purchase order) upload.

    TODO 5.2 persists the confirmed request as a `ProformaInvoice`, with
    each cart line frozen onto a `ProformaInvoiceItem` snapshot (so later
    price/trainer changes never alter a document already sent out), and
    the uploaded bon de commande saved directly on the invoice. The client
    is then sent to the printable proforma page (`proforma_print` below —
    plain HTML with print CSS, no PDF library) instead of just a generic
    success message.

    TODO 5.4 then locks the cart: once its lines are frozen onto the
    invoice, the cart itself is flipped to `status="converted"` so its
    items become read-only history (`cart_update_item`/`cart_remove_item`
    only ever match `cart__status="active"`) instead of staying editable
    underneath an already-submitted request. `Cart.get_active_for_client`
    transparently opens a fresh empty "active" cart for the client's next
    visit."""
    client = getattr(request.user, "client", None)
    if client is None:
        messages.info(
            request,
            "لا يوجد حساب زبون مرتبط بحسابك بعد. تواصل مع الإدارة إذا كنت تعتقد أن هذا خطأ.",
        )
        return redirect("pages:home")

    if not client.is_vip:
        messages.warning(
            request, "طلب الفاتورة الأولية (بروفورما) متاح فقط لزبائن VIP."
        )
        return redirect("enrollment:cart")

    active_cart = Cart.get_active_for_client(client)
    items = list(
        active_cart.items.select_related(
            "offering__session", "offering__specialty__branch", "trainer"
        )
    )
    if not items:
        messages.info(
            request,
            "سلتك فارغة — أضف تخصصا واحدا على الأقل قبل طلب فاتورة أولية.",
        )
        return redirect("enrollment:cart")

    unpriceable = [item for item in items if not item.offering.has_group_pricing]
    if unpriceable:
        titles = "، ".join(item.offering.title for item in unpriceable)
        messages.warning(
            request,
            f"لا يمكن طلب فاتورة أولية حاليا: لا يتوفر سعر جماعي للتخصص/التخصصات التالية: {titles}. "
            "تواصل مع الإدارة أو أزلها من سلتك.",
        )
        return redirect("enrollment:cart")

    if request.method == "POST":
        line_forms = [
            ProformaLineConfirmForm(request.POST, instance=item, prefix=f"item{item.pk}")
            for item in items
        ]
        attachment_form = BonDeCommandeUploadForm(request.POST, request.FILES)

        if all(f.is_valid() for f in line_forms) and attachment_form.is_valid():
            for f in line_forms:
                f.save()  # persists the confirmed billing_basis onto CartItem

            invoice = ProformaInvoice.objects.create(client=client)
            ProformaInvoiceItem.objects.bulk_create(
                [
                    ProformaInvoiceItem.snapshot_from_cart_item(invoice, item)
                    for item in items
                ]
            )

            uploaded = attachment_form.cleaned_data.get("bon_de_commande")
            if uploaded:
                invoice.bon_de_commande = uploaded
                invoice.bon_de_commande_original_name = uploaded.name
                invoice.save(
                    update_fields=["bon_de_commande", "bon_de_commande_original_name"]
                )
                messages.success(
                    request,
                    f"تم إنشاء طلب الفاتورة الأولية رقم {invoice.reference} مع إرفاق بون دي كوماند.",
                )
            else:
                messages.success(
                    request,
                    f"تم إنشاء طلب الفاتورة الأولية رقم {invoice.reference}.",
                )

            # TODO 5.4 — lock the submitted items in and free up the cart.
            active_cart.status = "converted"
            active_cart.save(update_fields=["status", "updated_at"])

            return redirect("enrollment:proforma_print", pk=invoice.pk)
    else:
        line_forms = [
            ProformaLineConfirmForm(instance=item, prefix=f"item{item.pk}")
            for item in items
        ]
        attachment_form = BonDeCommandeUploadForm()

    items_with_forms = list(zip(items, line_forms))

    context = {
        "settings": SiteSettings.load(),
        "client": client,
        "cart": active_cart,
        "items_with_forms": items_with_forms,
        "attachment_form": attachment_form,
        "can_view_price": _can_view_prices(request),
        "active_tab": "cart",
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/request_proforma.html", context)


@login_required
def proforma_print(request, pk):
    """Printable proforma invoice — TODO 5.2. No PDF-generation library:
    plain HTML rendered from `invoice`/`items`, with print-specific CSS
    (@media print) that the browser's own "Print / Save as PDF" handles —
    same pattern as `fiche_technique_print`/`formateur_cv_print` above.
    Only the invoice's own client, or staff, may view it."""
    invoice = get_object_or_404(
        ProformaInvoice.objects.select_related("client").prefetch_related(
            "items__offering__session", "items__trainer"
        ),
        pk=pk,
    )
    client = getattr(request.user, "client", None)
    if not request.user.is_staff and invoice.client_id != getattr(client, "pk", None):
        raise Http404("الفاتورة الأولية غير موجودة.")

    context = {
        "invoice": invoice,
        "client": invoice.client,
        "items": invoice.items.all(),
        "settings": SiteSettings.load(),
    }
    return render(request, "enrollment/documents/proforma_print.html", context)


@login_required
@require_POST
def request_quote(request):
    """'طلب عرض سعر' — TODO 5.3 (Non-VIP): the "Request Quote" action on
    the cart. Unlike the VIP "Request Proforma" flow (TODO 5.1/5.2), this
    is a single confirm-and-submit action — no per-line billing-basis/
    trainer confirmation and no attachment, since non-VIP `CartItem` rows
    never carry those to begin with. Persists a `QuoteRequest` with every
    cart line frozen onto a `QuoteRequestItem` (offering + participant
    count only). An accountant sets pricing per line afterwards
    (Phase 6).

    TODO 5.4 then locks the cart the same way `request_proforma` does:
    once its lines are frozen onto the quote, the cart flips to
    `status="converted"` so the client starts a fresh active cart next
    time rather than continuing to edit an already-submitted request."""
    client = getattr(request.user, "client", None)
    if client is None:
        messages.info(
            request,
            "لا يوجد حساب زبون مرتبط بحسابك بعد. تواصل مع الإدارة إذا كنت تعتقد أن هذا خطأ.",
        )
        return redirect("pages:home")

    if client.is_vip:
        messages.warning(
            request,
            "طلب عرض السعر متاح فقط لغير زبائن VIP — استعمل «طلب فاتورة أولية» بدلا من ذلك.",
        )
        return redirect("enrollment:cart")

    active_cart = Cart.get_active_for_client(client)
    items = list(active_cart.items.select_related("offering__session"))
    if not items:
        messages.info(
            request,
            "سلتك فارغة — أضف تخصصا واحدا على الأقل قبل طلب عرض سعر.",
        )
        return redirect("enrollment:cart")

    quote = QuoteRequest.objects.create(client=client)
    QuoteRequestItem.objects.bulk_create(
        [QuoteRequestItem.snapshot_from_cart_item(quote, item) for item in items]
    )

    # TODO 5.4 — lock the submitted items in and free up the cart.
    active_cart.status = "converted"
    active_cart.save(update_fields=["status", "updated_at"])

    messages.success(
        request,
        f"تم إنشاء طلب عرض السعر رقم {quote.reference}. سيتواصل معك فريقنا بعد التسعير.",
    )
    return redirect("enrollment:my_purchases")


@login_required
def quote_print(request, pk):
    """Printable quote-turned-invoice document — TODO 6.4. Same pattern as
    `proforma_print` above (plain HTML + print-specific CSS, no PDF
    library): the browser's own "Print / Save as PDF" handles the rest.

    Only reachable once the accountant has actually priced the quote
    (TODO 6.2/6.3 — `status` moved past "pending"); a still-pending quote
    has no tariff to show yet, so the client is sent back to "My
    Purchases" with an explanatory message instead of a half-empty
    document. Only the quote's own client, or staff, may view it."""
    quote = get_object_or_404(
        QuoteRequest.objects.select_related("client").prefetch_related(
            "items__offering"
        ),
        pk=pk,
    )
    client = getattr(request.user, "client", None)
    if not request.user.is_staff and quote.client_id != getattr(client, "pk", None):
        raise Http404("طلب عرض السعر غير موجود.")

    if quote.status == "pending" and not request.user.is_staff:
        messages.info(
            request,
            f"طلب عرض السعر {quote.reference} قيد التسعير — سيتم إعلامك فور توفر الفاتورة الأولية.",
        )
        return redirect("enrollment:my_purchases")

    context = {
        "quote": quote,
        "client": quote.client,
        "items": quote.items.all(),
        "settings": SiteSettings.load(),
    }
    return render(request, "enrollment/documents/quote_print.html", context)


@login_required
def wishlist(request):
    """'قائمة رغباتي' — Wishlist page (TODO 4.4): every offering the client
    has saved for later, each with a "move to cart" action."""
    client = getattr(request.user, "client", None)
    if client is None:
        messages.info(
            request,
            "لا يوجد حساب زبون مرتبط بحسابك بعد. تواصل مع الإدارة إذا كنت تعتقد أن هذا خطأ.",
        )
        return redirect("pages:home")

    items = WishlistItem.objects.filter(client=client).select_related(
        "offering__session", "offering__specialty__branch"
    )
    context = {
        "settings": SiteSettings.load(),
        "client": client,
        "items": items,
        "active_tab": "wishlist",
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/wishlist.html", context)


@login_required
@require_POST
def wishlist_remove(request, item_id):
    client = getattr(request.user, "client", None)
    item = get_object_or_404(WishlistItem, pk=item_id, client=client)
    title = item.offering.title
    item.delete()
    messages.success(request, f"تمت إزالة «{title}» من قائمة رغباتك.")
    return redirect("enrollment:wishlist")


@login_required
@require_POST
def wishlist_move_to_cart(request, item_id):
    """Convert a saved offering into a real cart line (TODO 4.4) — reuses
    `Cart.get_active_for_client` (TODO 4.1) and the same get_or_create
    idempotency as `add_to_cart`/`toggle_wishlist` above, then drops the
    now-redundant wishlist bookmark."""
    client = getattr(request.user, "client", None)
    item = get_object_or_404(WishlistItem, pk=item_id, client=client)
    offering = item.offering
    active_cart = Cart.get_active_for_client(client)
    CartItem.objects.get_or_create(cart=active_cart, offering=offering)
    item.delete()
    messages.success(request, f"تم نقل «{offering.title}» إلى سلتك.")
    return redirect("enrollment:cart")


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


@login_required
def dashboard(request):
    """'مساحتي' — the subscriber's own dashboard: every enrollment tied to
    the Client account linked to the logged-in user (TODO 1.8 — replaces
    the retired phone/session login), with self-service confirm/cancel."""
    client = getattr(request.user, "client", None)
    if client is None:
        messages.info(
            request,
            "لا يوجد حساب زبون مرتبط بحسابك بعد. تواصل مع الإدارة إذا كنت تعتقد أن هذا خطأ.",
        )
        return redirect("pages:home")

    enrollments = (
        Enrollment.objects.filter(client=client)
        .select_related(
            "offering__session", "offering__specialty__branch", "participant", "client"
        )
        .order_by("-created_at")
    )
    context = {
        "settings": SiteSettings.load(),
        "client": client,
        "phone": client.phone,
        "enrollments": enrollments,
        "active_tab": "dashboard",
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/dashboard.html", context)


@login_required
def profile(request):
    """'ملفي الشخصي' — My Profile (TODO 2.2): lets the logged-in client
    edit their own personal/contact fields (individuals) or personal +
    legal/enterprise fields (enterprises), reusing the individual/
    enterprise field split from `IndividualSubscribeForm`/`Client`."""
    client = getattr(request.user, "client", None)
    if client is None:
        messages.info(
            request,
            "لا يوجد حساب زبون مرتبط بحسابك بعد. تواصل مع الإدارة إذا كنت تعتقد أن هذا خطأ.",
        )
        return redirect("pages:home")

    if request.method == "POST":
        form = ClientProfileForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث ملفك الشخصي بنجاح.")
            return redirect("enrollment:profile")
    else:
        form = ClientProfileForm(instance=client)

    context = {
        "settings": SiteSettings.load(),
        "client": client,
        "form": form,
        "active_tab": "profile",
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/profile.html", context)


@login_required
@require_POST
def dashboard_confirm(request, pk):
    client = getattr(request.user, "client", None)
    enrollment = get_object_or_404(Enrollment, pk=pk, client=client)
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


@login_required
@require_POST
def dashboard_cancel(request, pk):
    client = getattr(request.user, "client", None)
    enrollment = get_object_or_404(Enrollment, pk=pk, client=client)
    if enrollment.can_cancel:
        enrollment.status = "cancelled"
        enrollment.cancelled_at = timezone.now()
        enrollment.save(update_fields=["status", "cancelled_at", "updated_at"])
        messages.success(request, "تم إلغاء تسجيلك.")
    else:
        messages.warning(request, "لا يمكن إلغاء تسجيل تم تأكيده مسبقا.")
    return redirect("enrollment:dashboard")


@login_required
def my_purchases(request):
    """'مشترياتي' — client-space nav tab (TODO 4.5). Confirmed enrollments,
    the client's `ProformaInvoice` requests (TODO 5.2), and now (TODO 5.3)
    `QuoteRequest`s for non-VIP clients — Phase 8.1's "Request History"
    tab will give these their own dedicated section later."""
    client = getattr(request.user, "client", None)
    if client is None:
        messages.info(
            request,
            "لا يوجد حساب زبون مرتبط بحسابك بعد. تواصل مع الإدارة إذا كنت تعتقد أن هذا خطأ.",
        )
        return redirect("pages:home")

    purchases = (
        Enrollment.objects.filter(client=client, status="confirmed")
        .select_related(
            "offering__session", "offering__specialty__branch", "participant"
        )
        .order_by("-confirmed_at")
    )
    proformas = ProformaInvoice.objects.filter(client=client).prefetch_related("items")
    quotes = QuoteRequest.objects.filter(client=client).prefetch_related("items")
    context = {
        "settings": SiteSettings.load(),
        "client": client,
        "purchases": purchases,
        "proformas": proformas,
        "quotes": quotes,
        "can_view_price": _can_view_prices(request),
        "active_tab": "purchases",
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/my_purchases.html", context)


@login_required
def metrics(request):
    """'إحصائياتي' — client-space nav tab (TODO 4.5). Plain counts drawn
    from what already exists (enrollments, cart, wishlist); Phase 8.2 will
    turn this into Chart.js widgets (vendor asset already bundled) once
    spend/proforma history exists to chart."""
    client = getattr(request.user, "client", None)
    if client is None:
        messages.info(
            request,
            "لا يوجد حساب زبون مرتبط بحسابك بعد. تواصل مع الإدارة إذا كنت تعتقد أن هذا خطأ.",
        )
        return redirect("pages:home")

    enrollments = Enrollment.objects.filter(client=client)
    active_cart = Cart.get_active_for_client(client)

    context = {
        "settings": SiteSettings.load(),
        "client": client,
        "total_enrollments": enrollments.count(),
        "confirmed_count": enrollments.filter(status="confirmed").count(),
        "pending_count": enrollments.filter(status="pending").count(),
        "cancelled_count": enrollments.filter(status="cancelled").count(),
        "cart_items_count": active_cart.items_count,
        "wishlist_count": WishlistItem.objects.filter(client=client).count(),
        "active_tab": "metrics",
        **_shared_chrome_context(),
    }
    return render(request, "enrollment/metrics.html", context)
