from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("register/merci/", views.register_success, name="register_success"),
    path("login/", views.EEMSLoginView.as_view(), name="login"),
    path("logout/", views.EEMSLogoutView.as_view(), name="logout"),
    path(
        "password-reset/",
        views.EEMSPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        views.EEMSPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        views.EEMSPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        views.EEMSPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
