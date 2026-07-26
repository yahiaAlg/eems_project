from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    protocol = "https"

    def items(self):
        # Each item: (url_name, priority, changefreq)
        return [
            ("pages:home", 1.0, "weekly"),
            ("pages:nomenclature", 0.8, "monthly"),
        ]

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]
