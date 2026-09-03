from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .services import activate_client_and_send_credentials

# Re-register auth's User so the same "Activate & send credentials" bulk
# action from ClientAdmin (TODO 1.4) is also available from the Users list
# — useful when staff land on /admin/auth/user/ directly.
admin.site.unregister(User)


@admin.register(User)
class ClientAwareUserAdmin(UserAdmin):
    actions = list(UserAdmin.actions or []) + ["activate_and_send_credentials"]

    @admin.action(description="✅ تفعيل الحساب وإرسال بيانات الدخول (كزبون)")
    def activate_and_send_credentials(self, request, queryset):
        ok_count = 0
        for user in queryset:
            client = getattr(user, "client", None)
            if client is None:
                self.message_user(
                    request,
                    f"{user.username}: هذا المستخدم غير مرتبط بأي زبون.",
                    level=messages.WARNING,
                )
                continue
            ok, message = activate_client_and_send_credentials(client)
            self.message_user(
                request, message, level=messages.SUCCESS if ok else messages.WARNING
            )
            if ok:
                ok_count += 1
        if ok_count:
            self.message_user(
                request,
                f"إجمالي: تم تفعيل {ok_count} حساب/حسابات بنجاح.",
                level=messages.INFO,
            )
