# Padel — monorepo

- **`frontend/`** — Next.js (site public + **réécriture** `/login`, `/admin`, `/api/…` vers Django, tout sur le port **3000**).
- **`backend/`** — **Django** (MVT : modèles, vues, templates) + **SQLite3** — portail administrateur avec interface HTML.

## Architecture MVT (Django)

| Couche | Rôle |
|--------|------|
| **Modèle** | `portal/models.py` (+ tables Django `auth`, etc. dans `data/db.sqlite3`) |
| **Vue** | `portal/views.py` (`PortalLoginView`, `DashboardView`, …) |
| **Template** | `portal/templates/portal/*.html` + statiques `portal/static/portal/` |

Connexion admin (URL canonique) : **`/login/`** (ex. `http://localhost:3000/login?next=…`). Les chemins `/admin/login/` et `/connexion/` redirigent vers `/login/`.  
Tableau de bord (connecté) : `/admin` ou `/tableau-de-bord/` (réécriture vers la même vue Django).  
Déconnexion : `POST /deconnexion/`  
**API JSON déconnexion** : `POST /api/auth/logout/` sur **le même hôte que Next** (port **3000**) → le proxy réécrit vers Django ; réponse `{"ok": true}`.

Exemple depuis le frontend (recommandé, même origine) :

```javascript
await fetch("/api/auth/logout/", {
  method: "POST",
  credentials: "include",
  headers: { Accept: "application/json" },
});
```

Module utilitaire : `frontend/shared/backend-api.ts` (`djangoAuthLogout`, `djangoUrl`, …).

Alternative cross-origin (sans proxy sur `/api`) :

```javascript
await fetch(`${process.env.NEXT_PUBLIC_DJANGO_ORIGIN}/api/auth/logout/`, {
  method: "POST",
  credentials: "include",
  headers: { Accept: "application/json" },
});
```

`django-cors-headers` est configuré pour autoriser `localhost:3000` et `127.0.0.1:3000` avec cookies (`CORS_ALLOW_CREDENTIALS`).

> L’endpoint est marqué `csrf_exempt` pour simplifier les appels cross-origin en développement. En production, préférez une auth par token ou un flux CSRF explicite.

Admin Django natif (optionnel) : `/gestion-django/`

## Prérequis

- **Node.js** 20+ (frontend)
- **Python** 3.10+ avec `pip` (backend)

## Installation

### Frontend

```bash
cd frontend
npm install
```

### Backend (au choix : **venv + pip** ou **Pipenv**)

#### Option A — `venv` + `requirements.txt` (recommandé)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_admin
# Si la connexion échoue alors que le compte existe déjà :
python manage.py seed_admin --reset
```

> Ne pas lancer : `python -m venv .venv .venv\Scripts\activate` (deux arguments : le 2ᵉ doit être uniquement le dossier du venv).

#### Option B — Pipenv (si vous avez un `Pipfile`)

Après `pipenv shell` ou dans le dossier `backend` :

```powershell
cd backend
pipenv install
pipenv run python manage.py migrate
pipenv run python manage.py seed_admin
pipenv run python manage.py runserver
```

Sans `pipenv install`, le message **`No module named 'django'`** est normal : Django n’est pas encore installé dans l’environnement Pipenv.

Compte créé par `seed_admin` :

- **Identifiant :** `admin`  
- **Mot de passe :** `admin`  
- **E-mail :** `admin@espaceramez.tn`

## Développement

**Terminal 1 — Django** (port **8000** par défaut) :

- **Depuis la racine du dépôt** (`padel-frontend/`) :

```bash
npm run dev:backend
```

- **Depuis le dossier `backend/`** (le script s’appelle `dev`, pas `dev:backend`) :

```bash
cd backend
npm run dev
```

Avec un venv activé : `python manage.py runserver`. Avec **Pipenv** (sans activer le venv à la main) : `cd backend` puis `npm run dev:pipenv`.

**Terminal 2 — Next.js** (port **3000**) :

```bash
cd frontend
npm run dev
```

Copier la config frontend :

```bash
copy frontend\.env.example frontend\.env.local
```

Les URLs `http://localhost:3000/login`, `/admin`, `/connexion/`, etc. sont **réécrites** ou **redirigées** côté Next vers Django (`NEXT_PUBLIC_DJANGO_ORIGIN`) : le navigateur reste sur le **port 3000**.

## Build production (frontend)

```bash
cd frontend
npm run build
```

Le déploiement Django (WSGI, `collectstatic`, etc.) est à prévoir séparément (ex. Gunicorn + Nginx).

## Dépannage

| Problème | Cause | Solution |
|----------|--------|----------|
| `ModuleNotFoundError: No module named 'corsheaders'` | Le serveur Django tourne avec un **autre** Python que celui du venv où les paquets sont installés. | Dans `backend` : `.\.venv\Scripts\Activate.ps1` puis `pip install -r requirements.txt`, **ou** lancer explicitement `.\.venv\Scripts\python.exe manage.py runserver`. Ne pas mélanger **Pipenv** et un dossier `backend\.venv` sans y réinstaller les paquets. |
| `Missing script: "dev:backend"` dans `backend/` | Ce script existe **à la racine** du monorepo, pas dans `backend/package.json`. | À la racine : `npm run dev:backend` **ou** dans `backend` : `npm run dev`. |
| `No module named 'django'` après `pipenv shell` | Dépendances pas installées dans l’environnement Pipenv. | `cd backend` puis `pipenv install`. |
| `pip install` installe « globalement » | Le venv n’est pas activé. | `.\.venv\Scripts\Activate.ps1` puis `pip install -r requirements.txt`. |
| `Failed running 'src/server.mjs'` | Ancien backend Node supprimé. | Utiliser Django : `npm run dev:backend` ou `npm run dev` dans `backend/`. |
