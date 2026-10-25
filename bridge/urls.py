from django.urls import path

from . import views

app_name = "bridge"

urlpatterns = [
    path("formations/", views.formations_upsert, name="formations_upsert"),
    path("formations/deactivate/", views.formations_deactivate, name="formations_deactivate"),
    path("feed/", views.feed, name="feed"),
]
