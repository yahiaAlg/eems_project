"""django-import-export Resource classes for every concrete model in the
`pages` app (django-import-export must be installed and "import_export"
added to INSTALLED_APPS; wire a resource onto an app's ModelAdmin by
subclassing `import_export.admin.ImportExportModelAdmin` and setting
`resource_classes = [XResource]`).

`SingletonModel` (models.py) is abstract and has no resource of its own —
its two concrete subclasses (`SiteSettings`, `AboutPage`) are listed below.
"""

from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from .models import (
    AboutPage,
    AboutValue,
    Branch,
    CarouselImage,
    ContactMessage,
    ContactPageSettings,
    FAQCategory,
    FAQItem,
    HeroStat,
    InternalApp,
    MissionCard,
    Milestone,
    NavLink,
    NewsletterSubscriber,
    Partner,
    ProcessStep,
    SiteSettings,
    SiteVisitor,
    SocialLink,
    Specialty,
    Testimonial,
    TrainingSession,
)


# ──────────────────────────────────────────────────────────────────
#  Visitor counter
# ──────────────────────────────────────────────────────────────────
class SiteVisitorResource(resources.ModelResource):
    class Meta:
        model = SiteVisitor
        import_id_fields = ("ip_hash", "date")


# ──────────────────────────────────────────────────────────────────
#  SiteSettings — singleton
# ──────────────────────────────────────────────────────────────────
class SiteSettingsResource(resources.ModelResource):
    class Meta:
        model = SiteSettings


# ──────────────────────────────────────────────────────────────────
#  Hero statistics / mission cards / carousel
# ──────────────────────────────────────────────────────────────────
class HeroStatResource(resources.ModelResource):
    class Meta:
        model = HeroStat


class MissionCardResource(resources.ModelResource):
    class Meta:
        model = MissionCard


class CarouselImageResource(resources.ModelResource):
    class Meta:
        model = CarouselImage


# ──────────────────────────────────────────────────────────────────
#  Catalogue: professional Branches & Specialties
# ──────────────────────────────────────────────────────────────────
class BranchResource(resources.ModelResource):
    class Meta:
        model = Branch
        import_id_fields = ("code",)


class SpecialtyResource(resources.ModelResource):
    branch = fields.Field(
        column_name="branch",
        attribute="branch",
        widget=ForeignKeyWidget(Branch, field="code"),
    )

    class Meta:
        model = Specialty
        import_id_fields = ("code",)


# ──────────────────────────────────────────────────────────────────
#  Upcoming training sessions
# ──────────────────────────────────────────────────────────────────
class TrainingSessionResource(resources.ModelResource):
    branch = fields.Field(
        column_name="branch",
        attribute="branch",
        widget=ForeignKeyWidget(Branch, field="code"),
    )

    class Meta:
        model = TrainingSession


# ──────────────────────────────────────────────────────────────────
#  Social links / internal apps / footer nav / partners / process steps
# ──────────────────────────────────────────────────────────────────
class SocialLinkResource(resources.ModelResource):
    class Meta:
        model = SocialLink


class InternalAppResource(resources.ModelResource):
    class Meta:
        model = InternalApp


class NavLinkResource(resources.ModelResource):
    class Meta:
        model = NavLink


class PartnerResource(resources.ModelResource):
    class Meta:
        model = Partner


class ProcessStepResource(resources.ModelResource):
    class Meta:
        model = ProcessStep


# ──────────────────────────────────────────────────────────────────
#  Testimonials / newsletter
# ──────────────────────────────────────────────────────────────────
class TestimonialResource(resources.ModelResource):
    class Meta:
        model = Testimonial


class NewsletterSubscriberResource(resources.ModelResource):
    class Meta:
        model = NewsletterSubscriber
        import_id_fields = ("email",)


# ──────────────────────────────────────────────────────────────────
#  About page — singleton + values & milestones
# ──────────────────────────────────────────────────────────────────
class AboutPageResource(resources.ModelResource):
    class Meta:
        model = AboutPage


class AboutValueResource(resources.ModelResource):
    class Meta:
        model = AboutValue


class MilestoneResource(resources.ModelResource):
    class Meta:
        model = Milestone


# ──────────────────────────────────────────────────────────────────
#  FAQ page — categories + items
# ──────────────────────────────────────────────────────────────────
class FAQCategoryResource(resources.ModelResource):
    class Meta:
        model = FAQCategory
        import_id_fields = ("name",)


class FAQItemResource(resources.ModelResource):
    category = fields.Field(
        column_name="category",
        attribute="category",
        widget=ForeignKeyWidget(FAQCategory, field="name"),
    )

    class Meta:
        model = FAQItem


# ──────────────────────────────────────────────────────────────────
#  Contact page — singleton + incoming messages
# ──────────────────────────────────────────────────────────────────
class ContactPageSettingsResource(resources.ModelResource):
    class Meta:
        model = ContactPageSettings


class ContactMessageResource(resources.ModelResource):
    class Meta:
        model = ContactMessage
