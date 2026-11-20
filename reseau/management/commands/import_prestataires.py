from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openpyxl import load_workbook

from reseau.geo import resolve_coords
from reseau.models import Prestataire
from reseau.types_soin import normalize_type


def clean(value) -> str:
    if value is None:
        return ''
    text = str(value).replace('\xa0', ' ').strip()
    return ' '.join(text.split())


def build_zone(commune: str, secteur: str) -> str:
    commune = clean(commune)
    secteur = clean(secteur)
    for prefix in ('SECTEUR ', 'QUARTIER '):
        if secteur.upper().startswith(prefix):
            secteur = secteur[len(prefix):].strip()
        if commune.upper().startswith(prefix):
            commune = commune[len(prefix):].strip()

    # Quartier/secteur s'il apporte une info différente de la commune
    if secteur and commune and secteur.upper() != commune.upper():
        if commune.upper() in secteur.upper():
            return secteur.title()
        # Ex. secteur ANGRé + commune COCODY → Angré
        return secteur.title()
    return (commune or secteur or 'Non précisé').title()


class Command(BaseCommand):
    help = 'Importe le fichier Excel/CSV Réseau de Soin 2025.'

    def add_arguments(self, parser):
        parser.add_argument(
            'fichier',
            nargs='?',
            default=str(settings.BASE_DIR / 'RESEAU DE SOIN 2025.xlsx'),
        )
        parser.add_argument('--clear', action='store_true')
        parser.add_argument(
            '--geocode',
            action='store_true',
            help='Compléter via Nominatim les lieux inconnus (lent)',
        )

    def handle(self, *args, **options):
        path = Path(options['fichier'])
        if not path.exists():
            raise CommandError(f'Fichier introuvable : {path}')

        if options['clear']:
            n, _ = Prestataire.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'{n} enregistrement(s) supprimé(s).'))

        suffix = path.suffix.lower()
        if suffix in ('.xlsx', '.xlsm'):
            rows = self._read_xlsx(path)
        elif suffix == '.csv':
            rows = self._read_csv(path)
        else:
            raise CommandError('Format supporté : .xlsx ou .csv')

        created = updated = skipped = gps = 0
        cache = {}

        for row in rows:
            numero = row.get('numero')
            nom = clean(row.get('nom'))
            if not nom:
                skipped += 1
                continue

            direction = clean(row.get('direction'))
            secteur = clean(row.get('secteur'))
            commune = clean(row.get('commune'))
            nature = clean(row.get('nature'))
            adresse = clean(row.get('adresse'))
            telephone = clean(row.get('telephone'))
            email = clean(row.get('email')).replace(',', '.')
            zone = build_zone(commune, secteur)
            type_soin = normalize_type(nature)

            coords = resolve_coords(
                commune=commune,
                secteur=secteur,
                zone=zone,
                adresse=adresse,
                nom=nom,
                use_nominatim=options['geocode'],
                cache=cache,
            )

            defaults = {
                'nom': nom,
                'nature': nature,
                'type_soin': type_soin,
                'direction': direction,
                'commune': commune,
                'secteur': secteur,
                'zone': zone,
                'adresse': adresse,
                'telephone': telephone,
                'email': email,
                'actif': True,
            }
            if coords:
                defaults['latitude'], defaults['longitude'] = coords
                gps += 1

            lookup = {'numero_ordre': numero} if numero is not None else {'nom': nom, 'zone': zone}
            if numero is not None:
                obj, was_created = Prestataire.objects.update_or_create(
                    numero_ordre=numero,
                    defaults=defaults,
                )
            else:
                obj, was_created = Prestataire.objects.update_or_create(
                    nom=nom,
                    zone=zone,
                    defaults=defaults,
                )

            if was_created:
                created += 1
            else:
                if not coords and obj.latitude is None:
                    pass
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Import OK — créés: {created}, mis à jour: {updated}, '
                f'ignorés: {skipped}, avec GPS: {gps}'
            )
        )

    def _read_xlsx(self, path: Path):
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        out = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or all(c is None or str(c).strip() == '' for c in row):
                continue
            try:
                numero = int(row[0]) if row[0] is not None else None
            except (TypeError, ValueError):
                numero = None
            out.append(
                {
                    'numero': numero,
                    'direction': row[1] if len(row) > 1 else '',
                    'secteur': row[2] if len(row) > 2 else '',
                    'commune': row[3] if len(row) > 3 else '',
                    'nature': row[4] if len(row) > 4 else '',
                    'nom': row[5] if len(row) > 5 else '',
                    'adresse': row[6] if len(row) > 6 else '',
                    'telephone': row[7] if len(row) > 7 else '',
                    'email': row[8] if len(row) > 8 else '',
                }
            )
        wb.close()
        return out

    def _read_csv(self, path: Path):
        import csv

        out = []
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                numero = row.get('N°ORDRE') or row.get('numero') or row.get('NORDRE')
                try:
                    numero = int(numero) if numero not in (None, '') else None
                except ValueError:
                    numero = None
                out.append(
                    {
                        'numero': numero,
                        'direction': row.get('LIBELLE DIRECTION') or row.get('direction', ''),
                        'secteur': row.get('SECTEUR') or row.get('secteur', ''),
                        'commune': row.get('COMMUNES') or row.get('commune', ''),
                        'nature': row.get('NATURE PRESTATAIRE') or row.get('nature', ''),
                        'nom': row.get('PRESTATAIRE') or row.get('nom', ''),
                        'adresse': row.get('SITUATION GEOGRAPHIQUE') or row.get('adresse', ''),
                        'telephone': row.get('TELEPHONE') or row.get('telephone', ''),
                        'email': row.get('E-MAIL') or row.get('email', ''),
                    }
                )
        return out
