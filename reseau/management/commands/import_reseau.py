from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from openpyxl import load_workbook

from reseau.geo import resolve_coords
from reseau.models import Prestataire


def clean(value) -> str:
    if value is None:
        return ''
    text = str(value).replace('\xa0', ' ').strip()
    return ' '.join(text.split())


class Command(BaseCommand):
    help = 'Importe le fichier Excel RESEAU DE SOIN 2025 dans la base.'

    def add_arguments(self, parser):
        parser.add_argument(
            'fichier',
            nargs='?',
            default=str(settings.BASE_DIR / 'RESEAU DE SOIN 2025.xlsx'),
            help='Chemin vers le fichier Excel',
        )
        parser.add_argument(
            '--geocode',
            action='store_true',
            help='Compléter les communes inconnues via Nominatim (lent)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprimer les prestataires existants avant import',
        )

    def handle(self, *args, **options):
        path = Path(options['fichier'])
        if not path.exists():
            raise CommandError(f'Fichier introuvable : {path}')

        if options['clear']:
            deleted, _ = Prestataire.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'{deleted} prestataire(s) supprimé(s).'))

        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active

        created = updated = skipped = geocoded = 0

        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or all(c is None or str(c).strip() == '' for c in row):
                continue

            try:
                numero = int(row[0]) if row[0] is not None else None
            except (TypeError, ValueError):
                skipped += 1
                continue

            if numero is None:
                skipped += 1
                continue

            direction = clean(row[1])
            secteur = clean(row[2])
            commune = clean(row[3])
            nature = clean(row[4])
            nom = clean(row[5])
            adresse = clean(row[6])
            telephone = clean(row[7])
            email = clean(row[8]).replace(',', '.')

            if not nom:
                skipped += 1
                continue

            coords = resolve_coords(
                commune=commune,
                secteur=secteur,
                adresse=adresse,
                nom=nom,
                use_nominatim=options['geocode'],
            )

            defaults = {
                'direction': direction,
                'secteur': secteur,
                'commune': commune,
                'nature': nature,
                'nom': nom,
                'adresse': adresse,
                'telephone': telephone,
                'email': email,
            }
            if coords:
                defaults['latitude'], defaults['longitude'] = coords
                geocoded += 1

            obj, was_created = Prestataire.objects.update_or_create(
                numero_ordre=numero,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                # conserver coords existantes si nouvel import sans coords
                if not coords and (obj.latitude is None):
                    pass
                updated += 1

            if i % 100 == 0:
                self.stdout.write(f'… ligne {i}')

        wb.close()
        self.stdout.write(
            self.style.SUCCESS(
                f'Import terminé — créés: {created}, mis à jour: {updated}, '
                f'ignorés: {skipped}, avec GPS: {geocoded}'
            )
        )
