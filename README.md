# Réseau de Soin SODECI 2025

Application Django mobile-first pour les employés SODECI : trouver un prestataire agréé près de chez soi.

## Parcours

1. **Connexion**
2. **Résultats** — carte plein écran + panneau avec filtres, géolocalisation, distances voiture et itinéraires

## Installation

```bash
cd "Soin SODECI"
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

python manage.py migrate
python manage.py import_prestataires --clear
python manage.py refine_gps
python manage.py createsuperuser
python manage.py runserver
```

Ouvrir http://127.0.0.1:8000/

### Comptes démo (si déjà créés)

| Rôle | Identifiant | Mot de passe |
|------|-------------|--------------|
| Employé | `employe` | `sodeci2025` |
| Admin | `admin` | `admin2025` |

## Commandes données

```bash
python manage.py import_prestataires
python manage.py import_prestataires --clear
python manage.py import_prestataires chemin/fichier.xlsx
python manage.py refine_gps
python manage.py geocode_prestataires
python manage.py geocode_prestataires --nominatim --limit 50
```

## Tests

```bash
python manage.py test reseau
```

## Production

Dans `.env` :

```
DJANGO_SECRET_KEY=...
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=votre-domaine.ci
```
