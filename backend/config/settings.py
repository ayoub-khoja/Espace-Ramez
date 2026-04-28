"""Configuration du projet Espace Ramez (MVT)."""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-not-for-production-change-with-env",  # noqa: S105
)

_DJANGO_DEBUG = os.environ.get("DJANGO_DEBUG", "").lower()
# En local: DEBUG=True par défaut pour voir les erreurs.
# En production (Render): DEBUG=False par défaut.
DEBUG = (
    (_DJANGO_DEBUG in {"1", "true", "yes", "on"})
    if _DJANGO_DEBUG
    else (os.environ.get("RENDER") is None)
)

ALLOWED_HOSTS: list[str] = [
    "espace-ramez.onrender.com",
    "www.espaceramez.com",
    "espaceramez.com",
    "www.espaceramez.tn",
    "espaceramez.tn",
    # local
    "127.0.0.1",
    "localhost",
]
# Optionnel: permettre d'ajouter des hosts via env sans écraser la liste ci-dessus.
_EXTRA_ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
ALLOWED_HOSTS += [h for h in _EXTRA_ALLOWED_HOSTS if h not in ALLOWED_HOSTS]

# Avec le proxy Next (réécriture vers Django), le navigateur envoie Host :3000 ;
# Django utilise X-Forwarded-Host pour les cookies / URLs cohérents.
USE_X_FORWARDED_HOST = True

# Appels API depuis le frontend Next (dev)
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "https://espaceramez.com",
    "https://www.espaceramez.com",
    "https://espaceramez.tn",
    "https://www.espaceramez.tn",
    "https://espace-ramez.onrender.com",
    # local
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

INSTALLED_APPS = [
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "portal.apps.PortalConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "data" / "db.sqlite3",
    },
}

# Render / production: si DATABASE_URL est présent (Postgres), on l'utilise.
if os.environ.get("DATABASE_URL"):
    DATABASES["default"] = dj_database_url.config(conn_max_age=600, ssl_require=True)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Tunis"
USE_I18N = True
USE_TZ = True

# Email (confirmation réservation)
# En dev: affichage dans la console si aucun SMTP n'est fourni.
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") in {"1", "true", "True", "yes", "on"}
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@espaceramez.tn")

STATIC_URL = "/static/"
# Required for collectstatic (Render)
STATIC_ROOT = BASE_DIR / "staticfiles"
# Images partagées avec le frontend Next (`frontend/public/`, ex. HomeClient.png)
_FRONTEND_PUBLIC = BASE_DIR.parent / "frontend" / "public"
STATICFILES_DIRS = [_FRONTEND_PUBLIC] if _FRONTEND_PUBLIC.is_dir() else []

# Storages (Django >= 4.2)
STORAGES = {
    # Uploads (MEDIA)
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Static files (Render/production)
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Media uploads (images/vidéos offres)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Par défaut, les pages "client" redirigent vers /login/
# (les pages admin utilisent un login_url spécifique dans les décorateurs).
LOGIN_URL = "portal:login"
LOGIN_REDIRECT_URL = "portal:home"
LOGOUT_REDIRECT_URL = "portal:home"

# Connexion avec « admin » ou « admin@espaceramez.tn » dans le champ identifiant
AUTHENTICATION_BACKENDS = [
    "portal.authentication.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]
