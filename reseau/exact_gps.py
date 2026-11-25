"""Coordonnées GPS vérifiées (Nominatim / Google) — priorité absolue."""

from __future__ import annotations

import json
import re
from pathlib import Path

# id prestataire → (lat, lng)  OU motif nom → (lat, lng)
# Complété aussi via data/exact_gps.json
EXACT_BY_PATTERN: list[tuple[str, float, float]] = [
    # Pharmacie Sainte Famille Cocody (Cap Nord / Cité Allabra / Riviera 3)
    (r'PHARMACIE\s+SAINTE[\s\-]*FAMILLE', 5.3557089, -3.9673062),
    (r'VISION\s*2000', 5.3881002, -3.9733093),
    # Hôtel Palm Club — Boulevard André Latrille, Cocody (Nominatim)
    (r'PALM\s*CLUB', 5.3532676, -4.0024157),
    # Assil Optic — plus code Google 92M6+8RV Angré
    (r'ASSIL\s*OPTIC', 5.3833625, -3.9879531),
]

_DATA_FILE = Path(__file__).resolve().parent.parent / 'data' / 'exact_gps.json'
_CACHE: dict[str, tuple[float, float]] | None = None


def _load_json() -> dict[str, tuple[float, float]]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    _CACHE = {}
    if _DATA_FILE.exists():
        raw = json.loads(_DATA_FILE.read_text(encoding='utf-8'))
        for key, val in raw.items():
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                _CACHE[str(key)] = (float(val[0]), float(val[1]))
    return _CACHE


def lookup_exact(nom: str = '', adresse: str = '', zone: str = '', pk: int | None = None):
    data = _load_json()
    if pk is not None and str(pk) in data:
        return data[str(pk)]
    key = f'{(nom or "").strip().upper()}|{(zone or "").strip().upper()}'
    if key in data:
        return data[key]
    text = f'{nom} {adresse} {zone}'.upper()
    for pat, lat, lng in EXACT_BY_PATTERN:
        if re.search(pat, text, re.I):
            # Ne pas appliquer Sainte Famille hors Cocody / Abidjan
            if 'SAINTE' in pat.upper() and 'FAMILLE' in pat.upper():
                if any(x in text for x in ('ABENGOUROU', 'ABOISSO', 'BOUAKE', 'YAMOUSSOUKRO')):
                    continue
            return lat, lng
    return None
