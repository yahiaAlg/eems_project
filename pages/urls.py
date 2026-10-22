from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("robots.txt", views.robots, name="robots"),
    path("nomenclature/", views.nomenclature, name="nomenclature"),
    path("newsletter/", views.newsletter_subscribe, name="newsletter_subscribe"),
    path("about/", views.about, name="about"),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    # Attestation QR gateway — see views.verify_gateway
    path("internal/institute-ping/", views.institute_ping, name="institute_ping"),
    path("v/", views.verify_gateway, name="verify_gateway_empty"),
    path("v/<str:code>/", views.verify_gateway, name="verify_gateway"),
]
