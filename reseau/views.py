from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .geo import (
    driving_route,
    format_distance_km,
    haversine_km,
    road_distances_km,
    walking_route,
)
from .models import Prestataire
from .types_soin import TYPE_CHOICES, TYPE_ICONS, TYPE_LABELS


class SoinLoginView(LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True

    def form_invalid(self, form):
        form.add_error(
            None,
            'Identifiant ou mot de passe incorrect. Réessayez ou contactez votre RH.',
        )
        return super().form_invalid(form)


@login_required
def home(request):
    return redirect('results')


@login_required
def results(request):
    """Écran unique mobile-first : carte + panneau bas."""
    type_counts = {
        row['type_soin']: row['total']
        for row in Prestataire.objects.filter(actif=True).values('type_soin').annotate(total=Count('id'))
    }
    total = Prestataire.objects.filter(actif=True).count()

    chips = [{'id': 'tous', 'label': 'Tous', 'icon': '✨', 'count': total}]
    for type_id, label in TYPE_CHOICES:
        short = label.split('/')[0].strip() if '/' in label else label
        chips.append(
            {
                'id': type_id,
                'label': short,
                'icon': TYPE_ICONS.get(type_id, '📍'),
                'count': type_counts.get(type_id, 0),
            }
        )

    zones = list(
        Prestataire.objects.filter(actif=True)
        .exclude(zone='')
        .values('zone')
        .annotate(total=Count('id'))
        .order_by('zone')
    )

    return render(
        request,
        'reseau/results.html',
        {
            'chips': chips,
            'zones_json': zones,
            'type_labels': TYPE_LABELS,
        },
    )


@login_required
def zone_picker(request):
    return redirect('results')


@login_required
@require_GET
def api_prestataires(request):
    zone = request.GET.get('zone', '').strip()
    type_id = request.GET.get('type', 'tous').strip() or 'tous'
    q = request.GET.get('q', '').strip()
    limit = min(int(request.GET.get('limit', 80) or 80), 150)

    user_lat = user_lng = None
    try:
        if request.GET.get('lat') not in (None, '') and request.GET.get('lng') not in (None, ''):
            user_lat = float(request.GET.get('lat'))
            user_lng = float(request.GET.get('lng'))
    except (TypeError, ValueError):
        user_lat = user_lng = None

    qs = Prestataire.objects.filter(actif=True)
    if zone:
        qs = qs.filter(zone__iexact=zone)
    if type_id and type_id != 'tous':
        qs = qs.filter(type_soin=type_id)
    if q:
        qs = qs.filter(
            Q(nom__icontains=q)
            | Q(adresse__icontains=q)
            | Q(telephone__icontains=q)
            | Q(commune__icontains=q)
            | Q(secteur__icontains=q)
            | Q(zone__icontains=q)
        )

    # Pour le tri proximité, on a besoin de GPS
    if user_lat is not None:
        qs = qs.exclude(latitude__isnull=True).exclude(longitude__isnull=True)

    items = []
    for p in qs.iterator(chunk_size=200):
        data = p.to_dict()
        if user_lat is not None and p.latitude is not None and p.longitude is not None:
            # 1) Tri rapide à vol d'oiseau
            data['distance_air_km'] = round(
                haversine_km(user_lat, user_lng, p.latitude, p.longitude), 2
            )
        items.append(data)

    distance_mode = 'none'
    if user_lat is not None:
        items.sort(
            key=lambda x: (
                x.get('distance_air_km') is None,
                x['distance_air_km'] if x.get('distance_air_km') is not None else 10**9,
            )
        )
        # 2) Affiner les plus proches avec distance routière (comme Google Maps)
        candidates = [it for it in items if it.get('lat') is not None][: min(40, limit)]
        dests = [(it['lat'], it['lng']) for it in candidates]
        road = road_distances_km(user_lat, user_lng, dests)
        if any(d is not None for d in road):
            distance_mode = 'driving'
            for it, d in zip(candidates, road):
                air = it.get('distance_air_km')
                # Garde-fou : OSRM peut coller 2 points au même nœud (ex. 20 m)
                # alors que le vol d'oiseau est bien plus grand → on garde l'air.
                if d is None:
                    d = air
                    it['distance_mode'] = 'air'
                elif air is not None and air >= 0.25 and d < air * 0.35:
                    d = air
                    it['distance_mode'] = 'air'
                else:
                    it['distance_mode'] = 'driving'
                it['distance_km'] = d
                it['distance_label'] = format_distance_km(d)
            candidates.sort(
                key=lambda x: (
                    x.get('distance_km') is None,
                    x['distance_km'] if x.get('distance_km') is not None else 10**9,
                )
            )
            candidate_ids = {it['id'] for it in candidates}
            rest = [it for it in items if it['id'] not in candidate_ids]
            for it in rest:
                if it.get('distance_air_km') is not None and 'distance_km' not in it:
                    it['distance_km'] = it['distance_air_km']
                    it['distance_label'] = format_distance_km(it['distance_air_km'])
                    it['distance_mode'] = 'air'
            items = candidates + rest
        else:
            distance_mode = 'air'
            for it in items:
                if it.get('distance_air_km') is not None:
                    it['distance_km'] = it['distance_air_km']
                    it['distance_label'] = format_distance_km(it['distance_air_km'])
                    it['distance_mode'] = 'air'
    else:
        items.sort(key=lambda x: x.get('nom') or '')

    items = items[:limit]

    count_qs = Prestataire.objects.filter(actif=True)
    if zone:
        count_qs = count_qs.filter(zone__iexact=zone)
    counts = {
        row['type_soin']: row['total']
        for row in count_qs.values('type_soin').annotate(total=Count('id'))
    }
    total = count_qs.count()

    return JsonResponse(
        {
            'zone': zone,
            'type': type_id,
            'count': len(items),
            'total_zone': total,
            'counts': counts,
            'sorted_by_distance': user_lat is not None,
            'distance_mode': distance_mode,
            'origin': {'lat': user_lat, 'lng': user_lng} if user_lat is not None else None,
            'results': items,
        }
    )


@login_required
@require_GET
def api_zones(request):
    q = request.GET.get('q', '').strip()
    qs = (
        Prestataire.objects.filter(actif=True)
        .exclude(zone='')
        .values('zone')
        .annotate(total=Count('id'))
        .order_by('zone')
    )
    if q:
        qs = qs.filter(zone__icontains=q)
    return JsonResponse({'zones': list(qs)})


@login_required
@require_GET
def api_detail(request, pk: int):
    p = get_object_or_404(Prestataire, pk=pk, actif=True)
    return JsonResponse(p.to_dict())


@login_required
@require_GET
def api_itineraire(request):
    """Itinéraires voiture + pied à afficher sur la carte (sans quitter l'app)."""
    try:
        o_lat = float(request.GET.get('lat'))
        o_lng = float(request.GET.get('lng'))
        d_lat = float(request.GET.get('dest_lat'))
        d_lng = float(request.GET.get('dest_lng'))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Coordonnées invalides'}, status=400)

    preferred = (request.GET.get('mode') or 'car').strip().lower()
    if preferred not in ('car', 'foot'):
        preferred = 'car'

    car = driving_route(o_lat, o_lng, d_lat, d_lng)
    foot = walking_route(o_lat, o_lng, d_lat, d_lng)

    if not car and not foot:
        dist = haversine_km(o_lat, o_lng, d_lat, d_lng)
        fallback = {
            'mode': 'air',
            'distance_km': round(dist, 2),
            'distance_label': format_distance_km(dist),
            'duration_min': None,
            'coordinates': [[o_lat, o_lng], [d_lat, d_lng]],
        }
        return JsonResponse(
            {
                'ok': True,
                'active': 'air',
                'car': None,
                'foot': None,
                **fallback,
            }
        )

    active = preferred if (preferred == 'car' and car) or (preferred == 'foot' and foot) else (
        'car' if car else 'foot'
    )
    current = car if active == 'car' else foot
    return JsonResponse(
        {
            'ok': True,
            'active': active,
            'car': car,
            'foot': foot,
            **current,
        }
    )
