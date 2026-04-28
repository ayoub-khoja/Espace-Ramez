"""Vues MVT du portail administrateur."""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView
from django import forms
from django.core.exceptions import ValidationError

from .models import Availability, Offer, Reservation, Terrain


def _fixed_terrain() -> Terrain | None:
    preferred = "Terrain-Padel-Espace-Ramez"
    t = Terrain.objects.filter(nom__iexact=preferred).first()
    if t:
        return t

    t = Terrain.objects.order_by("nom").first()
    if t:
        return t

    # Bootstrap: si aucun terrain en base, on crée le terrain par défaut.
    t, _ = Terrain.objects.get_or_create(
        nom=preferred,
        defaults={"type": "Padel", "indoor": True, "prix_par_session": 45, "actif": True},
    )
    return t


class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ["titre", "badge", "remise_percent", "description", "conditions_titre", "conditions", "media", "actif"]

        widgets = {
            "titre": forms.TextInput(attrs={"class": "crud-input", "placeholder": "Titre de l’offre"}),
            "badge": forms.TextInput(attrs={"class": "crud-input", "placeholder": "Badge (optionnel)"}),
            "remise_percent": forms.NumberInput(attrs={"class": "crud-input", "placeholder": "Ex: 12"}),
            "description": forms.Textarea(attrs={"class": "crud-input", "rows": 4, "placeholder": "Description (optionnel)"}),
            "conditions_titre": forms.TextInput(attrs={"class": "crud-input", "placeholder": "Ex: Conditions premium"}),
            "conditions": forms.TextInput(attrs={"class": "crud-input", "placeholder": "Ex: Annulation flexible · Support 7j/7"}),
        }

User = get_user_model()

ADMIN_LOGIN_URL = reverse_lazy("portal:admin_login")
CLIENT_LOGIN_URL = reverse_lazy("portal:login")


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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        terrains = list(Terrain.objects.filter(actif=True).order_by("nom"))
        ctx["terrains"] = terrains

        # Date/terrain sélectionnés via query params
        today = timezone.localdate()
        date_s = (self.request.GET.get("date") or "").strip()
        selected_date = today
        if date_s:
            try:
                selected_date = timezone.datetime.fromisoformat(date_s).date()
            except ValueError:
                selected_date = today

        terrain_id = (self.request.GET.get("terrain") or "").strip()
        selected_terrain = terrains[0] if terrains else None
        if terrain_id.isdigit():
            for t in terrains:
                if t.id == int(terrain_id):
                    selected_terrain = t
                    break

        ctx["selected_date"] = selected_date
        ctx["selected_terrain"] = selected_terrain
        ctx["date_choices"] = [today + timezone.timedelta(days=i) for i in range(0, 7)]

        slots = []
        if selected_terrain:
            avail_qs = (
                Availability.objects.filter(
                    terrain=selected_terrain,
                    date=selected_date,
                    actif=True,
                )
                .order_by("heure_debut")
            )
            reservations = list(
                Reservation.objects.filter(
                    terrain=selected_terrain,
                    date=selected_date,
                ).exclude(statut="CANCELLED")
            )

            def is_reserved(a: Availability) -> bool:
                for r in reservations:
                    # overlap: start < other_end and other_start < end
                    if a.heure_debut < r.heure_fin and r.heure_debut < a.heure_fin:
                        return True
                return False

            for a in avail_qs:
                slots.append(
                    {
                        "id": a.id,
                        "start": a.heure_debut,
                        "end": a.heure_fin,
                        "reserved": is_reserved(a),
                    }
                )

        ctx["slots"] = slots
        return ctx


class ClientContactView(TemplateView):
    template_name = "portal/public/contact.html"


@method_decorator(login_required(login_url=CLIENT_LOGIN_URL), name="dispatch")
class ClientPanierView(TemplateView):
    template_name = "portal/public/panier.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        r = (
            Reservation.objects.filter(client=self.request.user, statut="PENDING")
            .select_related("terrain")
            .order_by("-created_at")
            .first()
        )
        ctx["pending_reservation"] = r
        ctx["prefill"] = {
            "nom": (self.request.user.get_full_name() or self.request.user.get_username() or "").strip(),
            "email": (getattr(self.request.user, "email", "") or "").strip(),
            "tel": "",
        }
        return ctx


@method_decorator(login_required(login_url=CLIENT_LOGIN_URL), name="dispatch")
class ClientOffresView(ListView):
    model = Offer
    template_name = "portal/public/offres.html"
    context_object_name = "offers"
    paginate_by = 6

    def get_queryset(self):
        return Offer.objects.filter(actif=True).order_by("-updated_at", "-created_at")


@require_POST
def client_logout(request):
    """Déconnexion côté site client (ne touche pas au portail admin)."""
    logout(request)
    return redirect("portal:home")


@login_required(login_url=CLIENT_LOGIN_URL)
@require_POST
def client_book_slot(request):
    availability_id = (request.POST.get("availability_id") or "").strip()
    if not availability_id.isdigit():
        messages.error(request, "Créneau invalide.")
        return redirect("portal:client_reservation")

    a = Availability.objects.filter(pk=int(availability_id), actif=True).select_related("terrain").first()
    if not a:
        messages.error(request, "Ce créneau n'est plus disponible.")
        return redirect("portal:client_reservation")

    overlap_exists = (
        Reservation.objects.filter(
            terrain=a.terrain,
            date=a.date,
        )
        .exclude(statut="CANCELLED")
        .filter(heure_debut__lt=a.heure_fin, heure_fin__gt=a.heure_debut)
        .exists()
    )
    if overlap_exists:
        messages.error(request, "Ce créneau vient d’être réservé. Choisissez un autre horaire.")
        return redirect("portal:client_reservation")

    Reservation.objects.create(
        terrain=a.terrain,
        client=request.user,
        date=a.date,
        heure_debut=a.heure_debut,
        heure_fin=a.heure_fin,
        statut="PENDING",
    )
    messages.success(request, "Créneau ajouté au panier. Confirmez pour finaliser.")
    return redirect("portal:client_panier")


@login_required(login_url=CLIENT_LOGIN_URL)
@require_POST
def client_confirm_reservation(request):
    r = (
        Reservation.objects.filter(client=request.user, statut="PENDING")
        .select_related("terrain")
        .order_by("-created_at")
        .first()
    )
    if not r:
        messages.error(request, "Aucune réservation en attente.")
        return redirect("portal:client_panier")

    nom = (request.POST.get("nom") or "").strip()
    email = (request.POST.get("email") or "").strip()
    tel = (request.POST.get("tel") or "").strip()

    if not nom:
        messages.error(request, "Veuillez renseigner votre nom.")
        return redirect("portal:client_panier")
    if not email or "@" not in email:
        messages.error(request, "Veuillez renseigner un e-mail valide.")
        return redirect("portal:client_panier")

    # Vérifie que le créneau n'a pas été pris entre-temps
    overlap_exists = (
        Reservation.objects.filter(
            terrain=r.terrain,
            date=r.date,
        )
        .exclude(pk=r.pk)
        .exclude(statut="CANCELLED")
        .filter(heure_debut__lt=r.heure_fin, heure_fin__gt=r.heure_debut)
        .exists()
    )
    if overlap_exists:
        r.statut = "CANCELLED"
        r.save(update_fields=["statut"])
        messages.error(request, "Ce créneau n'est plus disponible. Veuillez choisir un autre horaire.")
        return redirect("portal:client_reservation")

    r.contact_nom = nom
    r.contact_email = email
    r.contact_tel = tel
    r.statut = "CONFIRMED"
    r.confirmed_at = timezone.now()
    r.save(update_fields=["contact_nom", "contact_email", "contact_tel", "statut", "confirmed_at"])

    # Email confirmation
    subject = "Confirmation de réservation — Espace Ramez"
    body = (
        f"Bonjour {nom},\n\n"
        f"Votre réservation est confirmée.\n\n"
        f"Terrain: {r.terrain.nom}\n"
        f"Date: {r.date}\n"
        f"Heure: {r.heure_debut.strftime('%H:%M')} - {r.heure_fin.strftime('%H:%M')}\n\n"
        f"Merci,\nEspace Ramez"
    )
    try:
        send_mail(subject, body, None, [email], fail_silently=False)
    except Exception:
        # On ne bloque pas la confirmation si l'email échoue.
        messages.warning(request, "Réservation confirmée, mais l'envoi de l'e-mail a échoué. Vérifiez la configuration SMTP.")
    else:
        messages.success(request, "Réservation confirmée. Un e-mail de confirmation a été envoyé.")

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
    messages.success(request, "Compte créé avec succès. Connectez-vous pour continuer.")
    return redirect("portal:login")


class PortalLogoutView(LogoutView):
    """Vue — déconnexion (POST recommandé — formulaire dans le template)."""

    next_page = reverse_lazy("portal:admin_login")


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
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


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
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


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class TerrainCreateView(CreateView):
    model = Terrain
    fields = ["nom", "type", "indoor", "prix_par_session", "actif"]
    template_name = "portal/crud/terrain_form.html"
    success_url = reverse_lazy("portal:terrain_list")


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class TerrainUpdateView(UpdateView):
    model = Terrain
    fields = ["nom", "type", "indoor", "prix_par_session", "actif"]
    template_name = "portal/crud/terrain_form.html"
    success_url = reverse_lazy("portal:terrain_list")


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class TerrainDeleteView(DeleteView):
    model = Terrain
    template_name = "portal/crud/terrain_confirm_delete.html"
    success_url = reverse_lazy("portal:terrain_list")


# ---------------------------
# CRUD Reservation (Bootstrap)
# ---------------------------


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
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


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class ReservationCreateView(CreateView):
    model = Reservation
    fields = ["terrain", "client", "date", "heure_debut", "heure_fin", "statut"]
    template_name = "portal/crud/reservation_form.html"
    success_url = reverse_lazy("portal:reservation_list")


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class ReservationUpdateView(UpdateView):
    model = Reservation
    fields = ["terrain", "client", "date", "heure_debut", "heure_fin", "statut"]
    template_name = "portal/crud/reservation_form.html"
    success_url = reverse_lazy("portal:reservation_list")


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class ReservationDeleteView(DeleteView):
    model = Reservation
    template_name = "portal/crud/reservation_confirm_delete.html"
    success_url = reverse_lazy("portal:reservation_list")


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class ReservationsAdminView(ListView):
    """Vue — écran admin des réservations (dynamique)."""

    model = Reservation
    template_name = "portal/reservations.html"
    context_object_name = "reservations_qs"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("terrain", "client")

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(client__username__icontains=q) | qs.filter(client__email__icontains=q) | qs.filter(terrain__nom__icontains=q)

        date_s = (self.request.GET.get("date") or "").strip()
        if date_s:
            qs = qs.filter(date=date_s)

        statut = (self.request.GET.get("statut") or "").strip().upper()
        if statut in {"CONFIRMED", "IN_PROGRESS", "PENDING", "CANCELLED"}:
            qs = qs.filter(statut=statut)

        return qs.order_by("-date", "-heure_debut", "-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        ctx["kpis"] = {
            "today_bookings": Reservation.objects.filter(date=today).exclude(statut="CANCELLED").count(),
            "active_courts": Terrain.objects.filter(actif=True).count(),
        }
        ctx["today"] = today
        ctx["filters"] = {
            "q": (self.request.GET.get("q") or "").strip(),
            "date": (self.request.GET.get("date") or "").strip(),
            "statut": (self.request.GET.get("statut") or "").strip(),
        }
        return ctx


@method_decorator(login_required, name="dispatch")
class OffersAdminView(TemplateView):
    """Vue — gestion des offres et réductions (admin)."""

    template_name = "portal/offers_admin.html"


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class OfferListView(ListView):
    model = Offer
    template_name = "portal/crud/offer_list.html"
    context_object_name = "offers"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(titre__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["offer_form"] = kwargs.get("offer_form") or OfferForm()
        ctx["offer_modal_open"] = kwargs.get("offer_modal_open", False)
        return ctx

    def post(self, request, *args, **kwargs):
        form = OfferForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Offre ajoutée avec succès.")
            return redirect("portal:offer_list")

        # Réaffiche la liste + ouvre la modal avec les erreurs.
        self.object_list = self.get_queryset()
        context = self.get_context_data(offer_form=form, offer_modal_open=True)
        return self.render_to_response(context, status=400)


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class OfferCreateView(CreateView):
    model = Offer
    fields = ["titre", "badge", "remise_percent", "description", "conditions_titre", "conditions", "media", "actif"]
    template_name = "portal/crud/offer_form.html"
    success_url = reverse_lazy("portal:offer_list")


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class OfferUpdateView(UpdateView):
    model = Offer
    fields = ["titre", "badge", "remise_percent", "description", "conditions_titre", "conditions", "media", "actif"]
    template_name = "portal/crud/offer_form.html"
    success_url = reverse_lazy("portal:offer_list")


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class OfferDeleteView(DeleteView):
    model = Offer
    template_name = "portal/crud/offer_confirm_delete.html"
    success_url = reverse_lazy("portal:offer_list")


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class ClientListView(ListView):
    model = User
    template_name = "portal/crud/client_list.html"
    context_object_name = "clients"
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True, is_staff=False, is_superuser=False)
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(username__icontains=q) | qs.filter(email__icontains=q) | qs.filter(first_name__icontains=q) | qs.filter(last_name__icontains=q)
        return qs.order_by("-date_joined")


class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ["terrain", "date", "heure_debut", "heure_fin", "actif"]
        widgets = {
            "terrain": forms.Select(attrs={"class": "crud-select"}),
            "date": forms.DateInput(attrs={"class": "crud-input", "type": "date"}),
            "heure_debut": forms.TimeInput(attrs={"class": "crud-input", "type": "time"}),
            "heure_fin": forms.TimeInput(attrs={"class": "crud-input", "type": "time"}),
        }

    repeat_days = forms.MultipleChoiceField(
        required=False,
        choices=[
            ("0", "Lun"),
            ("1", "Mar"),
            ("2", "Mer"),
            ("3", "Jeu"),
            ("4", "Ven"),
            ("5", "Sam"),
            ("6", "Dim"),
        ],
        widget=forms.CheckboxSelectMultiple,
        label="Jours",
        help_text="Optionnel: créer les mêmes horaires sur plusieurs jours.",
    )
    repeat_weeks = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=52,
        initial=1,
        label="Nombre de semaines",
        help_text="Ex: 4 pour répéter sur 4 semaines à partir de la date choisie.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dans ton projet, on force un seul terrain sélectionné (non modifiable).
        fixed = _fixed_terrain()
        self._fixed_terrain = fixed

        if fixed:
            self.fields["terrain"].queryset = Terrain.objects.filter(pk=fixed.pk)
            self.fields["terrain"].initial = fixed
            self.fields["terrain"].widget = forms.HiddenInput()

    def clean_terrain(self):
        # Ignore toute tentative de modifier le terrain depuis le formulaire.
        if getattr(self, "_fixed_terrain", None):
            return self._fixed_terrain
        return self.cleaned_data["terrain"]

    def clean(self):
        cleaned = super().clean()
        hd = cleaned.get("heure_debut")
        hf = cleaned.get("heure_fin")
        if hd and hf and hf <= hd:
            # Erreur claire côté formulaire (au lieu de la contrainte DB).
            self.add_error("heure_fin", "L'heure de fin doit être après l'heure de début.")
            raise ValidationError("Horaires invalides.")
        return cleaned


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class AvailabilityListView(ListView):
    model = Availability
    template_name = "portal/crud/availability_list.html"
    context_object_name = "items"
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset().select_related("terrain")
        terrain_id = (self.request.GET.get("terrain") or "").strip()
        date_s = (self.request.GET.get("date") or "").strip()
        if terrain_id.isdigit():
            qs = qs.filter(terrain_id=int(terrain_id))
        if date_s:
            qs = qs.filter(date=date_s)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = kwargs.get("availability_form") or AvailabilityForm()
        ctx["availability_form"] = form
        fixed = _fixed_terrain()
        ctx["availability_terrain_label"] = getattr(fixed, "nom", None) or "Terrain"
        ctx["availability_modal_open"] = kwargs.get("availability_modal_open", False)
        return ctx

    def post(self, request, *args, **kwargs):
        form = AvailabilityForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            terrain = cd["terrain"]
            date = cd["date"]
            hd = cd["heure_debut"]
            hf = cd["heure_fin"]
            actif = cd["actif"]

            repeat_days = [int(x) for x in (cd.get("repeat_days") or []) if str(x).isdigit()]
            repeat_weeks = cd.get("repeat_weeks") or 1

            created = 0
            if repeat_days:
                start = date
                for w in range(int(repeat_weeks)):
                    base = start + timezone.timedelta(days=7 * w)
                    # Pour chaque jour de la semaine choisi, on calcule la date dans la semaine.
                    for d in repeat_days:
                        day_date = base + timezone.timedelta(days=(d - base.weekday()) % 7)
                        Availability.objects.create(
                            terrain=terrain,
                            date=day_date,
                            heure_debut=hd,
                            heure_fin=hf,
                            actif=actif,
                        )
                        created += 1
            else:
                form.save()
                created = 1

            messages.success(request, f"Disponibilité ajoutée ({created}).")
            return redirect("portal:availability_list")

        self.object_list = self.get_queryset()
        context = self.get_context_data(availability_form=form, availability_modal_open=True)
        return self.render_to_response(context, status=400)


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class AvailabilityCreateView(CreateView):
    model = Availability
    form_class = AvailabilityForm
    template_name = "portal/crud/availability_form.html"
    success_url = reverse_lazy("portal:availability_list")


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class AvailabilityUpdateView(UpdateView):
    model = Availability
    form_class = AvailabilityForm
    template_name = "portal/crud/availability_form.html"
    success_url = reverse_lazy("portal:availability_list")


@method_decorator(login_required(login_url=ADMIN_LOGIN_URL), name="dispatch")
class AvailabilityDeleteView(DeleteView):
    model = Availability
    template_name = "portal/crud/availability_confirm_delete.html"
    success_url = reverse_lazy("portal:availability_list")

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
