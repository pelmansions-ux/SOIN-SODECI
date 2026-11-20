from django.db import models

from .types_soin import TYPE_CHOICES, TYPE_ICONS, TYPE_LABELS


class Prestataire(models.Model):
    numero_ordre = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    nom = models.CharField(max_length=255, db_index=True)
    nature = models.CharField(max_length=255, blank=True, help_text='Libellé brut Excel')
    type_soin = models.CharField(
        max_length=32,
        choices=TYPE_CHOICES,
        db_index=True,
        default='centre',
    )
    direction = models.CharField(max_length=255, blank=True, db_index=True)
    commune = models.CharField(max_length=255, blank=True, db_index=True)
    secteur = models.CharField(max_length=255, blank=True, db_index=True)
    zone = models.CharField(
        max_length=255,
        db_index=True,
        help_text='Quartier / commune / ville pour la recherche',
    )
    adresse = models.TextField(blank=True)
    telephone = models.CharField(max_length=255, blank=True)
    email = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    actif = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['nom']
        verbose_name = 'Prestataire'
        verbose_name_plural = 'Prestataires'
        indexes = [
            models.Index(fields=['zone', 'type_soin']),
            models.Index(fields=['actif', 'zone']),
        ]

    def __str__(self):
        return f'{self.nom} ({self.zone})'

    @property
    def has_coords(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def type_label(self):
        return TYPE_LABELS.get(self.type_soin, self.type_soin)

    @property
    def type_icon(self):
        return TYPE_ICONS.get(self.type_soin, '📍')

    @property
    def maps_url(self):
        if self.has_coords:
            return (
                f'https://www.google.com/maps/dir/?api=1'
                f'&destination={self.latitude},{self.longitude}'
            )
        query = f'{self.nom} {self.adresse} {self.commune} Côte d\'Ivoire'
        return f'https://www.google.com/maps/search/?api=1&query={query}'

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'nature': self.nature,
            'type': self.type_soin,
            'type_label': self.type_label,
            'type_icon': self.type_icon,
            'commune': self.commune,
            'secteur': self.secteur,
            'zone': self.zone,
            'adresse': self.adresse,
            'telephone': self.telephone,
            'email': self.email,
            'lat': self.latitude,
            'lng': self.longitude,
            'maps_url': self.maps_url,
        }
