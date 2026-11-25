from collections import defaultdict

from django.core.management.base import BaseCommand

from reseau.landmarks import refine_coords
from reseau.models import Prestataire


class Command(BaseCommand):
    help = 'Affine les GPS (landmarks précis + positions distinctes).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Recalculer tous les GPS (recommandé après maj landmarks).',
        )

    def handle(self, *args, **options):
        buckets = defaultdict(list)
        for p in Prestataire.objects.filter(actif=True).exclude(latitude__isnull=True):
            buckets[(round(p.latitude, 5), round(p.longitude, 5))].append(p.id)
        crowded = {k for k, ids in buckets.items() if len(ids) >= 2}

        updated = 0
        for p in Prestataire.objects.filter(actif=True).iterator():
            key = (
                (round(p.latitude, 5), round(p.longitude, 5))
                if p.latitude is not None
                else None
            )
            must = options['all'] or key in crowded or p.latitude is None
            refined = refine_coords(
                zone=p.zone,
                secteur=p.secteur,
                adresse=p.adresse,
                nom=p.nom,
                commune=p.commune,
                fallback=(p.latitude, p.longitude) if p.latitude is not None else None,
                force_unique=must,
                pk=p.pk,
            )
            if not refined:
                continue
            if must or abs(refined[0] - (p.latitude or 0)) > 1e-5 or abs(
                refined[1] - (p.longitude or 0)
            ) > 1e-5:
                p.latitude, p.longitude = refined
                p.save(update_fields=['latitude', 'longitude'])
                updated += 1

        # Contrôle Palm Club
        palm = (5.3335, -3.9865)
        from reseau.geo import haversine_km

        self.stdout.write(self.style.SUCCESS(f'GPS affinés: {updated}'))
        for p in Prestataire.objects.filter(nom__icontains='palm club'):
            d = haversine_km(palm[0], palm[1], p.latitude, p.longitude)
            self.stdout.write(
                f'  {p.nom[:45]} -> {p.latitude:.5f},{p.longitude:.5f} '
                f'(~{d*1000:.0f} m de Hotel Palm Club)'
            )
