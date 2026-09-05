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
    path("formations/<slug:session_slug>/<str:code>/panier/", views.add_to_cart, name="add_to_cart"),
    path("formations/<slug:session_slug>/<str:code>/liste-souhaits/", views.toggle_wishlist, name="toggle_wishlist"),
    path("inscription/merci/", views.subscribe_success, name="subscribe_success"),

    # Cart page (TODO 4.3) — list/edit/remove the logged-in client's queued items.
    path("mon-espace/panier/", views.cart, name="cart"),
    path("mon-espace/panier/<int:item_id>/modifier/", views.cart_update_item, name="cart_update_item"),
    path("mon-espace/panier/<int:item_id>/supprimer/", views.cart_remove_item, name="cart_remove_item"),

    # "Request Proforma" (TODO 5.1, VIP-only) — confirm billing basis per
    # line + optional bon de commande upload; submitting it persists a
    # ProformaInvoice (TODO 5.2) and redirects to its printable page below.
    path("mon-espace/panier/proforma/", views.request_proforma, name="request_proforma"),
    # Printable proforma invoice (TODO 5.2) — plain HTML + print CSS, no
    # PDF library; the client's browser handles "print / save as PDF".
    path("mon-espace/proforma/<int:pk>/", views.proforma_print, name="proforma_print"),

    # "Request Quote" (TODO 5.3, Non-VIP-only) — single confirm-and-submit
    # action on the cart: creates a QuoteRequest snapshot (offering +
    # participant_count only, no trainer/price/attachment).
    path("mon-espace/panier/devis/", views.request_quote, name="request_quote"),
    # Printable quote-turned-invoice document (TODO 6.4) — same plain-HTML
    # + print-CSS pattern as proforma_print above, once the accountant has
    # set every line's tariff (TODO 6.2/6.3).
    path("mon-espace/devis/<int:pk>/", views.quote_print, name="quote_print"),

    # Wishlist page (TODO 4.4) — saved-for-later offerings.
    path("mon-espace/liste-souhaits/", views.wishlist, name="wishlist"),
    path("mon-espace/liste-souhaits/<int:item_id>/supprimer/", views.wishlist_remove, name="wishlist_remove"),
    path("mon-espace/liste-souhaits/<int:item_id>/panier/", views.wishlist_move_to_cart, name="wishlist_move_to_cart"),
    path("advisor/", views.general_enquiry, name="general_enquiry"),

    # "مساحتي" — the subscriber's self-service dashboard (Django auth, see `accounts` app;
    # TODO 1.8 retired the old phone/session login — anonymous visitors are redirected
    # to accounts:login by the @login_required decorator on views.dashboard).
    path("mon-espace/", views.dashboard, name="dashboard"),
    path("mon-espace/profil/", views.profile, name="profile"),
    path("mon-espace/<int:pk>/confirmer/", views.dashboard_confirm, name="dashboard_confirm"),
    path("mon-espace/<int:pk>/annuler/", views.dashboard_cancel, name="dashboard_cancel"),

    # "مشترياتي" / "إحصائياتي" (TODO 4.5) — client-space nav tabs. My
    # Purchases surfaces confirmed enrollments today; Phase 5-8 will fold
    # proformas/quotes in once those models exist. Metrics are plain counts
    # until Phase 8.2 wires up the bundled Chart.js widgets.
    path("mon-espace/achats/", views.my_purchases, name="my_purchases"),
    path("mon-espace/statistiques/", views.metrics, name="metrics"),
]
