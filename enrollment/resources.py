"""django-import-export Resource classes for every concrete model in the
`enrollment` app (django-import-export must be installed and
"import_export" added to INSTALLED_APPS; wire a resource onto an app's
ModelAdmin by subclassing `import_export.admin.ImportExportModelAdmin`
and setting `resource_classes = [XResource]`).

`AttachmentBase` (models.py) is abstract and has no resource of its own —
its two concrete subclasses (`FormateurCertificate`, `OfferingAttachment`)
are listed below instead.

FK widgets below match on a human-readable natural key wherever the
target model has one (slug/code/reference/username) so exported CSVs stay
legible and re-import cleanly into another database; models with no such
field (e.g. `Client`, `Offering`'s row-level related lines) fall back to
the default pk-based widget.
"""

from django.contrib.auth.models import User
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from pages.models import Specialty

from .models import (
    Cart,
    CartItem,
    Client,
    Comment,
    Enquiry,
    Enrollment,
    EnrollmentNote,
    EnrollmentParticipant,
    Formateur,
    FormateurCareerEntry,
    FormateurCertificate,
    FormationSession,
    Offering,
    OfferingAttachment,
    OfferingImage,
    Participant,
    ProformaInvoice,
    ProformaInvoiceItem,
    QuoteRequest,
    QuoteRequestItem,
    SessionChangeRequest,
    WishlistItem,
)


# ──────────────────────────────────────────────────────────────────
#  Formateurs (trainers)
# ──────────────────────────────────────────────────────────────────
class FormateurResource(resources.ModelResource):
    class Meta:
        model = Formateur
        import_id_fields = ("slug",)


class FormateurCertificateResource(resources.ModelResource):
    formateur = fields.Field(
        column_name="formateur",
        attribute="formateur",
        widget=ForeignKeyWidget(Formateur, field="slug"),
    )

    class Meta:
        model = FormateurCertificate


class FormateurCareerEntryResource(resources.ModelResource):
    formateur = fields.Field(
        column_name="formateur",
        attribute="formateur",
        widget=ForeignKeyWidget(Formateur, field="slug"),
    )

    class Meta:
        model = FormateurCareerEntry


# ──────────────────────────────────────────────────────────────────
#  Formation sessions / offerings
# ──────────────────────────────────────────────────────────────────
class FormationSessionResource(resources.ModelResource):
    class Meta:
        model = FormationSession
        import_id_fields = ("slug",)


class OfferingResource(resources.ModelResource):
    session = fields.Field(
        column_name="session",
        attribute="session",
        widget=ForeignKeyWidget(FormationSession, field="slug"),
    )
    specialty = fields.Field(
        column_name="specialty",
        attribute="specialty",
        widget=ForeignKeyWidget(Specialty, field="code"),
    )
    formateur = fields.Field(
        column_name="formateur",
        attribute="formateur",
        widget=ForeignKeyWidget(Formateur, field="slug"),
    )

    class Meta:
        model = Offering
        # `code` is only unique per-session (see Meta.unique_together on
        # the model), so the pair together makes a stable natural key.
        import_id_fields = ("session", "code")


class OfferingImageResource(resources.ModelResource):
    offering = fields.Field(
        column_name="offering",
        attribute="offering",
        widget=ForeignKeyWidget(Offering, field="id"),
    )

    class Meta:
        model = OfferingImage


class OfferingAttachmentResource(resources.ModelResource):
    offering = fields.Field(
        column_name="offering",
        attribute="offering",
        widget=ForeignKeyWidget(Offering, field="id"),
    )

    class Meta:
        model = OfferingAttachment


# ──────────────────────────────────────────────────────────────────
#  Clients & participants
# ──────────────────────────────────────────────────────────────────
class ClientResource(resources.ModelResource):
    class Meta:
        model = Client


class ParticipantResource(resources.ModelResource):
    client = fields.Field(
        column_name="client",
        attribute="client",
        widget=ForeignKeyWidget(Client, field="id"),
    )

    class Meta:
        model = Participant


# ──────────────────────────────────────────────────────────────────
#  Enrollments
# ──────────────────────────────────────────────────────────────────
class EnrollmentResource(resources.ModelResource):
    client = fields.Field(
        column_name="client",
        attribute="client",
        widget=ForeignKeyWidget(Client, field="id"),
    )
    participant = fields.Field(
        column_name="participant",
        attribute="participant",
        widget=ForeignKeyWidget(Participant, field="id"),
    )
    offering = fields.Field(
        column_name="offering",
        attribute="offering",
        widget=ForeignKeyWidget(Offering, field="id"),
    )
    handled_by = fields.Field(
        column_name="handled_by",
        attribute="handled_by",
        widget=ForeignKeyWidget(User, field="username"),
    )

    class Meta:
        model = Enrollment


class EnrollmentNoteResource(resources.ModelResource):
    enrollment = fields.Field(
        column_name="enrollment",
        attribute="enrollment",
        widget=ForeignKeyWidget(Enrollment, field="id"),
    )
    author = fields.Field(
        column_name="author",
        attribute="author",
        widget=ForeignKeyWidget(User, field="username"),
    )

    class Meta:
        model = EnrollmentNote


class SessionChangeRequestResource(resources.ModelResource):
    enrollment = fields.Field(
        column_name="enrollment",
        attribute="enrollment",
        widget=ForeignKeyWidget(Enrollment, field="id"),
    )
    reviewed_by = fields.Field(
        column_name="reviewed_by",
        attribute="reviewed_by",
        widget=ForeignKeyWidget(User, field="username"),
    )

    class Meta:
        model = SessionChangeRequest


class EnrollmentParticipantResource(resources.ModelResource):
    # Field set deliberately mirrors formations.Participant on the
    # isi_pedagogical_webapp side (see the model's docstring) — kept as
    # the full default field set here (no `fields`/widget override) so a
    # CSV export round-trips unchanged.
    enrollment = fields.Field(
        column_name="enrollment",
        attribute="enrollment",
        widget=ForeignKeyWidget(Enrollment, field="id"),
    )

    class Meta:
        model = EnrollmentParticipant


# ──────────────────────────────────────────────────────────────────
#  Cart, cart items & wishlist
# ──────────────────────────────────────────────────────────────────
class CartResource(resources.ModelResource):
    client = fields.Field(
        column_name="client",
        attribute="client",
        widget=ForeignKeyWidget(Client, field="id"),
    )

    class Meta:
        model = Cart


class CartItemResource(resources.ModelResource):
    cart = fields.Field(
        column_name="cart",
        attribute="cart",
        widget=ForeignKeyWidget(Cart, field="id"),
    )
    offering = fields.Field(
        column_name="offering",
        attribute="offering",
        widget=ForeignKeyWidget(Offering, field="id"),
    )
    trainer = fields.Field(
        column_name="trainer",
        attribute="trainer",
        widget=ForeignKeyWidget(Formateur, field="slug"),
    )

    class Meta:
        model = CartItem


class WishlistItemResource(resources.ModelResource):
    client = fields.Field(
        column_name="client",
        attribute="client",
        widget=ForeignKeyWidget(Client, field="id"),
    )
    offering = fields.Field(
        column_name="offering",
        attribute="offering",
        widget=ForeignKeyWidget(Offering, field="id"),
    )

    class Meta:
        model = WishlistItem


# ──────────────────────────────────────────────────────────────────
#  Proforma invoices (VIP checkout)
# ──────────────────────────────────────────────────────────────────
class ProformaInvoiceResource(resources.ModelResource):
    client = fields.Field(
        column_name="client",
        attribute="client",
        widget=ForeignKeyWidget(Client, field="id"),
    )

    class Meta:
        model = ProformaInvoice
        import_id_fields = ("reference",)


class ProformaInvoiceItemResource(resources.ModelResource):
    invoice = fields.Field(
        column_name="invoice",
        attribute="invoice",
        widget=ForeignKeyWidget(ProformaInvoice, field="reference"),
    )
    offering = fields.Field(
        column_name="offering",
        attribute="offering",
        widget=ForeignKeyWidget(Offering, field="id"),
    )
    trainer = fields.Field(
        column_name="trainer",
        attribute="trainer",
        widget=ForeignKeyWidget(Formateur, field="slug"),
    )

    class Meta:
        model = ProformaInvoiceItem


# ──────────────────────────────────────────────────────────────────
#  Quote requests (non-VIP checkout)
# ──────────────────────────────────────────────────────────────────
class QuoteRequestResource(resources.ModelResource):
    client = fields.Field(
        column_name="client",
        attribute="client",
        widget=ForeignKeyWidget(Client, field="id"),
    )

    class Meta:
        model = QuoteRequest
        import_id_fields = ("reference",)


class QuoteRequestItemResource(resources.ModelResource):
    quote = fields.Field(
        column_name="quote",
        attribute="quote",
        widget=ForeignKeyWidget(QuoteRequest, field="reference"),
    )
    offering = fields.Field(
        column_name="offering",
        attribute="offering",
        widget=ForeignKeyWidget(Offering, field="id"),
    )

    class Meta:
        model = QuoteRequestItem


# ──────────────────────────────────────────────────────────────────
#  Public comments & enquiries
# ──────────────────────────────────────────────────────────────────
class CommentResource(resources.ModelResource):
    offering = fields.Field(
        column_name="offering",
        attribute="offering",
        widget=ForeignKeyWidget(Offering, field="id"),
    )

    class Meta:
        model = Comment


class EnquiryResource(resources.ModelResource):
    offering = fields.Field(
        column_name="offering",
        attribute="offering",
        widget=ForeignKeyWidget(Offering, field="id"),
    )
    answered_by = fields.Field(
        column_name="answered_by",
        attribute="answered_by",
        widget=ForeignKeyWidget(User, field="username"),
    )

    class Meta:
        model = Enquiry
