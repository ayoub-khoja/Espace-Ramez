# Projet Django — CRUD (SQLite3)

Objectif : **initiation à Django** via les opérations **CRUD** (Create, Read, Update, Delete) en **MVT** avec **templates Django** et **SQLite3**.

## Fonctionnalités (rubrique examen)

- **2+ modèles**: `Terrain`, `Availability`, `Offer`, `Reservation`, …
- **Relation (ForeignKey)**: `Availability.terrain -> Terrain`
- **CRUD complet (4 opérations)** via pages + templates:
  - `Availability` (Gestion horaires): liste / ajout / modification / suppression
  - `Offer` (Offres & réductions): liste / ajout / modification / suppression (+ upload média)
- **Recherche + Pagination**: sur les pages de listes
- **Authentification (login/logout)**: accès admin protégé
- **Base de données**: **SQLite3 exclusivement**

## Architecture MVT

| Couche | Rôle |
|--------|------|
| **Model** | `portal/models.py` |
| **View** | `portal/views.py` |
| **Template** | `portal/templates/portal/*.html` |

## Installation (Windows / PowerShell)

Prérequis : **Python 3.10+**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_admin
python manage.py runserver
```

Compte admin (dev) créé par `seed_admin` :
- **Identifiant**: `admin`
- **Mot de passe**: `admin`

## URLs utiles

- Login : `http://127.0.0.1:8000/login/`
- Gestion horaires (CRUD + pagination) : `http://127.0.0.1:8000/gestion-horaires/`
- Offres & réductions (CRUD + upload) : `http://127.0.0.1:8000/offres/` et `/offres-reductions/` (admin)

## Dépannage

- Si `ModuleNotFoundError: No module named 'django'` : activer le venv puis réinstaller `pip install -r requirements.txt`.
