from django.contrib import admin

from .models import FormationLink


@admin.register(FormationLink)
class FormationLinkAdmin(admin.ModelAdmin):
    list_display = ("isi_formation_id", "offering", "created_by_sync", "updated_at")
    search_fields = ("offering__title", "offering__code")
    raw_id_fields = ("offering",)
