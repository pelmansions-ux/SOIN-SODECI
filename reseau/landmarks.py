"""Repères GPS Abidjan / CI — prioriser les adresses précises (ex. Palm Club)."""

from __future__ import annotations

import hashlib
import re

# Ordre = priorité (plus précis en premier). Coords proches Google Maps.
LANDMARKS: list[tuple[str, float, float]] = [
    # --- Cocody très précis (coords Nominatim / repères Google) ---
    (r'VISION\s*2000', 5.3881002, -3.9733093),  # Caféier / Cocody (Nominatim)
    (r'PALM\s*CLUB|HOTEL\s*PALM', 5.3532676, -4.0024157),
    (r'LYC[EÉ]E\s*TECHNIQUE', 5.3398, -3.9912),
    (r'CARREFOUR\s*ABATTA', 5.3726499, -3.9292045),
    (r'\bABATTA\b', 5.3726499, -3.9292045),
    (r'B(OULE)?V(AR)?D\.?\s*DES\s*MARTYRS|BD\s*DES\s*MARTYRS', 5.3480, -3.9945),
    (r'CHU\s*(DE\s*)?COCODY|CHU\s*COCODY|INFES', 5.3465, -3.9868),
    (r'FAYA|G[EÉ]NIE\s*2000', 5.3920, -3.9580),
    (r'CORNICHE|STE\s*ANNE|SAINTE\s*ANNE\s*MARIE|PISAM', 5.3285, -3.9805),
    (r'SOCOCE', 5.3545, -3.9860),
    (r'ABIDJAN\s*MALL|BONOUMIN', 5.3520, -3.9780),
    (r'WINNER\s*CHAPEL', 5.3780, -3.9480),
    (r'CAF[EÉ]IER', 5.3881, -3.9733),
    (r'MAISON\s*PALMIER', 5.3520, -3.9880),
    (r'DEUX\s*PLATEAUX|2\s*PLATEAUX|2PLATEAUX|II\s*PLATEAUX|IIPLATEAUX', 5.3540, -3.9890),
    (r'RIVIERA\s*3|RIVIERA\s*III', 5.3555, -3.9480),
    (r'RIVIERA\s*2|RIVIERA\s*II|ALPHA\s*BLONDY', 5.3480, -3.9600),
    (r'RIVIERA\s*PALMERAIE|PALMERAIE|PALMERAIRE', 5.3800, -3.9600),
    (r'RIVIERA\s*1|RIVIERA\s*I\b', 5.3450, -3.9700),
    (r'RIVIERA', 5.3500, -3.9650),
    (r'ANGRE|ANGR[EÉ]', 5.3980, -3.9800),
    (r'JEAN\s*MERMOZ|MERMOZ', 5.3400, -3.9850),
    (r'COCODY\s*NORD|GRANDE\s*OURSE', 5.3720, -3.9780),
    (r'BLOCKHAUS|BLOC\s*HAUS', 5.3450, -3.9920),
    (r'AMBASSADES', 5.3350, -3.9950),
    (r'ST\s*JEAN|SAINT\s*JEAN', 5.3580, -3.9820),
    (r'VAL\s*DODO', 5.3650, -3.9700),
    (r'ATTOBAN', 5.3750, -3.9400),
    (r'DANGA', 5.3580, -3.9950),
    (r'DANGUI|DANGUIRA', 5.3680, -3.9550),
    (r'SID[EÉ]CI', 5.3500, -3.9800),
    (r'RTI', 5.3550, -3.9980),
    (r'ENA\b|ECOLE\s*NATIONALE\s*D.?ADMINISTRATION', 5.3410, -3.9880),
    (r'ZOO', 5.3450, -3.9950),
    # Autres Abidjan
    (r'ZONE\s*4', 5.2950, -3.9950),
    (r'TREICHVILLE', 5.2900, -4.0050),
    (r'MARCORY', 5.3000, -3.9833),
    (r'PLATEAU', 5.3200, -4.0200),
    (r'ADJAME|ADJam[EÉ]', 5.3531, -4.0231),
    (r'YOPOUGON|NIANGON', 5.3364, -4.0847),
    (r'ABOBO', 5.4167, -4.0167),
    (r'PORT[\s\-]?BOUET|VRIDI', 5.2564, -3.9631),
    (r'BINGERVILLE', 5.3558, -3.8853),
    (r'ANYAMA', 5.4947, -4.0517),
    (r'SONGON', 5.3167, -4.2500),
    # Koumassi
    (r'BOULEVARD DU CAMEROUN|BLVD DU CAMEROUN|REMBLAIS', 5.2932, -3.9690),
    (r'BOULEVARD DU GABON|BLVD DU GABON', 5.2885, -3.9558),
    (r'KAHIRA', 5.3004, -3.9644),
    (r'MARAIS', 5.3012, -3.9576),
    (r'KOUMASSI', 5.2900, -3.9600),
]

COMMUNE_FALLBACK: dict[str, tuple[float, float]] = {
    'COCODY': (5.3600, -3.9880),
    'YOPOUGON': (5.3364, -4.0847),
    'ABOBO': (5.4167, -4.0167),
    'KOUMASSI': (5.2900, -3.9600),
    'MARCORY': (5.3000, -3.9833),
    'TREICHVILLE': (5.2900, -4.0050),
    'PLATEAU': (5.3200, -4.0200),
    'PORT-BOUET': (5.2564, -3.9631),
    'PORT BOUET': (5.2564, -3.9631),
    'ADJAME': (5.3531, -4.0231),
}


def _hash_offset(seed: str, scale: float) -> tuple[float, float]:
    h = int(hashlib.md5(seed.encode('utf-8')).hexdigest()[:8], 16)
    dlat = ((h % 41) - 20) * scale
    dlng = (((h // 41) % 41) - 20) * scale
    return dlat, dlng


def refine_coords(
    zone: str = '',
    secteur: str = '',
    adresse: str = '',
    nom: str = '',
    commune: str = '',
    fallback=None,
    force_unique: bool = False,
    pk: int | None = None,
):
    from reseau.exact_gps import lookup_exact

    # 1) Coordonnées vérifiées (Nominatim / Google) — aucun décalage
    exact = lookup_exact(nom=nom, adresse=adresse, zone=zone, pk=pk)
    if exact:
        return exact

    text = f'{adresse} {secteur} {zone} {commune} {nom}'.upper()
    base = None
    precise = False
    for pat, lat, lng in LANDMARKS:
        if re.search(pat, text, re.I):
            base = (lat, lng)
            precise = True
            break

    if base is None:
        for key, coords in COMMUNE_FALLBACK.items():
            if key in text:
                base = coords
                break

    if base is None:
        base = fallback
    if base is None:
        return None

    # Landmark précis : petit écart (~15–80 m) pour rester fidèle à Google
    # Commune seule : écart plus large pour différencier les fiches
    scale = 0.00009 if precise else 0.00055
    if force_unique and not precise:
        scale *= 1.35
    dlat, dlng = _hash_offset(f'{nom}|{adresse}|{zone}', scale)
    return base[0] + dlat, base[1] + dlng
