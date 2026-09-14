"""django-import-export Resource classes for the `accounts` app.

`accounts` has no models of its own (see accounts/models.py) — it manages
django.contrib.auth's built-in User/Group models instead (see
accounts/admin.py's `ClientAwareUserAdmin`). These resources let staff
import/export Users and Groups from the admin (django-import-export must
be installed and "import_export" added to INSTALLED_APPS; wire these up
via `import_export.admin.ImportExportModelAdmin` on `ClientAwareUserAdmin`
and a `GroupAdmin` to enable the Import/Export buttons).
"""

from django.contrib.auth.models import Group, User
from import_export import fields, resources
from import_export.widgets import ManyToManyWidget


class GroupResource(resources.ModelResource):
    class Meta:
        model = Group
        import_id_fields = ("name",)
        fields = ("id", "name")


class UserResource(resources.ModelResource):
    # django.contrib.auth.models.Group has no globally-unique field other
    # than `name`, so match/export groups by name rather than pk — reads
    # naturally in a CSV ("Accountant,Staff") and survives a re-import
    # into a different database.
    groups = fields.Field(
        column_name="groups",
        attribute="groups",
        widget=ManyToManyWidget(Group, field="name", separator=","),
    )

    class Meta:
        model = User
        import_id_fields = ("username",)
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "date_joined",
            "last_login",
        )
        export_order = fields
