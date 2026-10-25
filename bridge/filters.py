from django.contrib import admin


class AwaitingReviewFilter(admin.SimpleListFilter):
    """Offerings created from ISI that staff still have to review and publish."""

    title = "مزامنة ISI"
    parameter_name = "isi_review"

    def lookups(self, request, model_admin):
        return [
            ("1", "بانتظار المراجعة والنشر (من ISI)"),
            ("2", "كل العروض القادمة من ISI"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(
                isi_link__created_from_isi=True, isi_link__deleted_in_isi=False, is_active=False
            )
        if self.value() == "2":
            return queryset.filter(isi_link__isnull=False)
        return queryset
