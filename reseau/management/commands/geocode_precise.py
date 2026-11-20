"""Géocode précisément chaque prestataire via Nominatim (adresse réelle)."""

from __future__ import annotations

import re
import time

from django.core.management.base import BaseCommand
from django.db.models import Count

from reseau.geo import geocode_nominatim
from reseau.models import Prestataire


def street_hint(adresse: str) -> str:
    """Extrait un bout d'adresse utile pour Nominatim."""
    text = re.sub(r'\s+', ' ', (adresse or '').strip())
    return text[:120]


class Command(BaseCommand):
    help = 'Affine le GPS via Nominatim pour obtenir des distances plus exactes.'

    def add_arguments(self, parser):
        parser.add_argument('--zone', default='', help='Limiter à une zone (ex. Koumassi)')
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument(
            '--shared-only',
            action='store_true',
            help='Uniquement les points GPS partagés par ≥3 prestataires',
        )

    def handle(self, *args, **options):
        zone = options['zone'].strip()
        qs = Prestataire.objects.filter(actif=True)

        if zone:
            targets = list(qs.filter(zone__iexact=zone).order_by('id'))
        elif options['shared_only']:
            shared = {
                (row['latitude'], row['longitude'])
                for row in (
                    qs.exclude(latitude__isnull=True)
                    .exclude(longitude__isnull=True)
                    .values('latitude', 'longitude')
                    .annotate(n=Count('id'))
                    .filter(n__gte=3)
                )
            }
            targets = [
                p
                for p in qs.exclude(latitude__isnull=True).order_by('id')
                if (p.latitude, p.longitude) in shared
            ]
        else:
            targets = list(qs.order_by('id'))

        if options['limit']:
            targets = targets[: options['limit']]

        cache: dict[str, tuple[float, float] | None] = {}
        ok = fail = 0
        self.stdout.write(f'Traitement de {len(targets)} prestataire(s)…')

        for p in targets:
            place = (p.commune or p.zone or '').strip()
            addr = street_hint(p.adresse)
            queries = []
            if addr:
                queries.append(f"{addr}, {place}, Abidjan, Côte d'Ivoire")
                queries.append(f"{addr}, {place}, Côte d'Ivoire")
            if p.nom:
                queries.append(f"{p.nom}, {place}, Abidjan, Côte d'Ivoire")
            if p.secteur and p.secteur.upper() != place.upper():
                queries.append(f"{p.secteur}, {place}, Abidjan, Côte d'Ivoire")

            found = None
            for q in queries:
                if q in cache:
                    found = cache[q]
                    if found:
                        break
                    continue
                found = geocode_nominatim(q)
                cache[q] = found
                time.sleep(1.1)
                if found:
                    break

            if found:
                p.latitude, p.longitude = found
                p.save(update_fields=['latitude', 'longitude'])
                ok += 1
                self.stdout.write(
                    self.style.SUCCESS(f'OK  {p.nom[:42]} -> {found[0]:.6f}, {found[1]:.6f}')
                )
            else:
                fail += 1
                self.stdout.write(self.style.WARNING(f'NO  {p.nom[:42]}'))

        self.stdout.write(self.style.SUCCESS(f'Terminé — OK: {ok}, échecs: {fail}'))
