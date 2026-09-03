from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.cache import never_cache

from enrollment.models import Client
from pages.emails import send_branded_mail

from .forms import (
    EEMSAuthenticationForm,
    EEMSPasswordResetForm,
    EEMSSetPasswordForm,
    RegistrationForm,
)


class EEMSLoginView(LoginView):
    """Login under `/account/login/` (TODO 1.5) — the only way into
    'مساحتي' now that the legacy phone/session `enrollment.dashboard_login`
    has been retired (TODO 1.8)."""

    template_name = "accounts/login.html"
    authentication_form = EEMSAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, "تم تسجيل الدخول بنجاح.")
        return super().form_valid(form)


class EEMSLogoutView(LogoutView):
    """Logout under `/account/logout/` (POST-only, per Django's default).
    `next_page` mirrors the retired `enrollment.dashboard_logout` behaviour
    (TODO 1.8) of always landing back on the homepage with a confirmation
    message. `enrollment/dashboard.html`'s logout button posts here."""

    next_page = "pages:home"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, "تم تسجيل خروجك.")
        return response


class EEMSPasswordResetView(PasswordResetView):
    """"Forgot password" — step 1: request the reset email (TODO 1.6).

    Reuses `pages/templates/emails/base_email.html` for the branded HTML
    version of the email (see `emails/password_reset_email.html`), with a
    plain-text fallback for clients that can't render HTML.
    """

    template_name = "accounts/password_reset_form.html"
    form_class = EEMSPasswordResetForm
    email_template_name = "emails/password_reset_email.txt"
    html_email_template_name = "emails/password_reset_email.html"
    subject_template_name = "emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    extra_email_context = {
        "site_name": "إيمس — مؤسسة التميز للإدارة والأمن",
        "site_url": "https://excellance-ms.dz",
    }


class EEMSPasswordResetDoneView(PasswordResetDoneView):
    """Step 2: "check your inbox" confirmation page."""

    template_name = "accounts/password_reset_done.html"


class EEMSPasswordResetConfirmView(PasswordResetConfirmView):
    """Step 3: the link from the email lands here to set a new password."""

    template_name = "accounts/password_reset_confirm.html"
    form_class = EEMSSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")


class EEMSPasswordResetCompleteView(PasswordResetCompleteView):
    """Step 4: success page, links back to `/account/login/`."""

    template_name = "accounts/password_reset_complete.html"


@never_cache
def register(request):
    """Public 'create an account' view — individual or enterprise.

    On submit: creates a `User(is_active=False)` (no usable password yet)
    plus a linked `Client(account_status="pending")`, then notifies the
    admin inbox. Activation + credential email is a separate step (TODO
    1.4), not done here.
    """
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            client_type = data["client_type"]
            is_individual = client_type != "enterprise"

            with transaction.atomic():
                user = User(username=data["phone"], email=data["email"], is_active=False)
                user.set_unusable_password()
                user.save()

                client = Client.objects.create(
                    user=user,
                    client_type=client_type,
                    phone=data["phone"],
                    email=data["email"],
                    wilaya=data.get("wilaya") or "سطيف",
                    address=data.get("address", ""),
                    full_name=data.get("full_name", "") if is_individual else "",
                    birth_date=data.get("birth_date") if is_individual else None,
                    gender=data.get("gender", "") if is_individual else "",
                    education_level=data.get("education_level", "") if is_individual else "",
                    company_name=data.get("company_name", "") if not is_individual else "",
                    trade_register_number=(
                        data.get("trade_register_number", "") if not is_individual else ""
                    ),
                    sector=data.get("sector", "") if not is_individual else "",
                    responsible_name=data.get("responsible_name", "") if not is_individual else "",
                    responsible_position=(
                        data.get("responsible_position", "") if not is_individual else ""
                    ),
                    account_status="pending",
                )

            # Notify admins/support inbox — same pattern as
            # enrollment.signals.notify_staff_on_new_enrollment.
            admin_emails = [addr for _name, addr in getattr(settings, "ADMINS", [])]
            if admin_emails:
                send_branded_mail(
                    template="emails/account_pending_admin_notification.html",
                    subject=f"حساب جديد بانتظار الموافقة: {client.display_name}",
                    to=admin_emails,
                    context={
                        "client_name": client.display_name,
                        "client_type": client.get_client_type_display(),
                        "phone": client.phone,
                        "email": client.email,
                    },
                )

            return redirect("accounts:register_success")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@never_cache
def register_success(request):
    return render(request, "accounts/register_success.html")
