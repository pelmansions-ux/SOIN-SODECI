from django.core.management.base import BaseCommand
from django.db.models import Q

from reseau.geo import resolve_coords
from reseau.models import Prestataire


class Command(BaseCommand):
    help = 'Complète latitude/longitude manquantes (cache local + Nominatim).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Nombre max à traiter (0 = tous)',
        )
        parser.add_argument(
            '--nominatim',
            action='store_true',
            help='Utiliser Nominatim pour les lieux inconnus du cache local',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recalculer même si des coords existent déjà',
        )

    def handle(self, *args, **options):
        qs = Prestataire.objects.filter(actif=True).order_by('id')
        if not options['force']:
            qs = qs.filter(Q(latitude__isnull=True) | Q(longitude__isnull=True))

        if options['limit']:
            qs = qs[: options['limit']]

        cache = {}
        ok = fail = 0
        missing = []

        for p in qs.iterator():
            coords = resolve_coords(
                commune=p.commune,
                secteur=p.secteur,
                zone=p.zone,
                adresse=p.adresse,
                nom=p.nom,
                use_nominatim=options['nominatim'],
                cache=cache,
            )
            if coords:
                p.latitude, p.longitude = coords
                p.save(update_fields=['latitude', 'longitude'])
                ok += 1
            else:
                fail += 1
                missing.append(f'#{p.id} {p.nom} — {p.zone or p.commune}')

        self.stdout.write(self.style.SUCCESS(f'Géocodés: {ok}'))
        if missing:
            self.stdout.write(self.style.WARNING(f'Non trouvés: {fail}'))
            for line in missing[:50]:
                self.stdout.write(f'  - {line}')
            if fail > 50:
                self.stdout.write(f'  … et {fail - 50} autres')
