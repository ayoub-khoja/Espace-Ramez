"""Crée/met à jour un superuser via variables d'environnement.

Pensé pour Render (sans shell) : on l'exécute dans build.sh après migrate.
"""

from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crée/met à jour un superuser via DJANGO_ADMIN_* (idempotent)."

    def handle(self, *args, **options):
        username = (os.environ.get("DJANGO_ADMIN_USERNAME") or "").strip()
        email = (os.environ.get("DJANGO_ADMIN_EMAIL") or "").strip()
        password = os.environ.get("DJANGO_ADMIN_PASSWORD") or ""

        if not username or not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "ensure_admin: variables manquantes (DJANGO_ADMIN_USERNAME/EMAIL/PASSWORD). Skip."
                )
            )
            return

        User = get_user_model()
        u = User.objects.filter(username__iexact=username).first()
        if not u:
            u = User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"ensure_admin: superuser créé: {username}"))
            return

        changed = False
        if not u.is_staff:
            u.is_staff = True
            changed = True
        if not u.is_superuser:
            u.is_superuser = True
            changed = True
        if email and (u.email or "").strip().lower() != email.lower():
            u.email = email
            changed = True

        # On met à jour le mot de passe à chaque déploiement (simple et fiable).
        u.set_password(password)
        changed = True

        if changed:
            u.save()
            self.stdout.write(self.style.SUCCESS(f"ensure_admin: superuser mis à jour: {username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"ensure_admin: rien à faire pour {username}"))

