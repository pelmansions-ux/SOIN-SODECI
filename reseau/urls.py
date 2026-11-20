from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('zone/', views.zone_picker, name='zone'),
    path('resultats/', views.results, name='results'),
    path('api/prestataires/', views.api_prestataires, name='api_prestataires'),
    path('api/zones/', views.api_zones, name='api_zones'),
    path('api/prestataire/<int:pk>/', views.api_detail, name='api_detail'),
    path('api/itineraire/', views.api_itineraire, name='api_itineraire'),
]
