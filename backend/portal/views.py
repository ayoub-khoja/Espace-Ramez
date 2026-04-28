"""Vues MVT du portail administrateur."""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .models import Reservation, Terrain

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


def public_home(request):
    """Accueil public (Django templates, Bootstrap)."""
    return render(request, "portal/public/home.html")


class ClientReservationView(TemplateView):
    template_name = "portal/public/reservation.html"


class ClientContactView(TemplateView):
    template_name = "portal/public/contact.html"


@method_decorator(login_required, name="dispatch")
class ClientPanierView(TemplateView):
    template_name = "portal/public/panier.html"


@method_decorator(login_required, name="dispatch")
class ClientOffresView(TemplateView):
    template_name = "portal/public/offres.html"


@require_POST
def client_logout(request):
    """Déconnexion côté site client (ne touche pas au portail admin)."""
    logout(request)
    return redirect("portal:home")


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
        # Après connexion client, on renvoie vers l'accueil Django (sans Next).
        return self.get_redirect_url() or reverse_lazy("portal:home")


def client_signup(request):
    """
    Inscription client (simple).

    - GET : affiche la carte d'inscription (flip)
    - POST : crée un utilisateur Django puis connecte la session
    """
    if request.user.is_authenticated:
        return redirect("portal:home")

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
    return redirect("portal:home")


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


# -----------------------
# CRUD Terrain (Bootstrap)
# -----------------------


@method_decorator(login_required, name="dispatch")
class TerrainListView(ListView):
    model = Terrain
    template_name = "portal/crud/terrain_list.html"
    context_object_name = "terrains"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(nom__icontains=q)
        return qs


@method_decorator(login_required, name="dispatch")
class TerrainCreateView(CreateView):
    model = Terrain
    fields = ["nom", "type", "indoor", "prix_par_session", "actif"]
    template_name = "portal/crud/terrain_form.html"
    success_url = reverse_lazy("portal:terrain_list")


@method_decorator(login_required, name="dispatch")
class TerrainUpdateView(UpdateView):
    model = Terrain
    fields = ["nom", "type", "indoor", "prix_par_session", "actif"]
    template_name = "portal/crud/terrain_form.html"
    success_url = reverse_lazy("portal:terrain_list")


@method_decorator(login_required, name="dispatch")
class TerrainDeleteView(DeleteView):
    model = Terrain
    template_name = "portal/crud/terrain_confirm_delete.html"
    success_url = reverse_lazy("portal:terrain_list")


# ---------------------------
# CRUD Reservation (Bootstrap)
# ---------------------------


@method_decorator(login_required, name="dispatch")
class ReservationListView(ListView):
    model = Reservation
    template_name = "portal/crud/reservation_list.html"
    context_object_name = "reservations"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().select_related("terrain", "client")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(client__username__icontains=q) | qs.filter(terrain__nom__icontains=q)
        return qs


@method_decorator(login_required, name="dispatch")
class ReservationCreateView(CreateView):
    model = Reservation
    fields = ["terrain", "client", "date", "heure_debut", "heure_fin", "statut"]
    template_name = "portal/crud/reservation_form.html"
    success_url = reverse_lazy("portal:reservation_list")


@method_decorator(login_required, name="dispatch")
class ReservationUpdateView(UpdateView):
    model = Reservation
    fields = ["terrain", "client", "date", "heure_debut", "heure_fin", "statut"]
    template_name = "portal/crud/reservation_form.html"
    success_url = reverse_lazy("portal:reservation_list")


@method_decorator(login_required, name="dispatch")
class ReservationDeleteView(DeleteView):
    model = Reservation
    template_name = "portal/crud/reservation_confirm_delete.html"
    success_url = reverse_lazy("portal:reservation_list")


@method_decorator(login_required, name="dispatch")
class ReservationsAdminView(TemplateView):
    """Vue — écran admin des réservations (template MVT)."""

    template_name = "portal/reservations.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["kpis"] = {
            "today_bookings": 42,
            "active_courts": "08",
        }
        ctx["reservations"] = [
            {
                "when_title": "Today, Oct 24",
                "when_sub": "10:00 AM - 11:30 AM",
                "court": "Court 01",
                "court_sub": "PREMIUM INDOOR",
                "accent": "blue",
                "client_initials": "JD",
                "client_name": "Julianna Duarte",
                "status": "CONFIRMED",
                "status_style": "ok",
            },
            {
                "when_title": "Today, Oct 24",
                "when_sub": "11:30 AM - 01:00 PM",
                "court": "Court 04",
                "court_sub": "PANORAMIC GLASS",
                "accent": "amber",
                "client_initials": "RK",
                "client_name": "Robert Kallis",
                "status": "IN-PROGRESS",
                "status_style": "live",
            },
            {
                "when_title": "Tomorrow, Oct 25",
                "when_sub": "08:00 AM - 08:30 AM",
                "court": "Court 02",
                "court_sub": "PREMIUM INDOOR",
                "accent": "blue",
                "client_initials": "SM",
                "client_name": "Sarah Millstone",
                "status": "PENDING",
                "status_style": "warn",
            },
            {
                "when_title": "Tomorrow, Oct 25",
                "when_sub": "10:00 AM - 12:00 PM",
                "court": "Court 07",
                "court_sub": "STANDARD OUTDOOR",
                "accent": "violet",
                "client_initials": "TC",
                "client_name": "Thomas Chen",
                "status": "CANCELLED",
                "status_style": "danger",
            },
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
