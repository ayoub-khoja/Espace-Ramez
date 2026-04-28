from django.contrib import admin

from .models import Reservation, Terrain


@admin.register(Terrain)
class TerrainAdmin(admin.ModelAdmin):
    list_display = ("nom", "type", "indoor", "prix_par_session", "actif", "created_at")
    list_filter = ("type", "indoor", "actif")
    search_fields = ("nom",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("date", "heure_debut", "heure_fin", "terrain", "client", "statut", "created_at")
    list_filter = ("statut", "date", "terrain")
    search_fields = ("client__username", "client__email", "terrain__nom")
    autocomplete_fields = ("terrain", "client")
