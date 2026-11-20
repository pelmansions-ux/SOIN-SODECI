from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crée les comptes démo employé / admin s’ils n’existent pas.'

    def handle(self, *args, **options):
        User = get_user_model()
        specs = [
            ('employe', 'sodeci2025', False),
            ('admin', 'admin2025', True),
        ]
        for username, password, is_super in specs:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'is_staff': is_super, 'is_superuser': is_super},
            )
            if created:
                user.set_password(password)
                user.is_staff = is_super
                user.is_superuser = is_super
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Créé: {username}'))
            else:
                self.stdout.write(f'Déjà présent: {username}')
