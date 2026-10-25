from django.contrib import admin

from .models import FormationLink


@admin.register(FormationLink)
class FormationLinkAdmin(admin.ModelAdmin):
    list_display = ("isi_formation_id", "offering", "is_published", "created_from_isi", "last_synced_at")
    list_filter = ("offering__is_active",)
    search_fields = ("offering__title", "offering__code")
    readonly_fields = ("isi_formation_id", "offering", "last_payload", "created_from_isi", "last_synced_at")

    actions = ["publish"]

    @admin.display(boolean=True, description="Publiée")
    def is_published(self, obj):
        return obj.offering.is_active

    @admin.action(description="Publier les offres sélectionnées (visibles sur le site)")
    def publish(self, request, queryset):
        n = 0
        for link in queryset.select_related("offering"):
            if not link.offering.is_active:
                link.offering.is_active = True
                link.offering.save()
                n += 1
        self.message_user(request, f"{n} offre(s) publiée(s).")

    def has_add_permission(self, request):
        return False
