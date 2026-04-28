"""Crée ou met à jour un compte client de test (SQLite)."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Crée l'utilisateur client / client si absent. "
        "Utilisez --reset pour forcer le mot de passe."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Réinitialise le mot de passe à « client » si le compte existe déjà.",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        reset = options["reset"]
        username = "client"
        email = "client@espaceramez.tn"
        password = "client"

        existing = User.objects.filter(username__iexact=username).first()
        if existing:
            if reset:
                existing.set_password(password)
                existing.email = email
                existing.is_staff = False
                existing.is_superuser = False
                existing.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Mot de passe réinitialisé pour « {username} » (connexion : {username} ou {email} / {password}).",
                    ),
                )
                return
            self.stdout.write(
                self.style.WARNING(
                    f"L'utilisateur « {username} » existe déjà. Lancez : python manage.py seed_client --reset",
                ),
            )
            return

        User.objects.create_user(username=username, email=email, password=password)
        self.stdout.write(
            self.style.SUCCESS(
                f"Compte client créé : identifiant « {username} » ou e-mail « {email} », mot de passe « {password} ».",
            ),
        )

