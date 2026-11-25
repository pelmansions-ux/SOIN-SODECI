"""Google Maps Platform — Routes API (distances & itinéraires comme l’app Maps)."""

from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


def google_api_key() -> str:
    return (
        os.environ.get('GOOGLE_MAPS_API_KEY')
        or os.environ.get('GOOGLE_API_KEY')
        or ''
    ).strip()


def _ssl_get(url: str, timeout: int = 15) -> dict | None:
    req = urllib.request.Request(url, headers={'User-Agent': 'SoinSODECI/2.6'})
    contexts = [ssl.create_default_context(), ssl._create_unverified_context()]
    for ctx in contexts:
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            continue
    return None


def _ssl_post_json(
    url: str,
    body: dict,
    headers: dict,
    timeout: int = 20,
) -> tuple[int, bytes]:
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST', headers=headers)
    contexts = [ssl.create_default_context(), ssl._create_unverified_context()]
    last_exc: Exception | None = None
    for ctx in contexts:
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read() if exc.fp else b''
        except Exception as exc:
            last_exc = exc
            continue
    raise last_exc or RuntimeError('POST failed')


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


def _parse_route_matrix_body(raw: bytes) -> list[dict]:
    """Routes API renvoie un tableau JSON ou un flux NDJSON."""
    text = raw.decode('utf-8').strip()
    if not text:
        return []
    if text.startswith('['):
        data = json.loads(text)
        return data if isinstance(data, list) else []
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _routes_matrix_km(
    origin_lat: float,
    origin_lng: float,
    destinations: list[tuple[float, float]],
    mode: str = 'driving',
) -> list[float | None] | None:
    """Routes API computeRouteMatrix. None = API indisponible."""
    key = google_api_key()
    if not key or not destinations:
        return None

    travel = 'WALK' if mode == 'foot' else 'DRIVE'
    out: list[float | None] = [None] * len(destinations)
    chunk = 25
    any_ok = False

    for start in range(0, len(destinations), chunk):
        batch = destinations[start : start + chunk]
        body = {
            'origins': [
                {
                    'waypoint': {
                        'location': {
                            'latLng': {
                                'latitude': origin_lat,
                                'longitude': origin_lng,
                            }
                        }
                    }
                }
            ],
            'destinations': [
                {
                    'waypoint': {
                        'location': {
                            'latLng': {'latitude': lat, 'longitude': lng}
                        }
                    }
                }
                for lat, lng in batch
            ],
            'travelMode': travel,
            'routingPreference': 'TRAFFIC_UNAWARE',
            'units': 'METRIC',
            'languageCode': 'fr',
            'regionCode': 'CI',
        }
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': key,
            'X-Goog-FieldMask': (
                'originIndex,destinationIndex,duration,distanceMeters,status,condition'
            ),
            'User-Agent': 'SoinSODECI/2.6',
        }
        try:
            status, raw = _ssl_post_json(
                'https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix',
                body,
                headers,
            )
        except Exception as exc:
            logger.warning('Routes matrix network error: %s', exc)
            return None

        if status != 200:
            try:
                err = json.loads(raw.decode('utf-8'))
                msg = (err[0] if isinstance(err, list) else err).get('error', {}).get(
                    'message', raw[:200]
                )
            except Exception:
                msg = raw[:200]
            logger.warning('Routes matrix HTTP %s: %s', status, msg)
            return None

        for row in _parse_route_matrix_body(raw):
            if row.get('condition') and row.get('condition') != 'ROUTE_EXISTS':
                continue
            dest_i = row.get('destinationIndex')
            meters = row.get('distanceMeters')
            if dest_i is None or meters is None:
                continue
            out[start + int(dest_i)] = round(float(meters) / 1000.0, 2)
            any_ok = True

    return out if any_ok else None


def _legacy_matrix_km(
    origin_lat: float,
    origin_lng: float,
    destinations: list[tuple[float, float]],
    mode: str = 'driving',
) -> list[float | None] | None:
    """Ancienne Distance Matrix API (si encore activée sur le projet)."""
    key = google_api_key()
    if not key or not destinations:
        return None

    out: list[float | None] = [None] * len(destinations)
    chunk = 25
    travel = 'walking' if mode == 'foot' else 'driving'
    any_ok = False

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
        if not data:
            continue
        status = data.get('status')
        if status != 'OK':
            logger.warning(
                'Legacy Distance Matrix %s: %s',
                status,
                data.get('error_message', ''),
            )
            return None
        elements = (data.get('rows') or [{}])[0].get('elements') or []
        for i, el in enumerate(elements):
            if el.get('status') != 'OK':
                continue
            meters = float((el.get('distance') or {}).get('value') or 0)
            out[start + i] = round(meters / 1000.0, 2)
            any_ok = True

    return out if any_ok else None


def google_distance_matrix_km(
    origin_lat: float,
    origin_lng: float,
    destinations: list[tuple[float, float]],
    mode: str = 'driving',
) -> list[float | None]:
    """
    Distances routières Google (km), alignées sur destinations.
    Priorité : Routes API → Distance Matrix legacy.
    """
    if not destinations:
        return []
    routes = _routes_matrix_km(origin_lat, origin_lng, destinations, mode=mode)
    if routes is not None and any(d is not None for d in routes):
        return routes
    legacy = _legacy_matrix_km(origin_lat, origin_lng, destinations, mode=mode)
    if legacy is not None and any(d is not None for d in legacy):
        return legacy
    return [None] * len(destinations)


def google_matrix_ok(
    origin_lat: float,
    origin_lng: float,
    destinations: list[tuple[float, float]],
    mode: str = 'driving',
) -> tuple[list[float | None], bool]:
    """Comme google_distance_matrix_km + flag « vraiment Google »."""
    dists = google_distance_matrix_km(origin_lat, origin_lng, destinations, mode=mode)
    return dists, any(d is not None for d in dists)


def _routes_directions(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    mode: str = 'car',
) -> dict | None:
    key = google_api_key()
    if not key:
        return None

    travel = 'WALK' if mode == 'foot' else 'DRIVE'
    body = {
        'origin': {
            'location': {
                'latLng': {'latitude': origin_lat, 'longitude': origin_lng}
            }
        },
        'destination': {
            'location': {
                'latLng': {'latitude': dest_lat, 'longitude': dest_lng}
            }
        },
        'travelMode': travel,
        'routingPreference': 'TRAFFIC_UNAWARE',
        'languageCode': 'fr',
        'regionCode': 'CI',
        'units': 'METRIC',
    }
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': key,
        'X-Goog-FieldMask': (
            'routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline'
        ),
        'User-Agent': 'SoinSODECI/2.6',
    }
    try:
        status, raw = _ssl_post_json(
            'https://routes.googleapis.com/directions/v2:computeRoutes',
            body,
            headers,
        )
    except Exception as exc:
        logger.warning('Routes directions network error: %s', exc)
        return None

    if status != 200:
        logger.warning('Routes directions HTTP %s: %s', status, raw[:300])
        return None

    try:
        data = json.loads(raw.decode('utf-8'))
    except json.JSONDecodeError:
        return None

    routes = data.get('routes') or []
    if not routes:
        return None

    route = routes[0]
    meters = float(route.get('distanceMeters') or 0)
    dur = route.get('duration') or '0s'
    seconds = float(str(dur).rstrip('s') or 0)
    poly = ((route.get('polyline') or {}).get('encodedPolyline')) or ''
    coords = (
        _decode_polyline(poly)
        if poly
        else [[origin_lat, origin_lng], [dest_lat, dest_lng]]
    )

    from reseau.geo import format_distance_km

    return {
        'mode': mode,
        'distance_km': round(meters / 1000.0, 2),
        'distance_label': format_distance_km(meters / 1000.0),
        'duration_min': max(1, int(round(seconds / 60.0))),
        'coordinates': coords,
        'provider': 'google',
    }


def _legacy_directions(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    mode: str = 'car',
) -> dict | None:
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
        if data:
            logger.warning(
                'Legacy Directions %s: %s',
                data.get('status'),
                data.get('error_message', ''),
            )
        return None

    route = data['routes'][0]
    leg = (route.get('legs') or [{}])[0]
    meters = float((leg.get('distance') or {}).get('value') or 0)
    seconds = float((leg.get('duration') or {}).get('value') or 0)
    poly = (route.get('overview_polyline') or {}).get('points') or ''
    coords = (
        _decode_polyline(poly)
        if poly
        else [[origin_lat, origin_lng], [dest_lat, dest_lng]]
    )

    from reseau.geo import format_distance_km

    return {
        'mode': mode,
        'distance_km': round(meters / 1000.0, 2),
        'distance_label': format_distance_km(meters / 1000.0),
        'duration_min': max(1, int(round(seconds / 60.0))),
        'coordinates': coords,
        'provider': 'google',
    }


def google_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    mode: str = 'car',
) -> dict | None:
    """Itinéraire Google (Routes API puis Directions legacy)."""
    route = _routes_directions(origin_lat, origin_lng, dest_lat, dest_lng, mode=mode)
    if route:
        return route
    return _legacy_directions(origin_lat, origin_lng, dest_lat, dest_lng, mode=mode)


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
        if data:
            logger.warning(
                'Geocoding %s: %s', data.get('status'), data.get('error_message', '')
            )
        return None
    loc = data['results'][0]['geometry']['location']
    return float(loc['lat']), float(loc['lng'])
