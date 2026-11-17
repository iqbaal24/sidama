from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit Log"

    def ready(self):
        # Register signal handlers only after every app registry is ready.
        from apps.audit.services import register_signals

        register_signals()
