from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count

from reseau.landmarks import refine_coords
from reseau.models import Prestataire


class Command(BaseCommand):
    help = 'Affine les GPS pour que chaque prestataire ait une position distincte.'

    def handle(self, *args, **options):
        # Groupes de coords identiques
        shared_keys = {
            (round(row['latitude'], 5), round(row['longitude'], 5))
            for row in (
                Prestataire.objects.filter(actif=True)
                .exclude(latitude__isnull=True)
                .exclude(longitude__isnull=True)
                .values('latitude', 'longitude')
            )
        }
        # Recount properly
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
            must = key in crowded or p.latitude is None
            refined = refine_coords(
                zone=p.zone,
                secteur=p.secteur,
                adresse=p.adresse,
                nom=p.nom,
                commune=p.commune,
                fallback=(p.latitude, p.longitude) if p.latitude is not None else None,
                force_unique=must,
            )
            if not refined:
                continue
            # Toujours réécrire les points en cluster, sinon seulement si landmark plus précis
            if must or abs(refined[0] - (p.latitude or 0)) > 1e-5:
                p.latitude, p.longitude = refined
                p.save(update_fields=['latitude', 'longitude'])
                updated += 1

        # Vérification Cocody
        cocody = Prestataire.objects.filter(zone__icontains='Cocody').exclude(latitude__isnull=True)
        uniq = cocody.values('latitude', 'longitude').distinct().count()
        self.stdout.write(
            self.style.SUCCESS(
                f'GPS affinés: {updated} | Cocody unique: {uniq}/{cocody.count()}'
            )
        )
