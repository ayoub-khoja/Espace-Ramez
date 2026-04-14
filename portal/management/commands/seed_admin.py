"""Crée ou met à jour le compte administrateur par défaut (SQLite)."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crée l'utilisateur admin / admin si absent. Utilisez --reset pour forcer le mot de passe."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Réinitialise le mot de passe à « admin » si le compte existe déjà.",
        )

    def handle(self, *args, **options):
        reset = options["reset"]
        username = "admin"
        email = "admin@espaceramez.tn"
        password = "admin"

        existing = User.objects.filter(username__iexact=username).first()
        if existing:
            if reset:
                existing.set_password(password)
                existing.email = email
                existing.is_staff = True
                existing.is_superuser = True
                existing.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Mot de passe réinitialisé pour « {username} » (connexion : {username} ou {email} / {password}).",
                    ),
                )
                return
            self.stdout.write(
                self.style.WARNING(
                    f"L'utilisateur « {username} » existe déjà. Lancez : python manage.py seed_admin --reset",
                ),
            )
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(
            self.style.SUCCESS(
                f"Compte créé : identifiant « {username} » ou e-mail « {email} », mot de passe « {password} ».",
            ),
        )
