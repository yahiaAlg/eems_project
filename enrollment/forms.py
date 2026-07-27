import re

from django import forms

PHONE_RE = re.compile(r"^0(5|6|7)\d{8}$")

GENDER_CHOICES = [("", "—"), ("m", "ذكر"), ("f", "أنثى")]


class IndividualSubscribeForm(forms.Form):
    """Web-form counterpart of the API's IndividualRegistrationSerializer — used by
    the public /formations/.../inscription/ page for a single, private individual."""

    full_name = forms.CharField(label="الاسم واللقب", max_length=150)
    phone = forms.CharField(label="رقم الهاتف", max_length=20)
    email = forms.EmailField(label="البريد الإلكتروني", required=False)
    birth_date = forms.DateField(
        label="تاريخ الميلاد", required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    gender = forms.ChoiceField(label="الجنس", choices=GENDER_CHOICES, required=False)
    education_level = forms.CharField(label="المستوى الدراسي", max_length=100, required=False)
    wilaya = forms.CharField(label="الولاية", max_length=60, required=False, initial="سطيف")
    motivation = forms.CharField(
        label="ملاحظات", required=False, widget=forms.Textarea(attrs={"rows": 3}),
    )
    # Honeypot: real users never see or fill this (hidden via CSS in the template).
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_website(self):
        value = self.cleaned_data.get("website")
        if value:
            raise forms.ValidationError("تعذر إرسال الطلب.")
        return value

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip().replace(" ", "")
        if not PHONE_RE.match(phone):
            raise forms.ValidationError("رقم هاتف غير صالح، مثال: 0770123456")
        return phone
