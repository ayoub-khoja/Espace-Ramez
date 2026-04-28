from django.urls import path
from django.views.generic.base import RedirectView

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.public_home, name="home"),
    # Pages client (Django templates "comme frontend")
    path("reservation/", views.ClientReservationView.as_view(), name="client_reservation"),
    path("contact/", views.ClientContactView.as_view(), name="client_contact"),
    path("panier/", views.ClientPanierView.as_view(), name="client_panier"),
    path("offres/", views.ClientOffresView.as_view(), name="client_offres"),
    # Login client (public)
    path("login/", views.ClientLoginView.as_view(), name="login"),
    # Login admin (portail)
    path("admin/login/", views.PortalLoginView.as_view(), name="admin_login"),
    path(
        "admin/login-legacy/",
        RedirectView.as_view(
            pattern_name="login",
            permanent=False,
            query_string=True,
        ),
    ),
    path(
        "connexion/",
        RedirectView.as_view(
            pattern_name="login",
            permanent=False,
            query_string=True,
        ),
    ),
    path("deconnexion/", views.PortalLogoutView.as_view(), name="logout"),
    # Logout client (site public)
    path("client/deconnexion/", views.client_logout, name="client_logout"),
    path("tableau-de-bord/", views.DashboardView.as_view(), name="dashboard"),
    path("reservations/", views.ReservationsAdminView.as_view(), name="reservations_admin"),
    # CRUD (Django templates + Bootstrap)
    path("terrains/", views.TerrainListView.as_view(), name="terrain_list"),
    path("terrains/ajouter/", views.TerrainCreateView.as_view(), name="terrain_create"),
    path("terrains/<int:pk>/modifier/", views.TerrainUpdateView.as_view(), name="terrain_update"),
    path("terrains/<int:pk>/supprimer/", views.TerrainDeleteView.as_view(), name="terrain_delete"),

    path("reservations-crud/", views.ReservationListView.as_view(), name="reservation_list"),
    path("reservations-crud/ajouter/", views.ReservationCreateView.as_view(), name="reservation_create"),
    path("reservations-crud/<int:pk>/modifier/", views.ReservationUpdateView.as_view(), name="reservation_update"),
    path("reservations-crud/<int:pk>/supprimer/", views.ReservationDeleteView.as_view(), name="reservation_delete"),
    # Next.js normalise souvent les URLs API sans slash final -> on supporte les deux.
    path("api/auth/logout", views.api_auth_logout, name="api_auth_logout_noslash"),
    path("api/auth/logout/", views.api_auth_logout, name="api_auth_logout"),
    path("api/auth/me", views.api_auth_me, name="api_auth_me_noslash"),
    path("api/auth/me/", views.api_auth_me, name="api_auth_me"),
    path("inscription/", views.client_signup, name="client_signup"),
]
