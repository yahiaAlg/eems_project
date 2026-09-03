from django.urls import path

from . import views

app_name = "enrollment"

urlpatterns = [
    path("formations/", views.catalog, name="catalog"),
    path("formations/inscription/", views.subscribe_general, name="subscribe_general"),
    path("formations/ajax/specialites/", views.ajax_specialties_for_branch, name="ajax_specialties"),
    path("formations/ajax/offres/", views.ajax_offerings_for_specialty, name="ajax_offerings"),
    path("formateurs/<str:slug>/", views.formateur_detail, name="formateur_detail"),
    path("formateurs/<str:slug>/cv/", views.formateur_cv_print, name="formateur_cv"),
    path("formations/<slug:session_slug>/<str:code>/", views.specialty_detail, name="detail"),
    path("formations/<slug:session_slug>/<str:code>/fiche-technique/", views.fiche_technique_print, name="fiche_technique"),
    path("formations/<slug:session_slug>/<str:code>/inscription/", views.subscribe, name="subscribe"),
    path("inscription/merci/", views.subscribe_success, name="subscribe_success"),
    path("advisor/", views.general_enquiry, name="general_enquiry"),

    # "مساحتي" — the subscriber's self-service dashboard (Django auth, see `accounts` app;
    # TODO 1.8 retired the old phone/session login — anonymous visitors are redirected
    # to accounts:login by the @login_required decorator on views.dashboard).
    path("mon-espace/", views.dashboard, name="dashboard"),
    path("mon-espace/<int:pk>/confirmer/", views.dashboard_confirm, name="dashboard_confirm"),
    path("mon-espace/<int:pk>/annuler/", views.dashboard_cancel, name="dashboard_cancel"),
]
