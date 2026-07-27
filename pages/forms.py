from django import forms

from .models import NewsletterSubscriber


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
