from django.apps import AppConfig


class PortalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portal"
    verbose_name = "Portail administrateur"

    def ready(self) -> None:
        from django.contrib import admin

        admin.site.site_header = "Espace Ramez — administration"
        admin.site.site_title = "Espace Ramez"
