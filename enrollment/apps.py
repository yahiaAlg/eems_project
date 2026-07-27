from django.apps import AppConfig


class EnrollmentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "enrollment"
    verbose_name = "التسجيلات والدخول المهني"

    def ready(self):
        from . import signals  # noqa: F401
