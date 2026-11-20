from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .models import Prestataire
from .types_soin import normalize_type


class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(username='employe', password='testpass123')

    def test_zone_requires_login(self):
        response = self.client.get('/zone/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_api_requires_login(self):
        response = self.client.get('/api/prestataires/')
        self.assertEqual(response.status_code, 302)


class FilterApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(username='employe', password='testpass123')
        Prestataire.objects.create(
            nom='Pharmacie Test',
            nature='PHARMACIE',
            type_soin='pharmacie',
            commune='YOPOUGON',
            secteur='YOPOUGON',
            zone='YOPOUGON',
            latitude=5.33,
            longitude=-4.08,
            actif=True,
        )
        Prestataire.objects.create(
            nom='Clinique Test',
            nature='CLINIQUE',
            type_soin='hopital',
            commune='YOPOUGON',
            secteur='YOPOUGON',
            zone='YOPOUGON',
            latitude=5.34,
            longitude=-4.09,
            actif=True,
        )
        Prestataire.objects.create(
            nom='Optique Cocody',
            nature='OPTIQUE',
            type_soin='optique',
            commune='COCODY',
            zone='COCODY',
            actif=True,
        )

    def test_normalize_type(self):
        self.assertEqual(normalize_type('PHARMACIE JEAN'), 'pharmacie')
        self.assertEqual(normalize_type('CLINIQUE ET POLYCLINIQUE'), 'hopital')
        self.assertEqual(normalize_type('CENTRE ET CABINET DENTAIRE'), 'dentaire')

    def test_api_filter_zone_and_type(self):
        self.client.login(username='employe', password='testpass123')
        response = self.client.get(
            '/api/prestataires/',
            {'zone': 'YOPOUGON', 'type': 'pharmacie'},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['nom'], 'Pharmacie Test')

    def test_api_sorted_by_distance(self):
        self.client.login(username='employe', password='testpass123')
        response = self.client.get(
            '/api/prestataires/',
            {'lat': '5.33', 'lng': '-4.08', 'type': 'tous'},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['sorted_by_distance'])
        self.assertGreaterEqual(len(data['results']), 2)
        dists = [r['distance_km'] for r in data['results'] if 'distance_km' in r]
        self.assertEqual(dists, sorted(dists))
        self.assertEqual(data['results'][0]['nom'], 'Pharmacie Test')

    def test_results_page_direct(self):
        self.client.login(username='employe', password='testpass123')
        response = self.client.get('/resultats/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'À proximité')

    def test_zone_redirects_to_results(self):
        self.client.login(username='employe', password='testpass123')
        response = self.client.get('/zone/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/resultats/', response.url)
