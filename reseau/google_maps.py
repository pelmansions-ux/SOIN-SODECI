"""Google Maps Platform — distances & itinéraires (comme l’app Google Maps)."""

from __future__ import annotations

import json
import os
import ssl
import urllib.parse
import urllib.request


def google_api_key() -> str:
    return (
        os.environ.get('GOOGLE_MAPS_API_KEY')
        or os.environ.get('GOOGLE_API_KEY')
        or ''
    ).strip()


def _ssl_get(url: str, timeout: int = 15) -> dict | None:
    req = urllib.request.Request(url, headers={'User-Agent': 'SoinSODECI/2.5'})
    contexts = [ssl.create_default_context(), ssl._create_unverified_context()]
    last = None
    for ctx in contexts:
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as exc:
            last = exc
            continue
    return None


def _decode_polyline(polyline: str) -> list[list[float]]:
    """Décode une polyline Google encodée → [[lat, lng], ...]."""
    coordinates: list[list[float]] = []
    index = lat = lng = 0
    length = len(polyline)
    while index < length:
        for coord in (0, 1):
            result = shift = 0
            while True:
                b = ord(polyline[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else (result >> 1)
            if coord == 0:
                lat += delta
            else:
                lng += delta
        coordinates.append([lat / 1e5, lng / 1e5])
    return coordinates


def google_distance_matrix_km(
    origin_lat: float,
    origin_lng: float,
    destinations: list[tuple[float, float]],
    mode: str = 'driving',
) -> list[float | None]:
    """Distances routières Google (km). Aligné destinations."""
    key = google_api_key()
    if not key or not destinations:
        return [None] * len(destinations)

    # API limite ~25 destinations / requête
    out: list[float | None] = [None] * len(destinations)
    chunk = 25
    travel = 'walking' if mode == 'foot' else 'driving'

    for start in range(0, len(destinations), chunk):
        batch = destinations[start : start + chunk]
        dests = '|'.join(f'{lat},{lng}' for lat, lng in batch)
        params = urllib.parse.urlencode(
            {
                'origins': f'{origin_lat},{origin_lng}',
                'destinations': dests,
                'mode': travel,
                'language': 'fr',
                'units': 'metric',
                'key': key,
            }
        )
        url = f'https://maps.googleapis.com/maps/api/distancematrix/json?{params}'
        data = _ssl_get(url)
        if not data or data.get('status') != 'OK':
            continue
        elements = (data.get('rows') or [{}])[0].get('elements') or []
        for i, el in enumerate(elements):
            if el.get('status') != 'OK':
                continue
            meters = float((el.get('distance') or {}).get('value') or 0)
            out[start + i] = round(meters / 1000.0, 2)
    return out


def google_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    mode: str = 'car',
) -> dict | None:
    """Itinéraire Google Directions + géométrie."""
    key = google_api_key()
    if not key:
        return None

    travel = 'walking' if mode == 'foot' else 'driving'
    params = urllib.parse.urlencode(
        {
            'origin': f'{origin_lat},{origin_lng}',
            'destination': f'{dest_lat},{dest_lng}',
            'mode': travel,
            'language': 'fr',
            'units': 'metric',
            'key': key,
        }
    )
    url = f'https://maps.googleapis.com/maps/api/directions/json?{params}'
    data = _ssl_get(url, timeout=20)
    if not data or data.get('status') != 'OK' or not data.get('routes'):
        return None

    route = data['routes'][0]
    leg = (route.get('legs') or [{}])[0]
    meters = float((leg.get('distance') or {}).get('value') or 0)
    seconds = float((leg.get('duration') or {}).get('value') or 0)
    poly = (route.get('overview_polyline') or {}).get('points') or ''
    coords = _decode_polyline(poly) if poly else [[origin_lat, origin_lng], [dest_lat, dest_lng]]

    from reseau.geo import format_distance_km

    return {
        'mode': mode,
        'distance_km': round(meters / 1000.0, 2),
        'distance_label': format_distance_km(meters / 1000.0),
        'duration_min': max(1, int(round(seconds / 60.0))),
        'coordinates': coords,
        'provider': 'google',
    }


def google_geocode(address: str) -> tuple[float, float] | None:
    key = google_api_key()
    if not key or not address:
        return None
    params = urllib.parse.urlencode(
        {
            'address': address,
            'region': 'ci',
            'language': 'fr',
            'key': key,
        }
    )
    url = f'https://maps.googleapis.com/maps/api/geocode/json?{params}'
    data = _ssl_get(url)
    if not data or data.get('status') != 'OK' or not data.get('results'):
        return None
    loc = data['results'][0]['geometry']['location']
    return float(loc['lat']), float(loc['lng'])
