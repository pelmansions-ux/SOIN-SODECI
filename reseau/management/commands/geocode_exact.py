"""Géocode des prestataires via Nominatim et enregistre data/exact_gps.json."""

from __future__ import annotations

import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from reseau.geo import geocode_nominatim
from reseau.models import Prestataire

DATA = Path(__file__).resolve().parents[3] / 'data' / 'exact_gps.json'


class Command(BaseCommand):
    help = 'Géocode (Nominatim) et sauvegarde des GPS exacts dans data/exact_gps.json'

    def add_arguments(self, parser):
        parser.add_argument('--zone', default='Cocody')
        parser.add_argument('--limit', type=int, default=80)
        parser.add_argument('--nom', default='', help='Filtrer par nom (ex. Sainte Famille)')

    def handle(self, *args, **options):
        DATA.parent.mkdir(parents=True, exist_ok=True)
        existing: dict = {}
        if DATA.exists():
            existing = json.loads(DATA.read_text(encoding='utf-8'))

        qs = Prestataire.objects.filter(actif=True)
        zone = (options['zone'] or '').strip()
        if zone:
            qs = qs.filter(zone__icontains=zone)
        nom = (options['nom'] or '').strip()
        if nom:
            qs = qs.filter(nom__icontains=nom)

        targets = list(qs.order_by('id')[: options['limit']])
        ok = 0
        self.stdout.write(f'Géocodage de {len(targets)} fiche(s)…')

        for p in targets:
            queries = []
            if p.nom:
                queries.append(f"{p.nom}, {p.zone or p.commune}, Abidjan, Côte d'Ivoire")
                queries.append(f"{p.nom}, Abidjan, Côte d'Ivoire")
            if p.adresse:
                queries.append(
                    f"{p.adresse}, {p.zone or p.commune}, Abidjan, Côte d'Ivoire"
                )

            found = None
            for q in queries:
                found = geocode_nominatim(q)
                time.sleep(1.15)
                if found:
                    break

            if not found:
                self.stdout.write(self.style.WARNING(f'NO  {p.nom[:50]}'))
                continue

            existing[str(p.pk)] = [found[0], found[1]]
            key = f'{p.nom.strip().upper()}|{(p.zone or "").strip().upper()}'
            existing[key] = [found[0], found[1]]
            p.latitude, p.longitude = found
            p.save(update_fields=['latitude', 'longitude'])
            ok += 1
            self.stdout.write(
                self.style.SUCCESS(f'OK  {p.nom[:42]} -> {found[0]:.6f},{found[1]:.6f}')
            )

        DATA.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Enregistré {DATA} — OK: {ok}'))
