from django.urls import path
from django.views.generic.base import RedirectView

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.home, name="home"),
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
    path("tableau-de-bord/", views.DashboardView.as_view(), name="dashboard"),
    # Next.js normalise souvent les URLs API sans slash final -> on supporte les deux.
    path("api/auth/logout", views.api_auth_logout, name="api_auth_logout_noslash"),
    path("api/auth/logout/", views.api_auth_logout, name="api_auth_logout"),
    path("api/auth/me", views.api_auth_me, name="api_auth_me_noslash"),
    path("api/auth/me/", views.api_auth_me, name="api_auth_me"),
    path("inscription/", views.client_signup, name="client_signup"),
]
