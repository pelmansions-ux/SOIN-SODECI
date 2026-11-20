from django.contrib import admin

from .models import Prestataire


@admin.register(Prestataire)
class PrestataireAdmin(admin.ModelAdmin):
    list_display = (
        'nom',
        'type_soin',
        'zone',
        'commune',
        'telephone',
        'actif',
        'has_gps',
    )
    list_filter = ('type_soin', 'actif', 'commune', 'direction')
    search_fields = ('nom', 'zone', 'commune', 'secteur', 'adresse', 'telephone', 'email')
    list_editable = ('actif',)
    ordering = ('nom',)

    @admin.display(boolean=True, description='GPS')
    def has_gps(self, obj):
        return obj.has_coords
