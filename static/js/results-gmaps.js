/**
 * Carte Google Maps native (même rendu que maps.google.com).
 */
(function () {
  const sheet = document.getElementById('sheet');
  const mapEl = document.getElementById('map');
  if (!sheet || !mapEl) return;

  const api = sheet.dataset.api;
  const routeApi = sheet.dataset.routeApi;
  let serverRouteLine = null;
  const listEl = document.getElementById('results-list');
  const statusEl = document.getElementById('sheet-status');
  const titleEl = document.getElementById('sheet-title');
  const handle = document.getElementById('sheet-handle');
  const zoneFilter = document.getElementById('zone-filter');
  const zoneSuggest = document.getElementById('zone-suggest');
  const btnClearZone = document.getElementById('btn-clear-zone');
  const browsePanel = document.getElementById('browse-panel');
  const selectedPanel = document.getElementById('selected-panel');
  const btnBack = document.getElementById('btn-back-list');
  const selectedName = document.getElementById('selected-name');
  const selectedMeta = document.getElementById('selected-meta');
  const selectedDistance = document.getElementById('selected-distance');
  const selectedActions = document.getElementById('selected-actions');
  const carLabel = document.getElementById('car-label');
  const footLabel = document.getElementById('foot-label');
  const btnLocate = document.getElementById('btn-locate');
  const geoPrompt = document.getElementById('geo-prompt');
  const geoPromptAllow = document.getElementById('geo-prompt-allow');
  const geoPromptLater = document.getElementById('geo-prompt-later');
  const geoPromptText = document.getElementById('geo-prompt-text');
  const fiche = document.getElementById('fiche');
  const ficheBody = document.getElementById('fiche-body');
  const ficheMini = document.getElementById('fiche-mini-map');
  const ficheClose = document.getElementById('fiche-close');
  const ficheBackdrop = document.getElementById('fiche-backdrop');

  let currentType = 'tous';
  let currentZone = '';
  let items = [];
  let selected = null;
  let travelMode = 'car';
  let userLat = null;
  let userLng = null;
  let userAccuracy = null;
  let bestAccuracy = Infinity;
  let map;
  let trafficLayer;
  let directionsService;
  let directionsRenderer;
  let userMarker;
  let userAccuracyCircle;
  let destMarker;
  let markers = [];
  let miniMap;
  let watchId = null;
  let followUser = true;
  let lastReloadAt = 0;
  let waitingAccurateFix = false;
  let zones = [];
  const MAX_ACCEPT_ACCURACY_M = 80;
  const GOOD_ACCURACY_M = 40;

  const TYPE_EMOJI = {
    pharmacie: '💊',
    hopital: '🏥',
    centre: '🩺',
    dentaire: '🦷',
    optique: '👓',
    labo: '🔬',
    specialiste: '👨‍⚕️',
  };

  try {
    var zonesNode = document.getElementById('zones-data');
    zones = zonesNode ? JSON.parse(zonesNode.textContent || '[]') : [];
  } catch (e) {
    zones = [];
  }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function telHref(t) {
    return 'tel:' + String(t || '').replace(/[\s/.]/g, '');
  }
  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }
  function formatDistanceKm(km) {
    if (km == null || isNaN(km)) return '';
    if (km < 1) return Math.round(km * 1000) + ' m';
    return (
      km.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) +
      ' km'
    );
  }
  function providerLabel(mode) {
    if (mode === 'google') return 'Google Maps';
    if (mode === 'driving') return 'itinéraire routier';
    if (mode === 'air') return 'vol d’oiseau';
    return '';
  }
  function updateTitle() {
    if (!titleEl) return;
    if (currentZone) titleEl.textContent = currentZone;
    else if (userLat != null) titleEl.textContent = 'À proximité';
    else titleEl.textContent = 'Réseau de soin';
    if (btnClearZone) btnClearZone.hidden = !currentZone;
  }
  function emojiFor(p) {
    return (p && (p.type_icon || TYPE_EMOJI[p.type])) || '📍';
  }
  function setSelectedDistance(text, loading) {
    if (!selectedDistance) return;
    selectedDistance.textContent = text || '';
    selectedDistance.classList.toggle('is-loading', !!loading);
  }
  function ll(lat, lng) {
    return new google.maps.LatLng(lat, lng);
  }
  function sheetPad() {
    var h = sheet ? sheet.getBoundingClientRect().height : 280;
    return { top: 72, right: 28, bottom: Math.max(160, h + 24), left: 28 };
  }

  function pinIcon(emoji, big) {
    var size = big ? 44 : 36;
    return {
      url:
        'data:image/svg+xml;charset=UTF-8,' +
        encodeURIComponent(
          '<svg xmlns="http://www.w3.org/2000/svg" width="' +
            size +
            '" height="' +
            size +
            '">' +
            '<circle cx="' +
            size / 2 +
            '" cy="' +
            size / 2 +
            '" r="' +
            (size / 2 - 2) +
            '" fill="#fff" stroke="' +
            (big ? '#ea4335' : '#0e6b8a') +
            '" stroke-width="3"/>' +
            '<text x="50%" y="54%" text-anchor="middle" font-size="' +
            (big ? 20 : 16) +
            '" dominant-baseline="middle">' +
            emoji +
            '</text></svg>'
        ),
      scaledSize: new google.maps.Size(size, size),
      anchor: new google.maps.Point(size / 2, size / 2),
    };
  }

  function clearMarkers() {
    markers.forEach(function (m) {
      m.setMap(null);
    });
    markers = [];
  }

  function clearRoute() {
    if (directionsRenderer) directionsRenderer.set('directions', null);
    if (serverRouteLine) {
      serverRouteLine.setMap(null);
      serverRouteLine = null;
    }
    if (destMarker) {
      destMarker.setMap(null);
      destMarker = null;
    }
  }

  function setUserMarker() {
    if (userLat == null || !map) return;
    var pos = ll(userLat, userLng);
    if (userMarker) {
      userMarker.setPosition(pos);
    } else {
      userMarker = new google.maps.Marker({
        map: map,
        position: pos,
        title: 'Vous êtes ici',
        zIndex: 999,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 8,
          fillColor: '#1a73e8',
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 3,
        },
      });
    }
    var radius = Math.max(12, Math.min(userAccuracy || 40, 120));
    if (userAccuracyCircle) {
      userAccuracyCircle.setCenter(pos);
      userAccuracyCircle.setRadius(radius);
    } else {
      userAccuracyCircle = new google.maps.Circle({
        map: map,
        center: pos,
        radius: radius,
        strokeColor: '#1a73e8',
        strokeOpacity: 0.35,
        strokeWeight: 1,
        fillColor: '#1a73e8',
        fillOpacity: 0.12,
        clickable: false,
      });
    }
  }

  function metersBetween(lat1, lng1, lat2, lng2) {
    var dlat = (lat2 - lat1) * 111320;
    var dlng = (lng2 - lng1) * 111320 * Math.cos((lat1 * Math.PI) / 180);
    return Math.sqrt(dlat * dlat + dlng * dlng);
  }

  function onUserMoved(lat, lng, accuracy) {
    var acc = typeof accuracy === 'number' && accuracy > 0 ? accuracy : 999;
    if (userLat != null && acc > bestAccuracy + 40 && acc > GOOD_ACCURACY_M) return false;
    var prevLat = userLat;
    var prevLng = userLng;
    var improved = acc < bestAccuracy - 5 || userLat == null;
    userLat = lat;
    userLng = lng;
    userAccuracy = acc;
    if (acc < bestAccuracy) bestAccuracy = acc;
    try {
      sessionStorage.setItem('sodeci_lat', String(userLat));
      sessionStorage.setItem('sodeci_lng', String(userLng));
      sessionStorage.setItem('sodeci_acc', String(acc));
    } catch (e) {}
    setUserMarker();
    if (followUser && map && !selected) {
      map.panTo(ll(userLat, userLng));
    }
    var movedFar = prevLat != null && metersBetween(prevLat, prevLng, lat, lng) > 50;
    var now = Date.now();
    if (waitingAccurateFix && (acc <= GOOD_ACCURACY_M || now - lastReloadAt > 8000)) {
      waitingAccurateFix = false;
      lastReloadAt = now;
      load();
    } else if (!selected && (improved || movedFar || now - lastReloadAt > 30000)) {
      lastReloadAt = now;
      load();
    }
    if (selected && selected.lat != null && (movedFar || improved)) {
      drawGoogleRoute(selected);
    }
    return true;
  }

  function startWatch() {
    if (!navigator.geolocation) return;
    if (watchId != null) navigator.geolocation.clearWatch(watchId);
    watchId = navigator.geolocation.watchPosition(
      function (pos) {
        onUserMoved(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy);
      },
      function () {},
      { enableHighAccuracy: true, maximumAge: 0, timeout: 25000 }
    );
  }

  function renderMarkers(list) {
    clearMarkers();
    if (selected) {
      setUserMarker();
      return;
    }
    var bounds = new google.maps.LatLngBounds();
    var n = 0;
    list.slice(0, 40).forEach(function (p) {
      if (p.lat == null || p.lng == null) return;
      var marker = new google.maps.Marker({
        map: map,
        position: ll(p.lat, p.lng),
        title: p.nom,
        icon: pinIcon(emojiFor(p), false),
      });
      marker.addListener('click', function () {
        enterSelection(p);
      });
      markers.push(marker);
      bounds.extend(ll(p.lat, p.lng));
      n += 1;
    });
    setUserMarker();
    if (userLat != null) bounds.extend(ll(userLat, userLng));
    if (n && followUser) {
      map.fitBounds(bounds, sheetPad());
    }
  }

  function formatRouteLabel(result) {
    if (!result || !result.routes || !result.routes[0]) return '';
    var leg = result.routes[0].legs[0];
    var dist = leg.distance ? leg.distance.text : '';
    var dur = leg.duration_in_traffic
      ? leg.duration_in_traffic.text
      : leg.duration
        ? leg.duration.text
        : '';
    return dist + (dur ? ' · ' + dur : '');
  }

  function drawGoogleRoute(p) {
    if (!map || userLat == null || p.lat == null) return;
    clearMarkers();
    setUserMarker();
    if (destMarker) destMarker.setMap(null);
    destMarker = new google.maps.Marker({
      map: map,
      position: ll(p.lat, p.lng),
      title: p.nom,
      icon: pinIcon(emojiFor(p), true),
      zIndex: 800,
    });

    var mode =
      travelMode === 'foot'
        ? google.maps.TravelMode.WALKING
        : google.maps.TravelMode.DRIVING;
    var req = {
      origin: ll(userLat, userLng),
      destination: ll(p.lat, p.lng),
      travelMode: mode,
      unitSystem: google.maps.UnitSystem.METRIC,
      region: 'ci',
      provideRouteAlternatives: false,
    };
    if (mode === google.maps.TravelMode.DRIVING) {
      req.drivingOptions = {
        departureTime: new Date(),
        trafficModel: 'bestguess',
      };
    }

    setSelectedDistance('Calcul Google Maps…', true);
    directionsService.route(req, function (result, status) {
      if (!selected || selected.id !== p.id) return;
      if (status !== 'OK' || !result) {
        drawServerRoute(p);
        return;
      }
      directionsRenderer.setDirections(result);
      var label = formatRouteLabel(result);
      var leg = result.routes[0].legs[0];
      var distText = leg.distance ? leg.distance.text : '';
      var durMin = Math.max(
        1,
        Math.round(
          ((leg.duration_in_traffic || leg.duration || {}).value || 60) / 60
        )
      );
      var summary =
        distText +
        ' · ~' +
        durMin +
        ' min · ' +
        (travelMode === 'foot' ? 'à pied' : 'en voiture');
      setSelectedDistance(summary, false);
      if (travelMode === 'car' && carLabel) {
        carLabel.textContent = distText + ' · ' + durMin + ' min';
      }
      if (travelMode === 'foot' && footLabel) {
        footLabel.textContent = distText + ' · ' + durMin + ' min';
      }
      // Charger l’autre mode pour le chip
      prefetchOtherMode(p);
      map.fitBounds(result.routes[0].bounds, sheetPad());
    });
  }

  /** Itinéraire calculé par le serveur (Routes API) si le service JS est refusé. */
  function drawServerRoute(p) {
    if (!routeApi) {
      setSelectedDistance('Impossible de calculer l’itinéraire.', true);
      return;
    }
    var params = new URLSearchParams({
      lat: String(userLat),
      lng: String(userLng),
      dest_lat: String(p.lat),
      dest_lng: String(p.lng),
      mode: travelMode,
    });
    fetch(routeApi + '?' + params.toString(), {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
      .then(function (r) {
        if (!r.ok) throw new Error('http');
        return r.json();
      })
      .then(function (data) {
        if (!selected || selected.id !== p.id) return;
        var path = (data.coordinates || []).map(function (c) {
          return ll(c[0], c[1]);
        });
        if (serverRouteLine) serverRouteLine.setMap(null);
        serverRouteLine = new google.maps.Polyline({
          map: map,
          path: path,
          strokeColor: travelMode === 'foot' ? '#5f6368' : '#1a73e8',
          strokeOpacity: 0.95,
          strokeWeight: 6,
        });
        var bounds = new google.maps.LatLngBounds();
        path.forEach(function (pt) {
          bounds.extend(pt);
        });
        if (path.length) map.fitBounds(bounds, sheetPad());
        setSelectedDistance(
          (data.distance_label || '—') +
            ' · ~' +
            (data.duration_min || 1) +
            ' min · ' +
            (travelMode === 'foot' ? 'à pied' : 'en voiture'),
          false
        );
        if (data.car && carLabel) {
          carLabel.textContent = data.car.distance_label + ' · ' + data.car.duration_min + ' min';
        }
        if (data.foot && footLabel) {
          footLabel.textContent =
            data.foot.distance_label + ' · ' + data.foot.duration_min + ' min';
        }
      })
      .catch(function () {
        setSelectedDistance('Impossible de calculer l’itinéraire.', true);
        map.panTo(ll(p.lat, p.lng));
        map.setZoom(15);
      });
  }

  function prefetchOtherMode(p) {
    var other = travelMode === 'car' ? 'foot' : 'car';
    var mode =
      other === 'foot'
        ? google.maps.TravelMode.WALKING
        : google.maps.TravelMode.DRIVING;
    directionsService.route(
      {
        origin: ll(userLat, userLng),
        destination: ll(p.lat, p.lng),
        travelMode: mode,
        unitSystem: google.maps.UnitSystem.METRIC,
        region: 'ci',
      },
      function (result, status) {
        if (status !== 'OK' || !result) return;
        var leg = result.routes[0].legs[0];
        var distText = leg.distance ? leg.distance.text : '—';
        var durMin = Math.max(1, Math.round((leg.duration.value || 60) / 60));
        if (other === 'car' && carLabel) carLabel.textContent = distText + ' · ' + durMin + ' min';
        if (other === 'foot' && footLabel)
          footLabel.textContent = distText + ' · ' + durMin + ' min';
      }
    );
  }

  function enterSelection(p) {
    selected = p;
    travelMode = 'car';
    document.body.classList.add('is-selecting');
    if (browsePanel) browsePanel.hidden = true;
    if (selectedPanel) selectedPanel.hidden = false;
    sheet.dataset.height = 'mid';
    followUser = true;
    clearMarkers();
    clearRoute();
    document.querySelectorAll('.travel-chip').forEach(function (c) {
      c.classList.toggle('active', c.dataset.mode === 'car');
    });
    if (carLabel) carLabel.textContent = '…';
    if (footLabel) footLabel.textContent = '…';
    if (selectedName) selectedName.textContent = p.nom;
    if (selectedMeta) {
      selectedMeta.textContent =
        (p.zone || p.commune || '') + (p.adresse ? ' · ' + p.adresse : '');
    }
    if (p.distance_label) {
      setSelectedDistance(p.distance_label + ' · en voiture (calcul…)', true);
    } else setSelectedDistance('Calcul Google Maps…', true);
    if (selectedActions) {
      selectedActions.innerHTML =
        (p.telephone
          ? '<a class="btn btn-primary" href="' + telHref(p.telephone) + '">📞 Appeler</a>'
          : '') +
        '<button type="button" class="btn btn-secondary" id="btn-open-fiche">Fiche</button>';
      var bf = document.getElementById('btn-open-fiche');
      if (bf)
        bf.addEventListener('click', function () {
          openFiche(p);
        });
    }
    renderList([p]);
    if (userLat == null) {
      setSelectedDistance('Activez la position pour l’itinéraire.', true);
      map.panTo(ll(p.lat, p.lng));
      map.setZoom(15);
      return;
    }
    drawGoogleRoute(p);
  }

  function exitSelection() {
    selected = null;
    travelMode = 'car';
    document.body.classList.remove('is-selecting');
    if (browsePanel) browsePanel.hidden = false;
    if (selectedPanel) selectedPanel.hidden = true;
    clearRoute();
    document.querySelectorAll('.travel-chip').forEach(function (c) {
      c.classList.toggle('active', c.dataset.mode === 'car');
    });
    sheet.dataset.height = 'mid';
    renderList(items);
    renderMarkers(items);
    updateTitle();
  }

  function renderList(list) {
    if (!list.length) {
      listEl.innerHTML =
        '<p class="empty">Aucun prestataire trouvé. Changez de filtre ou autorisez la position.</p>';
      return;
    }
    listEl.innerHTML = list
      .map(function (p, idx) {
        return (
          '<article class="p-card' +
          (selected && selected.id === p.id ? ' active' : '') +
          '" data-id="' +
          p.id +
          '" style="--i:' +
          Math.min(idx, 12) +
          '">' +
          '<div class="p-row"><div class="p-main"><div class="p-line1">' +
          '<span class="p-icon">' +
          escapeHtml(p.type_icon) +
          '</span><strong class="p-name">' +
          escapeHtml(p.nom) +
          '</strong></div><p class="p-meta">' +
          escapeHtml(p.zone || p.commune) +
          (p.adresse ? ' · ' + escapeHtml(p.adresse) : '') +
          '</p></div>' +
          (p.distance_label
            ? '<span class="p-dist">' + escapeHtml(p.distance_label) + '</span>'
            : '') +
          '</div>' +
          (selected
            ? ''
            : '<div class="p-actions">' +
              (p.telephone
                ? '<a class="btn btn-soft" href="' + telHref(p.telephone) + '">Appeler</a>'
                : '') +
              '<button type="button" class="btn btn-soft btn-route" data-id="' +
              p.id +
              '">Itinéraire</button>' +
              '<button type="button" class="btn btn-soft btn-fiche" data-id="' +
              p.id +
              '">Fiche</button></div>') +
          '</article>'
        );
      })
      .join('');
    if (!selected) {
      listEl.querySelectorAll('.p-card').forEach(function (card) {
        card.addEventListener('click', function (e) {
          if (e.target.closest('a') || e.target.closest('button')) return;
          var p = items.find(function (x) {
            return x.id === Number(card.dataset.id);
          });
          if (p) enterSelection(p);
        });
      });
      listEl.querySelectorAll('.btn-route').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          var p = items.find(function (x) {
            return x.id === Number(btn.dataset.id);
          });
          if (p) enterSelection(p);
        });
      });
      listEl.querySelectorAll('.btn-fiche').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          var p = items.find(function (x) {
            return x.id === Number(btn.dataset.id);
          });
          if (p) {
            enterSelection(p);
            openFiche(p);
          }
        });
      });
    }
  }

  function openFiche(p) {
    fiche.hidden = false;
    ficheBody.innerHTML =
      '<p class="badge">' +
      escapeHtml((p.type_icon || '') + ' ' + (p.type_label || '')) +
      '</p><h2 id="fiche-nom">' +
      escapeHtml(p.nom) +
      '</h2><dl class="fiche-dl"><div><dt>Zone</dt><dd>' +
      escapeHtml(p.zone) +
      '</dd></div>' +
      (p.adresse ? '<div><dt>Adresse</dt><dd>' + escapeHtml(p.adresse) + '</dd></div>' : '') +
      (p.telephone
        ? '<div><dt>Téléphone</dt><dd><a href="' +
          telHref(p.telephone) +
          '">' +
          escapeHtml(p.telephone) +
          '</a></dd></div>'
        : '') +
      '</dl>';
    ficheMini.innerHTML = '';
    if (p.lat != null) {
      setTimeout(function () {
        miniMap = new google.maps.Map(ficheMini, {
          center: ll(p.lat, p.lng),
          zoom: 15,
          disableDefaultUI: true,
          mapTypeId: 'roadmap',
        });
        new google.maps.Marker({
          map: miniMap,
          position: ll(p.lat, p.lng),
          icon: pinIcon(emojiFor(p), true),
        });
      }, 40);
    }
  }

  function closeFiche() {
    fiche.hidden = true;
    miniMap = null;
    ficheMini.innerHTML = '';
  }

  function applyData(data) {
    items = data.results || [];
    var counts = data.counts || {};
    var total = data.total_zone || 0;
    document.querySelectorAll('[data-count-for]').forEach(function (el) {
      var key = el.getAttribute('data-count-for');
      el.textContent = key === 'tous' ? String(total) : String(counts[key] || 0);
    });
    if (data.sorted_by_distance) {
      var pl = providerLabel(data.distance_mode);
      setStatus(
        items.length +
          ' résultat' +
          (items.length > 1 ? 's' : '') +
          (pl ? ' · ' + pl : '') +
          ' · plus proche → plus loin'
      );
    } else setStatus('Activez la position pour trier par distance');
    updateTitle();
    if (!selected) {
      clearRoute();
      renderList(items);
      renderMarkers(items);
    }
    if (data.sorted_by_distance && data.distance_mode !== 'google') {
      refineDistancesWithGoogle();
    }
  }

  /** Recalcule les distances via Distance Matrix JS (= app Google Maps). */
  function refineDistancesWithGoogle() {
    if (
      userLat == null ||
      userLng == null ||
      !items.length ||
      typeof google === 'undefined' ||
      !google.maps ||
      !google.maps.DistanceMatrixService
    ) {
      return;
    }
    var targets = items.filter(function (p) {
      return p.lat != null && p.lng != null;
    });
    if (!targets.length) return;

    var service = new google.maps.DistanceMatrixService();
    var chunk = 25;
    var pending = Math.ceil(targets.length / chunk);
    var gotAny = false;

    function finishChunk() {
      pending -= 1;
      if (pending > 0) return;
      if (!gotAny) return;
      items.sort(function (a, b) {
        var da = a.distance_km != null ? a.distance_km : 1e9;
        var db = b.distance_km != null ? b.distance_km : 1e9;
        return da - db;
      });
      setStatus(
        items.length +
          ' résultat' +
          (items.length > 1 ? 's' : '') +
          ' · Google Maps · plus proche → plus loin'
      );
      if (!selected) {
        renderList(items);
        renderMarkers(items);
      }
    }

    for (var start = 0; start < targets.length; start += chunk) {
      (function (batch) {
        service.getDistanceMatrix(
          {
            origins: [ll(userLat, userLng)],
            destinations: batch.map(function (p) {
              return ll(p.lat, p.lng);
            }),
            travelMode: google.maps.TravelMode.DRIVING,
            unitSystem: google.maps.UnitSystem.METRIC,
            region: 'CI',
          },
          function (response, status) {
            if (status === 'OK' && response && response.rows && response.rows[0]) {
              var els = response.rows[0].elements || [];
              els.forEach(function (el, i) {
                if (!el || el.status !== 'OK' || !el.distance) return;
                var km = el.distance.value / 1000;
                batch[i].distance_km = Math.round(km * 100) / 100;
                batch[i].distance_label = formatDistanceKm(batch[i].distance_km);
                batch[i].distance_mode = 'google';
                if (el.duration) {
                  batch[i].duration_min = Math.max(1, Math.round(el.duration.value / 60));
                }
                gotAny = true;
              });
            }
            finishChunk();
          }
        );
      })(targets.slice(start, start + chunk));
    }
  }

  function load() {
    setStatus('Chargement…');
    var params = new URLSearchParams({ type: currentType, limit: '60' });
    if (currentZone) params.set('zone', currentZone);
    if (userLat != null && userLng != null) {
      params.set('lat', String(userLat));
      params.set('lng', String(userLng));
    }
    fetch(api + '?' + params.toString(), {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
      .then(function (r) {
        if (!r.ok) throw new Error('http');
        return r.json();
      })
      .then(applyData)
      .catch(function () {
        setStatus('Erreur de chargement. Réessayez.');
      });
  }

  function showGeoPrompt(message) {
    if (!geoPrompt) return;
    if (geoPromptText && message) geoPromptText.textContent = message;
    geoPrompt.hidden = false;
  }
  function hideGeoPrompt() {
    if (geoPrompt) geoPrompt.hidden = true;
  }
  function setLocateBtn(state) {
    if (!btnLocate) return;
    btnLocate.classList.toggle('is-active', state === 'on');
    btnLocate.classList.toggle('is-pending', state === 'pending');
  }
  function isMobileDevice() {
    return /iPhone|iPad|iPod|Android/i.test(navigator.userAgent || '');
  }
  function deniedLocationHelp() {
    if (isMobileDevice()) {
      return 'Localisation refusée. Autorisez la localisation pour ce site, puis cliquez « Activer ma position ».';
    }
    return 'Localisation refusée. Cliquez sur le cadenas 🔒 à gauche de l’URL → Localisation → Autoriser, puis « Activer ma position ».';
  }

  function locate(opts) {
    opts = opts || {};
    if (!navigator.geolocation) {
      showGeoPrompt('Géolocalisation indisponible.');
      load();
      return;
    }
    hideGeoPrompt();
    setStatus('GPS haute précision…');
    setLocateBtn('pending');
    followUser = true;
    waitingAccurateFix = true;
    bestAccuracy = Infinity;
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        hideGeoPrompt();
        setLocateBtn('on');
        onUserMoved(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy);
        if (!opts.keepZone) {
          currentZone = '';
          if (zoneFilter) zoneFilter.value = '';
        }
        lastReloadAt = Date.now();
        setStatus('Position ±' + Math.round(pos.coords.accuracy) + ' m · Google Maps…');
        load();
        startWatch();
      },
      function () {
        setLocateBtn('off');
        showGeoPrompt(deniedLocationHelp());
        load();
      },
      { enableHighAccuracy: true, timeout: 30000, maximumAge: 0 }
    );
  }

  function restoreCachedPosition() {
    try {
      var la = parseFloat(sessionStorage.getItem('sodeci_lat'));
      var ln = parseFloat(sessionStorage.getItem('sodeci_lng'));
      var acc = parseFloat(sessionStorage.getItem('sodeci_acc'));
      if (!isNaN(la) && !isNaN(ln)) {
        userLat = la;
        userLng = ln;
        userAccuracy = !isNaN(acc) ? acc : 80;
        bestAccuracy = userAccuracy;
        setUserMarker();
        setLocateBtn('on');
        return true;
      }
    } catch (e) {}
    return false;
  }

  function bootLocation() {
    if (restoreCachedPosition()) {
      setStatus('Recalibrage GPS…');
      load();
    }
    locate({ keepZone: true, fromUser: true });
  }

  function showSuggest(q) {
    if (!zoneSuggest) return;
    var query = (q || '').trim().toLowerCase();
    if (!query) {
      zoneSuggest.hidden = true;
      zoneSuggest.innerHTML = '';
      return;
    }
    var matches = zones
      .filter(function (z) {
        return String(z.zone).toLowerCase().indexOf(query) !== -1;
      })
      .slice(0, 8);
    zoneSuggest.hidden = false;
    if (!matches.length) {
      zoneSuggest.innerHTML = '<p class="suggest-empty">Zone introuvable.</p>';
      return;
    }
    zoneSuggest.innerHTML = matches
      .map(function (z) {
        return (
          '<button type="button" class="suggest-row" data-zone="' +
          escapeHtml(z.zone).replace(/"/g, '&quot;') +
          '"><span>' +
          escapeHtml(z.zone) +
          '</span><span class="zone-count">' +
          z.total +
          '</span></button>'
        );
      })
      .join('');
    zoneSuggest.querySelectorAll('.suggest-row').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (selected) exitSelection();
        currentZone = btn.dataset.zone;
        if (zoneFilter) zoneFilter.value = currentZone;
        zoneSuggest.hidden = true;
        load();
      });
    });
  }

  window.initSoinGoogleMap = function () {
    map = new google.maps.Map(mapEl, {
      center: { lat: 5.36, lng: -4.01 },
      zoom: 13,
      mapTypeId: 'roadmap',
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: false,
      zoomControl: true,
      zoomControlOptions: { position: google.maps.ControlPosition.RIGHT_BOTTOM },
      clickableIcons: false,
      gestureHandling: 'greedy',
    });
    trafficLayer = new google.maps.TrafficLayer();
    trafficLayer.setMap(map);
    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer({
      map: map,
      suppressMarkers: true,
      polylineOptions: {
        strokeColor: '#1a73e8',
        strokeOpacity: 0.95,
        strokeWeight: 6,
      },
    });

    map.addListener('dragstart', function () {
      followUser = false;
    });

    if (ficheClose) ficheClose.addEventListener('click', closeFiche);
    if (ficheBackdrop) ficheBackdrop.addEventListener('click', closeFiche);
    if (btnBack) btnBack.addEventListener('click', exitSelection);
    document.querySelectorAll('.travel-chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        travelMode = chip.dataset.mode;
        document.querySelectorAll('.travel-chip').forEach(function (c) {
          c.classList.toggle('active', c === chip);
        });
        if (selected) drawGoogleRoute(selected);
      });
    });
    document.querySelectorAll('.type-chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        if (selected) exitSelection();
        document.querySelectorAll('.type-chip').forEach(function (c) {
          c.classList.remove('active');
        });
        chip.classList.add('active');
        currentType = chip.dataset.type;
        load();
      });
    });
    if (zoneFilter) zoneFilter.addEventListener('input', function () {
      showSuggest(zoneFilter.value);
    });
    if (btnClearZone) {
      btnClearZone.addEventListener('click', function () {
        if (selected) exitSelection();
        currentZone = '';
        if (zoneFilter) zoneFilter.value = '';
        locate({ fromUser: true });
      });
    }
    if (btnLocate) {
      btnLocate.addEventListener('click', function () {
        locate({ fromUser: true });
      });
    }
    if (geoPromptAllow) {
      geoPromptAllow.addEventListener('click', function () {
        locate({ fromUser: true });
      });
    }
    if (geoPromptLater) geoPromptLater.addEventListener('click', hideGeoPrompt);

    var heights = ['peek', 'mid', 'full'];
    if (handle) {
      handle.addEventListener('click', function () {
        var cur = sheet.dataset.height || 'mid';
        sheet.dataset.height = heights[(heights.indexOf(cur) + 1) % heights.length];
        setTimeout(function () {
          google.maps.event.trigger(map, 'resize');
        }, 280);
      });
    }

    updateTitle();
    bootLocation();
  };
})();
