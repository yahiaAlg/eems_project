from django import forms

from .models import Comment, Enquiry, GENDER_CHOICES, SOURCE_CHOICES

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


class DashboardLoginForm(forms.Form):
    """Access 'مساحتي' (my subscriptions dashboard) using either the phone
    number or the email address provided at subscription time — no
    password, matching the fact that clients aren't asked to create one
    anywhere in the flow."""

    LOGIN_METHOD_CHOICES = [("phone", "الهاتف"), ("email", "البريد الإلكتروني")]

    login_method = forms.ChoiceField(
        choices=LOGIN_METHOD_CHOICES,
        initial="phone",
        required=False,
        widget=forms.RadioSelect,
    )
    phone = forms.RegexField(
        label="رقم الهاتف",
        regex=r"^0(5|6|7)\d{8}$",
        required=False,
        error_messages={"invalid": "رقم هاتف جزائري غير صالح، مثال: 0770123456"},
        widget=forms.TextInput(
            attrs={
                **WIDGET_ATTRS,
                "placeholder": "0770 12 34 56",
                "dir": "ltr",
                "autofocus": True,
            }
        ),
    )
    email = forms.EmailField(
        label="البريد الإلكتروني",
        required=False,
        error_messages={"invalid": "بريد إلكتروني غير صالح."},
        widget=forms.EmailInput(
            attrs={**WIDGET_ATTRS, "placeholder": "example@email.com", "dir": "ltr"}
        ),
    )

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("login_method") or "phone"
        if method == "email":
            if not cleaned.get("email"):
                self.add_error("email", "الرجاء إدخال بريدك الإلكتروني.")
        else:
            if not cleaned.get("phone"):
                self.add_error("phone", "الرجاء إدخال رقم هاتفك.")
        return cleaned


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
