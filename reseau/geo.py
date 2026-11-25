"""Coordonnées locales + Nominatim."""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request

COMMUNE_COORDS: dict[str, tuple[float, float]] = {
    'ABENGOUROU': (6.7296, -3.4964),
    'ABIDJAN': (5.3600, -4.0083),
    'ABOBO': (5.4167, -4.0167),
    'ABOISSO': (5.4667, -3.2000),
    'ADJAME': (5.3531, -4.0231),
    'ADZOPE': (6.1069, -3.8619),
    'AGBOVILLE': (5.9280, -4.2132),
    'AGNIBILEKRO': (7.1333, -3.2000),
    'AKOUPE': (6.3842, -3.8875),
    'ANYAMA': (5.4947, -4.0517),
    'BINGERVILLE': (5.3558, -3.8853),
    'BONDOUKOU': (8.0402, -2.8000),
    'BOUAKE': (7.6906, -5.0303),
    'BOUNA': (9.2667, -2.9833),
    'BOUNDIALI': (9.5217, -6.4869),
    'COCODY': (5.3600, -3.9880),
    'DABOU': (5.3256, -4.3767),
    'DALOA': (6.8774, -6.4502),
    'DANANE': (7.2597, -8.1556),
    'DAOUKRO': (7.0589, -3.9631),
    'DIMBOKRO': (6.6469, -4.7050),
    'DIVO': (5.8372, -5.3572),
    'DUEKOUE': (6.7422, -7.3492),
    'FERKESSEDOUGOU': (9.5939, -5.1978),
    'GAGNOA': (6.1319, -5.9506),
    'GRAND BASSAM': (5.2111, -3.7389),
    'GRAND-BASSAM': (5.2111, -3.7389),
    'GUIGLO': (6.5436, -7.4936),
    'ISSIA': (6.4922, -6.5856),
    'JACQUEVILLE': (5.2056, -4.4153),
    'KATIOLA': (8.1372, -5.1011),
    'KORHOGO': (9.4581, -5.6296),
    'KOUMASSI': (5.3000, -3.9500),
    'LAKOTA': (5.8478, -5.6822),
    'MAN': (7.4125, -7.5539),
    'MARCORY': (5.3000, -3.9833),
    'ODIENNE': (9.5092, -7.5642),
    'OUME': (6.3833, -5.4167),
    'PLATEAU': (5.3200, -4.0200),
    'PORT BOUET': (5.2564, -3.9631),
    'PORT-BOUET': (5.2564, -3.9631),
    'SAN PEDRO': (4.7485, -6.6363),
    'SAN-PEDRO': (4.7485, -6.6363),
    'SASSANDRA': (4.9500, -6.0833),
    'SEGUELA': (7.9611, -6.6731),
    'SINFRA': (7.6167, -5.9167),
    'SOUBRE': (5.7839, -6.5939),
    'TIASSALE': (5.8983, -4.8283),
    'TREICHVILLE': (5.2900, -4.0050),
    'VAVOUA': (7.3819, -6.4778),
    'YAMOUSSOUKRO': (6.8276, -5.2893),
    'YOPOUGON': (5.3364, -4.0847),
    'ANGRE': (5.3980, -3.9800),
    'PALMERAIE': (5.3800, -3.9600),
    'RIVIERA': (5.3700, -3.9700),
    'SONGON': (5.3167, -4.2500),
    'BONOUA': (5.2722, -3.6000),
    'ASSINIE': (5.1333, -3.2833),
    'TOUMODI': (6.4833, -5.0167),
    'BOUAFLE': (6.9903, -5.7442),
    'TAABO': (6.3167, -5.1000),
    'TANDA': (7.8033, -3.1683),
    'BUYO': (6.2500, -7.0500),
    'DIKODOUGOU': (9.5167, -5.7667),
    'AYAME': (5.6000, -3.1667),
    'BONGOUANOU': (6.6500, -4.2000),
    'MAFERE': (5.4167, -3.0333),
    'NIAKARA': (8.6667, -5.2833),
    'DABAKALA': (8.3667, -4.4333),
    "M'BATTO": (6.4833, -4.3667),
    'MBATTO': (6.4833, -4.3667),
    'SAIOUA': (6.4833, -5.9500),
    'ATTINGUIE': (5.4167, -4.1833),
    'GUIBEROUA': (6.2333, -6.1667),
    'MEAGUI': (5.4167, -6.5500),
    'ADIAKE': (5.2864, -3.3042),
    'AFFERY': (6.3167, -3.9500),
    'AGOU': (5.8167, -4.0000),
    'BOCANDA': (7.0667, -4.5000),
    'DIEGONEFLA': (6.5833, -5.9333),
    'GUITRY': (5.5167, -5.2333),
    'TAFIRE': (9.0667, -5.1667),
    'KOSSOU': (7.0000, -5.4667),
    'MBENGUE': (9.8500, -5.7500),
    'SINEMATIALI': (9.5833, -5.4000),
    'VRIDI': (5.2500, -4.0000),
    'YAKASSE ATTOBROU': (5.8000, -3.6500),
    'ALEPE': (5.5000, -3.6667),
    'SIKENSI': (5.3667, -4.1500),
    'TIEBISSOU': (7.1667, -5.2333),
    'ZUENOULA': (7.4333, -6.0500),
    'BANGOLO': (7.0167, -7.4833),
    'BIANKOUMA': (7.7333, -7.6167),
    'FRESCO': (5.0833, -5.5667),
    'TABOU': (4.4167, -7.3500),
    'TINGRELA': (10.4897, -6.4069),
    'TENGRELA': (10.4897, -6.4069),
}


def normalize_key(value: str) -> str:
    return (
        (value or '')
        .upper()
        .strip()
        .replace('É', 'E')
        .replace('È', 'E')
        .replace('Ê', 'E')
        .replace('À', 'A')
        .replace('Â', 'A')
        .replace('Ô', 'O')
        .replace('Î', 'I')
        .replace('Û', 'U')
        .replace('Ç', 'C')
    )


def coords_for_place(*candidates: str) -> tuple[float, float] | None:
    for candidate in candidates:
        key = normalize_key(candidate)
        if not key:
            continue
        if key in COMMUNE_COORDS:
            return COMMUNE_COORDS[key]
        for known, coords in COMMUNE_COORDS.items():
            if known in key or key in known:
                return coords
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def format_distance_km(dist_km: float) -> str:
    if dist_km < 1:
        return f'{int(round(dist_km * 1000))} m'
    return f'{dist_km:.2f}'.replace('.', ',') + ' km'


def realistic_road_km(air_km: float | None, road_km: float | None) -> tuple[float | None, str]:
    """
    Distance affichée proche de Google Maps.
    OSRM public à Abidjan allonge souvent beaucoup les trajets ;
    on corrige avec un facteur urbain réaliste (~1,20 × vol d'oiseau),
    proche de Google Maps.
    """
    urban = 1.20
    if road_km is None and air_km is None:
        return None, 'none'
    if road_km is None:
        return round(air_km * urban, 2), 'est'
    if air_km is None:
        return round(road_km, 2), 'driving'

    # Trop court (même nœud OSM) alors que les points sont éloignés
    if air_km >= 0.2 and road_km < air_km * 0.4:
        return round(air_km * urban, 2), 'est'

    # OSRM trop long vs réalité Google (~1,15–1,5× air en ville)
    if air_km >= 0.15 and road_km > air_km * 1.65:
        return round(air_km * urban, 2), 'est'

    return round(road_km, 2), 'driving'


def estimate_duration_min(dist_km: float, mode: str = 'car') -> int:
    """Durée approximative (ville ~22 km/h, pied ~4,5 km/h)."""
    if dist_km is None or dist_km <= 0:
        return 1
    speed = 4.5 if mode == 'foot' else 22.0
    return max(1, int(round((dist_km / speed) * 60)))


def _osrm_table(url: str, user_agent: str, n_dest: int) -> list[float | None]:
    import ssl

    req = urllib.request.Request(url, headers={'User-Agent': user_agent})
    contexts = [ssl.create_default_context(), ssl._create_unverified_context()]
    data = None
    last_err = None
    for ctx in contexts:
        try:
            with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            break
        except Exception as exc:  # SSLError souvent encapsulé dans URLError sous Windows
            last_err = exc
            continue
    if data is None:
        raise last_err or RuntimeError('OSRM indisponible')

    if data.get('code') != 'Ok':
        return [None] * n_dest
    row = (data.get('distances') or [[]])[0]
    out: list[float | None] = []
    for i in range(n_dest):
        meters = row[i + 1] if i + 1 < len(row) else None
        if meters is None:
            out.append(None)
        else:
            out.append(round(float(meters) / 1000.0, 2))
    return out


def osrm_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    mode: str = 'car',
    user_agent: str = 'SoinSODECI/2.1',
) -> dict | None:
    """Itinéraire OSRM (voiture ou pied) avec géométrie."""
    import ssl

    path = f'{origin_lng},{origin_lat};{dest_lng},{dest_lat}?overview=full&geometries=geojson'
    if mode == 'foot':
        endpoints = [
            'https://routing.openstreetmap.de/routed-foot/route/v1/driving/',
        ]
    else:
        endpoints = [
            'https://router.project-osrm.org/route/v1/driving/',
            'https://routing.openstreetmap.de/routed-car/route/v1/driving/',
        ]

    contexts = [ssl.create_default_context(), ssl._create_unverified_context()]
    for base in endpoints:
        url = base + path
        req = urllib.request.Request(url, headers={'User-Agent': user_agent})
        for ctx in contexts:
            try:
                with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                if data.get('code') != 'Ok' or not data.get('routes'):
                    break
                route = data['routes'][0]
                meters = float(route.get('distance') or 0)
                seconds = float(route.get('duration') or 0)
                coords = route.get('geometry', {}).get('coordinates') or []
                latlngs = [[c[1], c[0]] for c in coords]
                return {
                    'mode': mode,
                    'distance_km': round(meters / 1000.0, 2),
                    'distance_label': format_distance_km(meters / 1000.0),
                    'duration_min': max(1, int(round(seconds / 60.0))),
                    'coordinates': latlngs,
                }
            except Exception:
                continue
    return None


def driving_route(origin_lat, origin_lng, dest_lat, dest_lng, user_agent='SoinSODECI/2.1'):
    return osrm_route(origin_lat, origin_lng, dest_lat, dest_lng, mode='car', user_agent=user_agent)


def walking_route(origin_lat, origin_lng, dest_lat, dest_lng, user_agent='SoinSODECI/2.1'):
    return osrm_route(origin_lat, origin_lng, dest_lat, dest_lng, mode='foot', user_agent=user_agent)


def road_distances_km(
    origin_lat: float,
    origin_lng: float,
    destinations: list[tuple[float, float]],
    user_agent: str = 'SoinSODECI/2.1',
) -> list[float | None]:
    """
    Distances routières (voiture) via OSRM — proches de Google Maps.
    Retourne une liste alignée sur destinations (None si indisponible).
    """
    if not destinations:
        return []

    # OSRM: lon,lat — source = position utilisateur
    coords = [f'{origin_lng},{origin_lat}']
    for lat, lng in destinations[:40]:
        coords.append(f'{lng},{lat}')

    path = ';'.join(coords) + '?sources=0&annotations=distance'
    endpoints = [
        'https://router.project-osrm.org/table/v1/driving/',
        'https://routing.openstreetmap.de/routed-car/table/v1/driving/',
    ]

    for base in endpoints:
        try:
            return _osrm_table(base + path, user_agent, len(destinations))
        except Exception:
            continue
    return [None] * len(destinations)


def geocode_nominatim(query: str, user_agent: str = 'SoinSODECI/2.0 (contact: rh@sodeci.local)') -> tuple[float, float] | None:
    params = urllib.parse.urlencode(
        {'q': query, 'format': 'json', 'limit': 1, 'countrycodes': 'ci'}
    )
    url = f'https://nominatim.openstreetmap.org/search?{params}'
    req = urllib.request.Request(url, headers={'User-Agent': user_agent})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        return None
    return None


def resolve_coords(commune='', secteur='', zone='', adresse='', nom='', use_nominatim=False, cache=None):
    from reseau.landmarks import refine_coords

    cache = cache if cache is not None else {}
    fallback = coords_for_place(zone, commune, secteur)

    if not fallback and use_nominatim:
        for query in (
            f'{adresse}, {commune}, Côte d\'Ivoire' if adresse else '',
            f'{zone}, Côte d\'Ivoire' if zone else '',
            f'{commune}, Côte d\'Ivoire' if commune else '',
            f'{nom}, {commune}, Côte d\'Ivoire' if nom else '',
        ):
            query = query.strip(', ')
            if not query or query == "Côte d'Ivoire":
                continue
            if query in cache:
                if cache[query]:
                    fallback = cache[query]
                    break
                continue
            result = geocode_nominatim(query)
            time.sleep(1.1)
            cache[query] = result
            if result:
                fallback = result
                break

    return refine_coords(
        zone=zone,
        secteur=secteur,
        adresse=adresse,
        nom=nom,
        commune=commune,
        fallback=fallback,
        force_unique=True,
    )
