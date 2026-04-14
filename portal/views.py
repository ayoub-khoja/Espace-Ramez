"""Vues MVT du portail administrateur."""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

User = get_user_model()


@dataclass
class SignupErrors:
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    password1: str | None = None
    password2: str | None = None
    non_field: str | None = None


def home(request):
    """Racine : renvoie vers le tableau de bord ou la connexion."""
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    return redirect("portal:admin_login")


class PortalLoginView(LoginView):
    """Vue — formulaire de connexion (template MVT)."""

    template_name = "portal/login.html"
    redirect_authenticated_user = True
    next_page = reverse_lazy("portal:dashboard")


class ClientLoginView(LoginView):
    """Vue — formulaire de connexion client (template MVT)."""

    template_name = "portal/client_login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        # Après connexion client, on renvoie vers l'accueil client (Next).
        return self.get_redirect_url() or "/client"


def client_signup(request):
    """
    Inscription client (simple).

    - GET : affiche la carte d'inscription (flip)
    - POST : crée un utilisateur Django puis connecte la session
    """
    if request.user.is_authenticated:
        return redirect("/client")

    if request.method == "GET":
        return render(request, "portal/client_login.html", {"show_signup": True})

    first_name = (request.POST.get("first_name") or "").strip()
    last_name = (request.POST.get("last_name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    password1 = request.POST.get("password1") or ""
    password2 = request.POST.get("password2") or ""

    errors = SignupErrors()

    if not first_name:
        errors.first_name = "Le prénom est requis."
    if not last_name:
        errors.last_name = "Le nom est requis."
    if not email or "@" not in email:
        errors.email = "Une adresse e-mail valide est requise."
    if not password1:
        errors.password1 = "Le mot de passe est requis."
    if password1 != password2:
        errors.password2 = "Les mots de passe ne correspondent pas."

    if email and User.objects.filter(email__iexact=email).exists():
        errors.email = "Cette adresse e-mail est déjà utilisée."

    if any(
        (
            errors.first_name,
            errors.last_name,
            errors.email,
            errors.phone,
            errors.password1,
            errors.password2,
            errors.non_field,
        )
    ):
        return render(
            request,
            "portal/client_login.html",
            {
                "show_signup": True,
                "signup_values": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": phone,
                },
                "signup_errors": errors,
            },
            status=400,
        )

    # Username dérivé (stable) : prenom.nom
    base_username = slugify(f"{first_name}.{last_name}").replace("-", "_") or "client"
    safe_username = base_username
    if User.objects.filter(username__iexact=safe_username).exists():
        # fallback léger si slugify collisionne
        safe_username = f"{safe_username}_{User.objects.count() + 1}"

    user = User.objects.create_user(username=safe_username, email=email, password=password1)
    user.first_name = first_name
    user.last_name = last_name
    # On stocke le téléphone dans last_name? Non. On le garde pour plus tard via un Profile model.
    # Pour l'instant on n'enregistre pas 'phone' en base (pas de champ standard).
    user.save()
    auth_login(request, user)
    return redirect("/client")


class PortalLogoutView(LogoutView):
    """Vue — déconnexion (POST recommandé — formulaire dans le template)."""

    next_page = reverse_lazy("portal:admin_login")


@method_decorator(login_required, name="dispatch")
class DashboardView(TemplateView):
    """Vue — tableau de bord après authentification."""

    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Tableau de bord"
        ctx["stats"] = [
            {"label": "Réservations aujourd'hui", "value": "42", "accent": "navy"},
            {"label": "Terrains actifs", "value": "08", "accent": "amber"},
        ]
        return ctx


@csrf_exempt
@require_POST
def api_auth_logout(request):
    """
    API JSON — déconnexion (ferme la session Django).

    ``POST /api/auth/logout/`` — corps vide ou JSON ``{}``.

    Réponse : ``{"ok": true}`` (idempotent si déjà déconnecté).

    Même origine (recommandé, port 3000) : ``fetch('/api/auth/logout/', { method: 'POST', credentials: 'include' })``.

    Cross-origin : ``fetch(DJANGO_ORIGIN + '/api/auth/logout/', { ... })`` (CORS déjà configuré).
    """
    if request.user.is_authenticated:
        logout(request)

    return JsonResponse({"ok": True})


@csrf_exempt
def api_auth_me(request):
    """API JSON — état session Django (client)."""
    u = request.user
    if not u.is_authenticated:
        return JsonResponse({"authenticated": False})
    return JsonResponse(
        {
            "authenticated": True,
            "user": {
                "username": u.get_username(),
                "full_name": u.get_full_name(),
                "email": getattr(u, "email", "") or "",
            },
        }
    )
