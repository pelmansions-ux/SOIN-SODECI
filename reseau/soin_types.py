"""Types de soins simplifiés pour le guide utilisateur."""

from django.db.models import Q

SOIN_TYPES = [
    {
        'id': 'pharmacie',
        'label': 'Pharmacie',
        'hint': 'Médicaments & conseils',
        'keywords': ['PHARMACIE'],
    },
    {
        'id': 'hopital',
        'label': 'Hôpital / Clinique',
        'hint': 'Hospitalisation & urgences',
        'keywords': ['HOPITAL', 'CLINIQUE', 'POLYCLINIQUE', 'INFIRMERIE'],
    },
    {
        'id': 'cabinet',
        'label': 'Cabinet / Centre médical',
        'hint': 'Consultation générale',
        'keywords': [
            'CABINET',
            'CENTRE MEDICAL',
            'CENTRE CABINET',
            'ESPACE MEDICAL',
            'MEDECIN',
            'CENTRE MUTUALISTE',
        ],
    },
    {
        'id': 'dentaire',
        'label': 'Dentaire',
        'hint': 'Soins des dents',
        'keywords': ['DENTAIRE'],
    },
    {
        'id': 'optique',
        'label': 'Optique',
        'hint': 'Lunettes & vue',
        'keywords': ['OPTIQUE', 'OPHTALMO'],
    },
    {
        'id': 'labo',
        'label': 'Labo / Imagerie',
        'hint': 'Analyses & radio',
        'keywords': ['LABORATOIRE', 'IMAGERIE'],
    },
    {
        'id': 'specialiste',
        'label': 'Spécialiste',
        'hint': 'Cardio, gynéco, kiné…',
        'keywords': [
            'CARDIO',
            'GYNECO',
            'NEURO',
            'ORTHOPEDIE',
            'KINE',
            'KINESITHERAPIE',
        ],
    },
]


def get_soin_type(type_id: str) -> dict | None:
    for item in SOIN_TYPES:
        if item['id'] == type_id:
            return item
    return None


def nature_q_for_type(type_id: str) -> Q | None:
    item = get_soin_type(type_id)
    if not item:
        return None
    q = Q()
    for kw in item['keywords']:
        q |= Q(nature__icontains=kw)
    return q


def short_direction(name: str) -> str:
    return (
        (name or '')
        .replace('DIRECTION REGIONALE ', '')
        .replace('DIRECTION RÉGIONALE ', '')
        .strip()
        .title()
    )
