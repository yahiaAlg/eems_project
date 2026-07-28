from django import forms

from .models import NewsletterSubscriber, ContactMessage


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "بريدك الإلكتروني",
                    "dir": "ltr",
                }
            )
        }
        labels = {"email": "البريد الإلكتروني"}


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "الاسم الكامل"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "بريدك الإلكتروني", "dir": "ltr"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "رقم الهاتف (اختياري)", "dir": "ltr"}
            ),
            "subject": forms.Select(attrs={"class": "form-select"}),
            "message": forms.Textarea(
                attrs={"class": "form-control", "placeholder": "اكتب رسالتك هنا...", "rows": 5}
            ),
        }
        labels = {
            "name": "الاسم الكامل",
            "email": "البريد الإلكتروني",
            "phone": "الهاتف",
            "subject": "الموضوع",
            "message": "الرسالة",
        }
