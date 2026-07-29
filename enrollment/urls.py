from django.urls import path

from . import views

app_name = "enrollment"

urlpatterns = [
    path("formations/", views.catalog, name="catalog"),
    path("formateurs/<str:slug>/", views.formateur_detail, name="formateur_detail"),
    path("formations/<slug:session_slug>/<str:code>/", views.specialty_detail, name="detail"),
    path("formations/<slug:session_slug>/<str:code>/inscription/", views.subscribe, name="subscribe"),
    path("inscription/merci/", views.subscribe_success, name="subscribe_success"),
    path("advisor/", views.general_enquiry, name="general_enquiry"),
]
