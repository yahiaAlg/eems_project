from django.urls import path

from . import views

app_name = "enrollment"

urlpatterns = [
    path("formations/", views.catalog, name="catalog"),
    path("formateurs/<str:slug>/", views.formateur_detail, name="formateur_detail"),
    path("formateurs/<str:slug>/cv/", views.formateur_cv_print, name="formateur_cv"),
    path("formations/<slug:session_slug>/<str:code>/", views.specialty_detail, name="detail"),
    path("formations/<slug:session_slug>/<str:code>/fiche-technique/", views.fiche_technique_print, name="fiche_technique"),
    path("formations/<slug:session_slug>/<str:code>/inscription/", views.subscribe, name="subscribe"),
    path("inscription/merci/", views.subscribe_success, name="subscribe_success"),
    path("advisor/", views.general_enquiry, name="general_enquiry"),
]
