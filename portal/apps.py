from django.apps import AppConfig
import os


class PortalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portal"
    verbose_name = "Portail administrateur"

    def ready(self) -> None:
        from django.contrib import admin

        admin.site.site_header = "Espace Ramez — administration"
        admin.site.site_title = "Espace Ramez"

        # Render/production: garantir un admin si les variables sont fournies.
        username = (os.environ.get("DJANGO_ADMIN_USERNAME") or "").strip()
        email = (os.environ.get("DJANGO_ADMIN_EMAIL") or "").strip()
        password = os.environ.get("DJANGO_ADMIN_PASSWORD") or ""
        if not username or not email or not password:
            return

        try:
            from django.contrib.auth import get_user_model
            from django.db import OperationalError, ProgrammingError

            User = get_user_model()
            u = User.objects.filter(username__iexact=username).first()
            if not u:
                User.objects.create_superuser(username=username, email=email, password=password)
            else:
                if not u.is_staff:
                    u.is_staff = True
                if not u.is_superuser:
                    u.is_superuser = True
                if email and (u.email or "").lower() != email.lower():
                    u.email = email
                u.set_password(password)
                u.save()
        except (OperationalError, ProgrammingError):
            return
