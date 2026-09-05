import os

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    BILLING_BASIS_CHOICES,
    CartItem,
    Client,
    Comment,
    Enquiry,
    Formateur,
    GENDER_CHOICES,
    SOURCE_CHOICES,
)

EDUCATION_LEVEL_CHOICES = [
    ("", "اختر المستوى الدراسي"),
    ("none", "بدون مستوى / محو أمية"),
    ("primary", "ابتدائي"),
    ("middle", "متوسط"),
    ("secondary", "ثانوي"),
    ("bac", "شهادة البكالوريا"),
    ("university", "جامعي"),
]

EMPLOYMENT_STATUS_CHOICES = [
    ("", "اختر الوضعية المهنية"),
    ("student", "طالب"),
    ("employed", "موظف/عامل"),
    ("unemployed", "بدون عمل"),
    ("self_employed", "صاحب نشاط حر"),
]

CONTACT_TIME_CHOICES = [
    ("", "أي وقت"),
    ("morning", "صباحا (08:00 - 12:00)"),
    ("afternoon", "بعد الظهر (13:00 - 16:30)"),
]


WIDGET_ATTRS = {"class": "form-control"}
SELECT_ATTRS = {"class": "form-select"}


class IndividualSubscribeForm(forms.Form):
    """Registration form for an individual candidate — collects rich profile data
    about the client in addition to the minimum contact fields."""

    # --- identity ---
    full_name = forms.CharField(
        label="الاسم واللقب",
        max_length=150,
        widget=forms.TextInput(
            attrs={**WIDGET_ATTRS, "placeholder": "مثال: أحمد بلعيد"}
        ),
    )
    birth_date = forms.DateField(
        label="تاريخ الميلاد",
        required=False,
        widget=forms.DateInput(attrs={**WIDGET_ATTRS, "type": "date"}),
    )
    gender = forms.ChoiceField(
        label="الجنس",
        choices=[("", "اختر")] + list(GENDER_CHOICES),
        required=False,
        widget=forms.Select(attrs=SELECT_ATTRS),
    )

    # --- contact ---
    phone = forms.RegexField(
        label="رقم الهاتف",
        regex=r"^0(5|6|7)\d{8}$",
        error_messages={"invalid": "رقم هاتف جزائري غير صالح، مثال: 0770123456"},
        widget=forms.TextInput(
            attrs={**WIDGET_ATTRS, "placeholder": "0770 12 34 56", "dir": "ltr"}
        ),
    )
    email = forms.EmailField(
        label="البريد الإلكتروني",
        required=False,
        widget=forms.EmailInput(
            attrs={**WIDGET_ATTRS, "dir": "ltr", "placeholder": "example@mail.com"}
        ),
    )
    wilaya = forms.CharField(
        label="الولاية",
        max_length=60,
        required=False,
        initial="سطيف",
        widget=forms.TextInput(attrs=WIDGET_ATTRS),
    )
    address = forms.CharField(
        label="العنوان (اختياري)",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs=WIDGET_ATTRS),
    )

    # --- profile / background ---
    education_level = forms.ChoiceField(
        label="المستوى الدراسي",
        choices=EDUCATION_LEVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs=SELECT_ATTRS),
    )
    employment_status = forms.ChoiceField(
        label="الوضعية المهنية الحالية",
        choices=EMPLOYMENT_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs=SELECT_ATTRS),
    )
    preferred_contact_time = forms.ChoiceField(
        label="الوقت المفضل للاتصال",
        choices=CONTACT_TIME_CHOICES,
        required=False,
        widget=forms.Select(attrs=SELECT_ATTRS),
    )
    source = forms.ChoiceField(
        label="كيف سمعت عنّا؟",
        choices=SOURCE_CHOICES,
        required=False,
        initial="web",
        widget=forms.Select(attrs=SELECT_ATTRS),
    )

    # --- about this enrollment ---
    motivation = forms.CharField(
        label="ملاحظات / دافع الترشح لهذا التخصص",
        required=False,
        widget=forms.Textarea(
            attrs={
                **WIDGET_ATTRS,
                "rows": 4,
                "placeholder": "لماذا تريد الالتحاق بهذا التخصص؟ أخبرنا بأي معلومة تفيدنا في متابعة ملفك.",
            }
        ),
    )
    agree_terms = forms.BooleanField(
        label="أوافق على أن يتم التواصل معي من طرف إيمس بخصوص هذا التسجيل",
        required=True,
        error_messages={"required": "يجب الموافقة على هذا الشرط لإتمام التسجيل."},
    )

    # Honeypot — real humans never fill this.
    website = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_website(self):
        value = self.cleaned_data.get("website")
        if value:
            raise forms.ValidationError("تعذر إرسال الطلب.")
        return value


# Fields relevant only to individual clients — dropped from
# `ClientProfileForm` entirely for enterprise instances so they can never
# be submitted/blanked via that form.
PROFILE_INDIVIDUAL_FIELDS = ["full_name", "birth_date", "gender", "education_level"]

# Fields relevant only to enterprise clients — dropped for individuals.
PROFILE_ENTERPRISE_FIELDS = [
    "company_name",
    "trade_register_number",
    "sector",
    "responsible_name",
    "responsible_position",
    "forme_juridique",
    "nif",
    "nis",
    "article_imposition",
    "rib",
    "tva_exempt",
    "postal_code",
    "city",
    "website",
    "main_contact_name",
    "main_contact_phone",
    "main_contact_email",
]


class ClientProfileForm(forms.ModelForm):
    """'My Profile' form (TODO 2.2) — lets a logged-in client edit their own
    contact/personal fields (individuals) or contact + legal/enterprise
    fields (enterprises), reusing the individual/enterprise field split
    already defined on `Client` (same split as `IndividualSubscribeForm`/
    `accounts.RegistrationForm`).

    `phone` (the login username), `client_type`, `source`, and the
    account-status/VIP fields are intentionally excluded — those are
    admin/accountant-only (see TODO 1.7/1.8 and the accounts app).
    """

    INDIVIDUAL_FIELDS = PROFILE_INDIVIDUAL_FIELDS
    ENTERPRISE_FIELDS = PROFILE_ENTERPRISE_FIELDS

    class Meta:
        model = Client
        fields = (
            ["email", "wilaya", "address"]
            + PROFILE_INDIVIDUAL_FIELDS
            + PROFILE_ENTERPRISE_FIELDS
        )
        widgets = {
            "email": forms.EmailInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
            "wilaya": forms.TextInput(attrs=WIDGET_ATTRS),
            "address": forms.TextInput(attrs=WIDGET_ATTRS),
            "full_name": forms.TextInput(attrs=WIDGET_ATTRS),
            "birth_date": forms.DateInput(attrs={**WIDGET_ATTRS, "type": "date"}),
            "gender": forms.Select(attrs=SELECT_ATTRS, choices=[("", "اختر")] + list(GENDER_CHOICES)),
            "education_level": forms.Select(attrs=SELECT_ATTRS, choices=EDUCATION_LEVEL_CHOICES),
            "company_name": forms.TextInput(attrs=WIDGET_ATTRS),
            "trade_register_number": forms.TextInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
            "sector": forms.TextInput(attrs=WIDGET_ATTRS),
            "responsible_name": forms.TextInput(attrs=WIDGET_ATTRS),
            "responsible_position": forms.TextInput(attrs=WIDGET_ATTRS),
            "forme_juridique": forms.TextInput(attrs=WIDGET_ATTRS),
            "nif": forms.TextInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
            "nis": forms.TextInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
            "article_imposition": forms.TextInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
            "rib": forms.TextInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
            "postal_code": forms.TextInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
            "city": forms.TextInput(attrs=WIDGET_ATTRS),
            "website": forms.URLInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
            "main_contact_name": forms.TextInput(attrs=WIDGET_ATTRS),
            "main_contact_phone": forms.TextInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
            "main_contact_email": forms.EmailInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Drop whichever field set doesn't apply to this client, so it can
        # never be submitted/blanked via this form (client_type itself is
        # fixed and not editable here — see class docstring).
        irrelevant = (
            self.ENTERPRISE_FIELDS
            if not self.instance.is_enterprise
            else self.INDIVIDUAL_FIELDS
        )
        for name in irrelevant:
            self.fields.pop(name, None)
        if "full_name" in self.fields:
            self.fields["full_name"].required = True
        if "company_name" in self.fields:
            self.fields["company_name"].required = True

    def clean(self):
        # Re-run Client.clean()'s individual-vs-enterprise requirement so a
        # required field missing here surfaces as a normal form error
        # instead of raising on save().
        cleaned = super().clean()
        if self.instance.is_enterprise and not cleaned.get("company_name"):
            self.add_error("company_name", "اسم المؤسسة مطلوب بالنسبة للمؤسسات.")
        if not self.instance.is_enterprise and not cleaned.get("full_name"):
            self.add_error("full_name", "الاسم الكامل مطلوب بالنسبة للأفراد.")
        return cleaned


class CartItemUpdateForm(forms.ModelForm):
    """Per-line edit form on the cart page (TODO 4.3): participant count for
    everyone, plus billing basis + trainer choice for VIP carts only —
    `billing_basis`/`trainer` are dropped entirely for non-VIP clients so
    the view can never render or accept them (TODO 4.1's "form/view layer"
    enforcement, `CartItem.clean()` is only the last-resort safety net).
    """

    class Meta:
        model = CartItem
        fields = ["participant_count", "billing_basis", "trainer"]
        widgets = {
            "participant_count": forms.NumberInput(attrs={**WIDGET_ATTRS, "min": 1}),
            "billing_basis": forms.Select(attrs=SELECT_ATTRS),
            "trainer": forms.Select(attrs=SELECT_ATTRS),
        }
        labels = {
            "participant_count": "عدد المشاركين",
            "billing_basis": "أساس الفوترة",
            "trainer": "المكوّن المفضّل",
        }

    def __init__(self, *args, is_vip=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not is_vip:
            self.fields.pop("billing_basis", None)
            self.fields.pop("trainer", None)
            return

        self.fields["billing_basis"].required = False
        # Only offer a billing basis this specific offering actually
        # carries a price for (TODO 3.1) — no point letting a VIP pick
        # "per day" on an offering with no price_per_day set. This form
        # only ever edits an existing CartItem (see the cart view), so
        # `self.instance.offering` is always available here.
        offering = self.instance.offering
        basis_labels = dict(BILLING_BASIS_CHOICES)
        choices = [("", "— اختر —")]
        if offering.price_per_day:
            choices.append(("per_day", basis_labels["per_day"]))
        if offering.price_per_participant:
            choices.append(("per_participant", basis_labels["per_participant"]))
        self.fields["billing_basis"].choices = choices

        self.fields["trainer"].required = False
        self.fields["trainer"].empty_label = "— بدون تفضيل —"
        self.fields["trainer"].queryset = Formateur.objects.filter(is_active=True)


# --- Request Proforma (TODO 5.1, VIP-only) ------------------------------
# Two small forms backing the "Request Proforma" action on the cart:
# `ProformaLineConfirmForm` re-confirms (and *requires*) the billing basis
# already offered as an optional inline edit on the cart page itself
# (`CartItemUpdateForm` above) — a proforma can't be requested for a line
# that isn't priced yet. `BonDeCommandeUploadForm` is the optional
# purchase-order attachment; it's a plain Form (not tied to a model) since
# TODO 5.2 hasn't introduced `ProformaInvoice` yet — see
# `views.request_proforma` for where the validated upload ends up meanwhile.

BON_DE_COMMANDE_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "webp"]
BON_DE_COMMANDE_MAX_SIZE = 10 * 1024 * 1024  # 10 MB — plenty for a scanned order form

# Magic-byte signatures checked against the file's actual bytes, not just
# its extension or browser-declared content-type (both of which a client
# can trivially fake) — a lightweight, dependency-free mimetype check.
BON_DE_COMMANDE_SIGNATURES = {
    "pdf": (b"%PDF-",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
}


def validate_bon_de_commande(uploaded_file):
    """TODO 5.1 — validate the optional "bon de commande" upload: allowed
    extension, a sane max size, and content that actually matches the
    extension it claims (magic-byte check)."""
    ext = os.path.splitext(uploaded_file.name)[1].lstrip(".").lower()
    if ext not in BON_DE_COMMANDE_EXTENSIONS:
        raise ValidationError(
            "صيغة الملف غير مدعومة. الصيغ المقبولة: PDF أو صورة (JPG, PNG, WEBP)."
        )

    if uploaded_file.size > BON_DE_COMMANDE_MAX_SIZE:
        raise ValidationError("حجم الملف كبير جدا (الحد الأقصى 10 ميغابايت).")

    head = uploaded_file.read(16)
    uploaded_file.seek(0)
    if ext == "webp":
        is_valid_signature = head.startswith(b"RIFF") and head[8:12] == b"WEBP"
    else:
        is_valid_signature = any(
            head.startswith(sig) for sig in BON_DE_COMMANDE_SIGNATURES[ext]
        )
    if not is_valid_signature:
        raise ValidationError(
            "محتوى الملف لا يطابق صيغته المعلنة — تحقق من أنه ملف PDF أو صورة صالح."
        )


class ProformaLineConfirmForm(forms.ModelForm):
    """TODO 5.1 — per cart-line "confirm billing basis" step. Same field
    as `CartItemUpdateForm.billing_basis` above, but required here: a
    proforma request cannot be sent for a line without a chosen basis."""

    class Meta:
        model = CartItem
        fields = ["billing_basis"]
        widgets = {"billing_basis": forms.Select(attrs=SELECT_ATTRS)}
        labels = {"billing_basis": "أساس الفوترة"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["billing_basis"].required = True
        offering = self.instance.offering
        basis_labels = dict(BILLING_BASIS_CHOICES)
        choices = []
        if offering.price_per_day:
            choices.append(("per_day", basis_labels["per_day"]))
        if offering.price_per_participant:
            choices.append(("per_participant", basis_labels["per_participant"]))
        self.fields["billing_basis"].choices = choices


class BonDeCommandeUploadForm(forms.Form):
    """TODO 5.1 — optional purchase-order attachment on the Request
    Proforma action. See module docstring above for why this stays a
    plain Form for now."""

    bon_de_commande = forms.FileField(
        label="بون دي كوماند (اختياري)",
        required=False,
        validators=[validate_bon_de_commande],
        widget=forms.ClearableFileInput(
            attrs={**WIDGET_ATTRS, "accept": ".pdf,.jpg,.jpeg,.png,.webp"}
        ),
    )


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["name", "email", "rating", "text"]
        widgets = {
            "name": forms.TextInput(attrs={**WIDGET_ATTRS, "placeholder": "اسمك"}),
            "email": forms.EmailInput(
                attrs={**WIDGET_ATTRS, "placeholder": "بريدك (اختياري)", "dir": "ltr"}
            ),
            "rating": forms.Select(attrs=SELECT_ATTRS),
            "text": forms.Textarea(
                attrs={
                    **WIDGET_ATTRS,
                    "rows": 3,
                    "placeholder": "شاركنا رأيك حول هذا التخصص...",
                }
            ),
        }
        labels = {
            "name": "الاسم",
            "email": "البريد الإلكتروني",
            "rating": "تقييمك",
            "text": "تعليقك",
        }


class GeneralEnquiryForm(forms.ModelForm):
    """Same as EnquiryForm, used for a general 'talk to an advisor' request
    that isn't tied to a specific offering."""

    class Meta:
        model = Enquiry
        fields = ["name", "phone", "email", "question"]
        widgets = {
            "name": forms.TextInput(attrs={**WIDGET_ATTRS, "placeholder": "اسمك"}),
            "phone": forms.TextInput(
                attrs={**WIDGET_ATTRS, "placeholder": "رقم الهاتف", "dir": "ltr"}
            ),
            "email": forms.EmailInput(
                attrs={
                    **WIDGET_ATTRS,
                    "placeholder": "بريدك الإلكتروني (اختياري)",
                    "dir": "ltr",
                }
            ),
            "question": forms.Textarea(
                attrs={
                    **WIDGET_ATTRS,
                    "rows": 3,
                    "placeholder": "ما الذي تريد الاستفسار عنه؟",
                }
            ),
        }
        labels = {
            "name": "الاسم",
            "phone": "الهاتف",
            "email": "البريد الإلكتروني",
            "question": "طلبك",
        }


class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ["name", "phone", "email", "question"]
        widgets = {
            "name": forms.TextInput(attrs={**WIDGET_ATTRS, "placeholder": "اسمك"}),
            "phone": forms.TextInput(
                attrs={
                    **WIDGET_ATTRS,
                    "placeholder": "رقم الهاتف (اختياري)",
                    "dir": "ltr",
                }
            ),
            "email": forms.EmailInput(
                attrs={**WIDGET_ATTRS, "placeholder": "بريدك الإلكتروني", "dir": "ltr"}
            ),
            "question": forms.Textarea(
                attrs={
                    **WIDGET_ATTRS,
                    "rows": 3,
                    "placeholder": "اطرح سؤالك حول هذا التخصص، الشروط، أو المواعيد...",
                }
            ),
        }
        labels = {
            "name": "الاسم",
            "phone": "الهاتف",
            "email": "البريد الإلكتروني",
            "question": "سؤالك",
        }
