from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from pages.sitemaps import StaticViewSitemap

sitemaps = {
    "static": StaticViewSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path(
        "api/", include("enrollment.api_urls")
    ),  # /api/sessions/, /api/offerings/, /api/register/...
    path(
        "api/pages/", include("pages.api_urls")
    ),  # /api/pages/branches/, /api/pages/specialties/...
    path("", include("enrollment.urls")),  # <-- أضف هذا قبل include("pages.urls")
    path("", include("pages.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
