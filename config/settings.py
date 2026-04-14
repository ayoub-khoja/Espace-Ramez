"""Configuration du projet Espace Ramez (MVT)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-not-for-production-change-with-env",  # noqa: S105
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") in ("1", "true", "True", "yes")

ALLOWED_HOSTS: list[str] = ["127.0.0.1", "localhost"]

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
    "portal",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
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

STATIC_URL = "static/"
# Images partagées avec le frontend Next (`frontend/public/`, ex. HomeClient.png)
_FRONTEND_PUBLIC = BASE_DIR.parent / "frontend" / "public"
STATICFILES_DIRS = [_FRONTEND_PUBLIC] if _FRONTEND_PUBLIC.is_dir() else []

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "portal:admin_login"
LOGIN_REDIRECT_URL = "portal:dashboard"
LOGOUT_REDIRECT_URL = "portal:admin_login"

# Connexion avec « admin » ou « admin@espaceramez.tn » dans le champ identifiant
AUTHENTICATION_BACKENDS = [
    "portal.authentication.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]
