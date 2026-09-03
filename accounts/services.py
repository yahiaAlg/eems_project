"""Business logic behind the "Activate & send credentials" admin action
(TODO 1.4).

Kept out of admin.py so the exact same logic can be triggered from both
`enrollment.admin.ClientAdmin` (acting on `Client` rows) and
`accounts.admin`'s customized `UserAdmin` (acting on `User` rows) without
duplicating it.
"""

import secrets

from pages.emails import send_branded_mail


def activate_client_and_send_credentials(client):
    """Activate `client`'s linked login, generate a fresh password, and
    email the username + password to the client.

    The plaintext password only ever exists in memory here and in the one
    outgoing email — it is never logged, stored, or returned to the caller.

    Returns a `(ok, message)` tuple; `message` is a human-readable status
    line safe to show in the admin (never contains the password). Never
    raises: mail-server errors are reported as a failed result instead.
    """
    user = client.user
    if user is None:
        return False, f"{client.display_name}: لا يوجد حساب دخول مرتبط بهذا الزبون."

    recipient = client.email or user.email
    if not recipient:
        return (
            False,
            f"{client.display_name}: لا يوجد بريد إلكتروني لإرسال بيانات الدخول إليه.",
        )

    password = secrets.token_urlsafe(12)

    user.set_password(password)
    user.is_active = True
    user.save(update_fields=["password", "is_active"])

    client.account_status = "active"
    client.save(update_fields=["account_status", "updated_at"])

    sent = send_branded_mail(
        template="emails/account_activated_credentials.html",
        subject="تم تفعيل حسابك — بيانات الدخول",
        to=[recipient],
        context={
            "client_name": client.display_name,
            "username": user.username,
            "password": password,
        },
    )
    if not sent:
        return (
            False,
            f"{client.display_name}: تم التفعيل لكن تعذر إرسال بريد بيانات الدخول "
            f"إلى {recipient} — يرجى المحاولة يدويا.",
        )
    return True, f"{client.display_name}: تم التفعيل وإرسال بيانات الدخول إلى {recipient}."
