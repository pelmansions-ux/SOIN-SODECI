"""Catégories de soin normalisées (7 types)."""

from django.db.models import Q

TYPE_CHOICES = [
    ('pharmacie', 'Pharmacie'),
    ('hopital', 'Hôpital / Clinique'),
    ('centre', 'Centre médical'),
    ('dentaire', 'Dentaire'),
    ('optique', 'Optique'),
    ('labo', 'Labo / Imagerie'),
    ('specialiste', 'Spécialiste'),
]

TYPE_LABELS = dict(TYPE_CHOICES)

TYPE_ICONS = {
    'pharmacie': '💊',
    'hopital': '🏥',
    'centre': '🩺',
    'dentaire': '🦷',
    'optique': '👓',
    'labo': '🔬',
    'specialiste': '👨‍⚕️',
}

# Mots-clés Excel → type normalisé (ordre = priorité)
TYPE_KEYWORDS = [
    ('pharmacie', ['PHARMACIE']),
    ('dentaire', ['DENTAIRE']),
    ('optique', ['OPTIQUE', 'OPHTALMO']),
    ('labo', ['LABORATOIRE', 'IMAGERIE']),
    ('specialiste', [
        'CARDIO', 'GYNECO', 'NEURO', 'ORTHOPEDIE', 'KINE', 'KINESITHERAPIE',
    ]),
    ('hopital', ['HOPITAL', 'CLINIQUE', 'POLYCLINIQUE', 'INFIRMERIE']),
    ('centre', [
        'CABINET', 'CENTRE MEDICAL', 'CENTRE CABINET', 'ESPACE MEDICAL',
        'MEDECIN', 'CENTRE MUTUALISTE', 'CENTRE  MEDICAL',
    ]),
]


def normalize_type(nature: str) -> str:
    text = (nature or '').upper()
    for type_id, keywords in TYPE_KEYWORDS:
        for kw in keywords:
            if kw in text:
                return type_id
    return 'centre'


def type_filter_q(type_id: str) -> Q | None:
    if not type_id or type_id == 'tous':
        return None
    return Q(type_soin=type_id)
