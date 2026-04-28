"""Modèles métier (MVT) — SQLite3 via ORM Django."""

from django.conf import settings
from django.db import models


class Terrain(models.Model):
    nom = models.CharField(max_length=120)
    type = models.CharField(max_length=60, default="Padel")
    indoor = models.BooleanField(default=True)
    prix_par_session = models.DecimalField(max_digits=7, decimal_places=2, default=45)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nom", "-created_at"]

    def __str__(self) -> str:
        return self.nom


class Reservation(models.Model):
    STATUS_CHOICES = [
        ("CONFIRMED", "Confirmed"),
        ("IN_PROGRESS", "In progress"),
        ("PENDING", "Pending"),
        ("CANCELLED", "Cancelled"),
    ]

    terrain = models.ForeignKey(Terrain, on_delete=models.PROTECT, related_name="reservations")
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-heure_debut", "-created_at"]

    def __str__(self) -> str:
        return f"{self.client} — {self.terrain} — {self.date} {self.heure_debut}-{self.heure_fin}"
