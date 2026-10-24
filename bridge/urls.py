from django.urls import path

from . import views

app_name = "bridge"

urlpatterns = [
    path("internal/sync/ping/", views.ping, name="ping"),
    path("internal/sync/formation/", views.formation_upsert, name="formation_upsert"),
]
