from django import forms

from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User
from enrollment.forms import EDUCATION_LEVEL_CHOICES, SELECT_ATTRS, WIDGET_ATTRS
from enrollment.models import CLIENT_TYPE_CHOICES, GENDER_CHOICES


class EEMSAuthenticationForm(AuthenticationForm):
    """Login form for the new User-based auth (TODO 1.5).

    Same username/password pair as Django's default, styled to match the
    rest of the site, with a clearer Arabic message for the
    `is_active=False` window between registration and admin approval
    (TODO 1.3/1.4) — and a distinct message if the account was rejected.
    """

    error_messages = {
        **AuthenticationForm.error_messages,
        "inactive": (
            "حسابك لا يزال بانتظار موافقة الإدارة. سنُرسل لك بريدا إلكترونيا "
            "يحتوي على بيانات الدخول بمجرد التفعيل."
        ),
    }

    username = forms.CharField(
        label="رقم الهاتف",
        widget=forms.TextInput(
            attrs={**WIDGET_ATTRS, "dir": "ltr", "autofocus": True}
        ),
    )
    password = forms.CharField(
        label="كلمة المرور",
        strip=False,
        widget=forms.PasswordInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
    )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            client = getattr(user, "client", None)
            if client is not None and client.account_status == "rejected":
                raise forms.ValidationError(
                    "تم رفض هذا الحساب. للاستفسار، تواصل مع إدارة إيمس.",
                    code="inactive",
                )
            raise forms.ValidationError(
                self.error_messages["inactive"], code="inactive"
            )


class EEMSPasswordResetForm(PasswordResetForm):
    """"Forgot password" request form (TODO 1.6) — same field/behaviour as
    Django's default (only ever emails users who are `is_active` and have a
    usable password, per `PasswordResetForm.get_users`), just styled to
    match the rest of the site and labeled in Arabic."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "البريد الإلكتروني"
        self.fields["email"].widget.attrs.update({**WIDGET_ATTRS, "dir": "ltr"})


class EEMSSetPasswordForm(SetPasswordForm):
    """New-password form shown at the reset-confirm link (TODO 1.6)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "كلمة المرور الجديدة"
        self.fields["new_password2"].label = "تأكيد كلمة المرور الجديدة"
        for field in self.fields.values():
            field.widget.attrs.update({**WIDGET_ATTRS, "dir": "ltr"})


class RegistrationForm(forms.Form):
    """Public 'create an account' form — individual or enterprise signup.

    Reuses the exact individual/enterprise field split already defined on
    `enrollment.models.Client` (see TODO 1.3), rather than the richer
    `enrollment.forms.IndividualSubscribeForm` (which also carries
    enrollment-specific fields like `motivation`/`employment_status` that
    don't belong on the account itself).

    Deliberately does NOT collect a password: per TODO 1.4, the linked
    `User` is created inactive and stays unusable until an admin reviews
    and activates the account, at which point a generated password is
    emailed to the client — so there is nothing for the visitor to set
    here.
    """

    client_type = forms.ChoiceField(
        label="نوع الحساب",
        choices=CLIENT_TYPE_CHOICES,
        initial="individual",
        widget=forms.RadioSelect,
    )

    # --- shared contact fields (Client.phone/email/wilaya/address) ---
    phone = forms.RegexField(
        label="رقم الهاتف",
        regex=r"^0(5|6|7)\d{8}$",
        error_messages={"invalid": "رقم هاتف جزائري غير صالح، مثال: 0770123456"},
        widget=forms.TextInput(
            attrs={**WIDGET_ATTRS, "placeholder": "0770 12 34 56", "dir": "ltr"}
        ),
        help_text="سيُستعمل هذا الرقم كاسم مستخدم لتسجيل الدخول لاحقا.",
    )
    # Required here (unlike the subscribe form) because TODO 1.4 emails the
    # generated login credentials to the client — an account with no email
    # would have no way to ever receive them.
    email = forms.EmailField(
        label="البريد الإلكتروني",
        widget=forms.EmailInput(
            attrs={**WIDGET_ATTRS, "dir": "ltr", "placeholder": "example@mail.com"}
        ),
        help_text="ضروري — سنرسل عليه بيانات الدخول بمجرد تفعيل الحساب.",
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

    # --- individual-only (Client.full_name/birth_date/gender/education_level) ---
    full_name = forms.CharField(
        label="الاسم واللقب",
        max_length=150,
        required=False,
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
    education_level = forms.ChoiceField(
        label="المستوى الدراسي",
        choices=EDUCATION_LEVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs=SELECT_ATTRS),
    )

    # --- enterprise-only (Client.company_name/trade_register_number/sector/responsible_*) ---
    company_name = forms.CharField(
        label="اسم المؤسسة",
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={**WIDGET_ATTRS, "placeholder": "مثال: مؤسسة النجاح ش.ذ.م.م"}
        ),
    )
    trade_register_number = forms.CharField(
        label="رقم السجل التجاري",
        max_length=60,
        required=False,
        widget=forms.TextInput(attrs={**WIDGET_ATTRS, "dir": "ltr"}),
    )
    sector = forms.CharField(
        label="قطاع النشاط",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs=WIDGET_ATTRS),
    )
    responsible_name = forms.CharField(
        label="الشخص المسؤول عن التنسيق",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs=WIDGET_ATTRS),
    )
    responsible_position = forms.CharField(
        label="منصب المسؤول",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs=WIDGET_ATTRS),
    )

    agree_terms = forms.BooleanField(
        label="أوافق على أن تراجع إيمس طلبي وتتواصل معي بخصوص هذا الحساب",
        required=True,
        error_messages={"required": "يجب الموافقة على هذا الشرط لإتمام إنشاء الحساب."},
    )

    # Honeypot — real humans never fill this. Same pattern as
    # IndividualSubscribeForm.
    website = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_website(self):
        value = self.cleaned_data.get("website")
        if value:
            raise forms.ValidationError("تعذر إرسال الطلب.")
        return value

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone and User.objects.filter(username=phone).exists():
            raise forms.ValidationError(
                "يوجد حساب مسجّل بهذا الرقم من قبل. إن كان هذا حسابك، استعمل "
                "صفحة تسجيل الدخول بدل إنشاء حساب جديد."
            )
        return phone

    def clean(self):
        cleaned = super().clean()
        client_type = cleaned.get("client_type")
        # Mirrors Client.clean()'s own individual-vs-enterprise requirement.
        if client_type == "enterprise":
            if not cleaned.get("company_name"):
                self.add_error("company_name", "اسم المؤسسة مطلوب بالنسبة للمؤسسات.")
        else:
            if not cleaned.get("full_name"):
                self.add_error("full_name", "الاسم الكامل مطلوب بالنسبة للأفراد.")
        return cleaned
