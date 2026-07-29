from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from enrollment.models import Formateur, Offering


class StaticViewSitemap(Sitemap):
    protocol = "https"

    def items(self):
        # Each item: (url_name, priority, changefreq)
        return [
            ("pages:home", 1.0, "weekly"),
            ("pages:about", 0.7, "monthly"),
            ("pages:faq", 0.6, "monthly"),
            ("pages:contact", 0.6, "monthly"),
            ("pages:nomenclature", 0.8, "monthly"),
            ("enrollment:catalog", 0.9, "daily"),
        ]

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]


class OfferingSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Offering.objects.filter(is_active=True, session__is_active=True).select_related("session")

    def location(self, obj):
        return obj.get_absolute_url()


class FormateurSitemap(Sitemap):
    protocol = "https"
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return Formateur.objects.filter(is_active=True)

    def location(self, obj):
        return obj.get_absolute_url()
