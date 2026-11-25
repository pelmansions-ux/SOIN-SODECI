from django.core.management.base import BaseCommand

from reseau.exact_gps import lookup_exact
from reseau.models import Prestataire


class Command(BaseCommand):
    help = 'Applique data/exact_gps.json et les motifs exacts sur la base.'

    def handle(self, *args, **options):
        n = 0
        for p in Prestataire.objects.filter(actif=True).iterator():
            coords = lookup_exact(nom=p.nom, adresse=p.adresse, zone=p.zone, pk=p.pk)
            if not coords:
                continue
            if p.latitude != coords[0] or p.longitude != coords[1]:
                p.latitude, p.longitude = coords
                p.save(update_fields=['latitude', 'longitude'])
                n += 1
        self.stdout.write(self.style.SUCCESS(f'GPS exacts appliqués: {n}'))
