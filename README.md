# Réseau de Soin SODECI 2025

Application Django mobile-first pour les employés SODECI : trouver un prestataire agréé près de chez soi.

## Parcours (3 écrans)

1. **Connexion**
2. **Où êtes-vous ?** — recherche de quartier/zone + géoloc
3. **Résultats** — carte plein écran + panneau (bottom sheet / colonne) avec filtres de type de soin

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

## Points à valider avec vous

1. **Format du fichier source** — actuellement Excel `RESEAU DE SOIN 2025.xlsx` (colonnes N°ordre, Direction, Secteur, Communes, Nature, Prestataire, Adresse, Téléphone, E-mail).
2. **Liste officielle des zones** — aujourd’hui la « zone » = secteur (quartier) si présent, sinon commune. Faut-il plutôt une liste figée des directions régionales ?
3. **Mentions légales / RGPD** — texte à afficher (usage interne SODECI, responsabilité des coordonnées, etc.).
