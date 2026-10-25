from django.apps import AppConfig


class BridgeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bridge"
    verbose_name = "Pont avec l'application pédagogique (ISI)"

    def ready(self):
        from . import signals  # noqa: F401
