(function () {
  const sheet = document.getElementById('sheet');
  const mapEl = document.getElementById('map');
  if (!sheet || !mapEl || typeof L === 'undefined') return;

  const api = sheet.dataset.api;
  const routeApi = sheet.dataset.routeApi || '/api/itineraire/';
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
  const fiche = document.getElementById('fiche');
  const ficheBody = document.getElementById('fiche-body');
  const ficheMini = document.getElementById('fiche-mini-map');
  const ficheClose = document.getElementById('fiche-close');
  const ficheBackdrop = document.getElementById('fiche-backdrop');

  let currentType = 'tous';
  let currentZone = '';
  let items = [];
  let selected = null;
  let routeData = null;
  let travelMode = 'car';
  let userLat = null;
  let userLng = null;
  let map, markersLayer, userMarker, miniMap, routeLayer, routeLabelMarker;
  const markerById = {};
  let zones = [];

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

  function updateTitle() {
    if (!titleEl) return;
    if (currentZone) titleEl.textContent = currentZone;
    else if (userLat != null) titleEl.textContent = 'À proximité';
    else titleEl.textContent = 'Réseau de soin';
    if (btnClearZone) btnClearZone.hidden = !currentZone;
  }

  function initMap() {
    map = L.map(mapEl, { zoomControl: false, attributionControl: false }).setView(
      [5.36, -4.01],
      12
    );
    L.control.zoom({ position: 'bottomright' }).addTo(map);
    // Fond type Google (clair, rues lisibles)
    L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
      { maxZoom: 19 }
    ).addTo(map);
    markersLayer = L.layerGroup().addTo(map);
    routeLayer = L.layerGroup().addTo(map);
    setTimeout(function () {
      map.invalidateSize();
    }, 200);
  }

  function setUserMarker() {
    if (userLat == null || !map) return;
    if (userMarker) map.removeLayer(userMarker);
    userMarker = L.circleMarker([userLat, userLng], {
      radius: 10,
      color: '#fff',
      fillColor: '#1a73e8',
      fillOpacity: 1,
      weight: 3,
      className: 'user-pulse',
    })
      .addTo(map)
      .bindPopup('Vous êtes ici');
  }

  function clearRoute() {
    if (routeLayer) routeLayer.clearLayers();
    routeLabelMarker = null;
  }

  function clearBrowseMarkers() {
    if (markersLayer) markersLayer.clearLayers();
    Object.keys(markerById).forEach(function (k) {
      delete markerById[k];
    });
  }

  function midPoint(coords) {
    if (!coords || !coords.length) return null;
    return coords[Math.floor(coords.length / 2)];
  }

  function sheetPad() {
    // Garde la route visible au-dessus du panneau bas
    var h = sheet ? sheet.getBoundingClientRect().height : 280;
    return {
      paddingTopLeft: [28, 72],
      paddingBottomRight: [28, Math.max(160, h + 24)],
    };
  }

  function frameRoute(line) {
    if (!map || !line) return;
    var bounds = line.getBounds();
    // Si trop proche (même point / < ~80 m), élargir pour voir les rues
    var ne = bounds.getNorthEast();
    var sw = bounds.getSouthWest();
    var span = Math.max(Math.abs(ne.lat - sw.lat), Math.abs(ne.lng - sw.lng));
    if (span < 0.0012) {
      var c = bounds.getCenter();
      bounds = L.latLngBounds(
        [c.lat - 0.0022, c.lng - 0.0022],
        [c.lat + 0.0022, c.lng + 0.0022]
      );
    }
    var pad = sheetPad();
    map.fitBounds(bounds, {
      paddingTopLeft: pad.paddingTopLeft,
      paddingBottomRight: pad.paddingBottomRight,
      maxZoom: 17,
      animate: true,
    });
    setTimeout(function () {
      map.invalidateSize();
      map.fitBounds(bounds, {
        paddingTopLeft: pad.paddingTopLeft,
        paddingBottomRight: pad.paddingBottomRight,
        maxZoom: 17,
      });
    }, 180);
  }

  function formatRouteSummary(route, mode) {
    if (!route || !route.distance_label) return '';
    var parts = [route.distance_label];
    if (route.duration_min) parts.push('~' + route.duration_min + ' min');
    parts.push(mode === 'foot' ? 'à pied' : 'en voiture');
    return parts.join(' · ');
  }

  function setSelectedDistance(text, loading) {
    if (!selectedDistance) return;
    selectedDistance.textContent = text || '';
    selectedDistance.classList.toggle('is-loading', !!loading);
  }

  function syncSelectionDistance(active) {
    if (!active) return;
    var isCar = travelMode !== 'foot';
    var summary = formatRouteSummary(active, isCar ? 'car' : 'foot');
    setSelectedDistance(summary, false);
    if (selected) {
      selected.distance_label = active.distance_label;
      selected.duration_min = active.duration_min || null;
      selected.distance_summary =
        active.distance_label +
        (active.duration_min ? ' · ~' + active.duration_min + ' min' : '');
    }
    var badge = listEl.querySelector('.p-dist');
    if (badge && selected && selected.distance_summary) {
      badge.textContent = selected.distance_summary;
    }
  }

  function drawActiveRoute() {
    if (!routeData || !selected) return;
    clearBrowseMarkers();
    clearRoute();

    var active =
      travelMode === 'foot' && routeData.foot
        ? routeData.foot
        : routeData.car || routeData.foot;
    if (!active || !active.coordinates) return;

    var isCar = travelMode !== 'foot';
    var color = isCar ? '#1a73e8' : '#34a853';

    // Ombre de route (effet Google)
    L.polyline(active.coordinates, {
      color: '#0b3b75',
      weight: 12,
      opacity: 0.28,
      lineCap: 'round',
      lineJoin: 'round',
    }).addTo(routeLayer);

    var line = L.polyline(active.coordinates, {
      color: color,
      weight: 7,
      opacity: 0.98,
      lineCap: 'round',
      lineJoin: 'round',
    }).addTo(routeLayer);

    setUserMarker();

    var destIcon = L.divIcon({
      className: 'dest-pin',
      html:
        '<div class="dest-pin-wrap"><div class="dest-pin-dot"></div><span class="dest-pin-label">Arrivée</span></div>',
      iconSize: [72, 44],
      iconAnchor: [14, 36],
    });
    L.marker([selected.lat, selected.lng], { icon: destIcon, zIndexOffset: 800 }).addTo(
      routeLayer
    );

    var mid = midPoint(active.coordinates);
    if (mid) {
      var label =
        (active.distance_label || '') +
        (active.duration_min ? ' · ' + active.duration_min + ' min' : '');
      routeLabelMarker = L.marker(mid, {
        interactive: false,
        zIndexOffset: 900,
        icon: L.divIcon({
          className: 'route-bubble-wrap',
          html:
            '<div class="route-bubble ' +
            (isCar ? 'is-car' : 'is-foot') +
            '">' +
            (isCar ? '🚗 ' : '🚶 ') +
            escapeHtml(label) +
            '</div>',
          iconSize: [160, 40],
          iconAnchor: [80, 20],
        }),
      }).addTo(routeLayer);
    }

    frameRoute(line);

    if (carLabel && routeData.car) {
      carLabel.textContent =
        routeData.car.distance_label +
        (routeData.car.duration_min ? ' · ' + routeData.car.duration_min + ' min' : '');
    } else if (carLabel) carLabel.textContent = '—';

    if (footLabel && routeData.foot) {
      footLabel.textContent =
        routeData.foot.distance_label +
        (routeData.foot.duration_min ? ' · ' + routeData.foot.duration_min + ' min' : '');
    } else if (footLabel) footLabel.textContent = '—';

    syncSelectionDistance(active);
  }

  function enterSelection(p) {
    selected = p;
    travelMode = 'car'; // défaut : voiture
    routeData = null;
    document.body.classList.add('is-selecting');
    if (browsePanel) browsePanel.hidden = true;
    if (selectedPanel) selectedPanel.hidden = false;
    sheet.dataset.height = 'mid';

    // Carte lisible : masquer tous les autres pins
    clearBrowseMarkers();
    clearRoute();
    if (p.lat != null) {
      map.setView([p.lat, p.lng], 16);
    }

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
    // Affiche déjà la distance liste en attendant l'itinéraire voiture
    if (p.distance_label) {
      setSelectedDistance(p.distance_label + ' · en voiture (calcul…)', true);
    } else {
      setSelectedDistance('Calcul de la distance…', true);
    }
    if (selectedActions) {
      selectedActions.innerHTML =
        (p.telephone
          ? '<a class="btn btn-primary" href="' + telHref(p.telephone) + '">📞 Appeler</a>'
          : '') +
        '<button type="button" class="btn btn-secondary" id="btn-open-fiche">Fiche</button>';
      var bf = document.getElementById('btn-open-fiche');
      if (bf) {
        bf.addEventListener('click', function () {
          openFiche(p);
        });
      }
    }

    renderList([p]);
    loadRoute(p);
  }

  function exitSelection() {
    selected = null;
    routeData = null;
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

  function loadRoute(p) {
    if (userLat == null || p.lat == null) {
      map.setView([p.lat, p.lng], 15);
      setSelectedDistance('Activez la position pour la distance.', true);
      return;
    }
    setSelectedDistance('Calcul de la distance…', true);
    var params = new URLSearchParams({
      lat: String(userLat),
      lng: String(userLng),
      dest_lat: String(p.lat),
      dest_lng: String(p.lng),
      mode: 'car', // toujours démarrer en voiture
    });
    fetch(routeApi + '?' + params.toString(), {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!selected || selected.id !== p.id) return; // sélection changée
        routeData = data;
        travelMode = 'car';
        if (!data.car && data.foot) travelMode = 'foot';
        document.querySelectorAll('.travel-chip').forEach(function (c) {
          c.classList.toggle('active', c.dataset.mode === travelMode);
        });
        drawActiveRoute();
      })
      .catch(function () {
        setSelectedDistance(
          p.distance_label
            ? p.distance_label + ' · distance approximative'
            : 'Impossible de calculer la distance.',
          true
        );
        map.setView([p.lat, p.lng], 15);
      });
  }

  function renderMarkers(list) {
    if (!map || !markersLayer) return;
    markersLayer.clearLayers();
    Object.keys(markerById).forEach(function (k) {
      delete markerById[k];
    });
    if (selected) return; // en sélection, la route gère l'affichage

    var bounds = [];
    list.slice(0, 30).forEach(function (p) {
      if (p.lat == null || p.lng == null) return;
      var m = L.marker([p.lat, p.lng]);
      m.bindPopup(
        '<strong>' +
          escapeHtml(p.nom) +
          '</strong><br>' +
          escapeHtml(p.type_label || '') +
          (p.distance_label ? '<br><strong>' + escapeHtml(p.distance_label) + '</strong>' : '')
      );
      m.on('click', function () {
        enterSelection(p);
      });
      markersLayer.addLayer(m);
      markerById[p.id] = m;
      bounds.push([p.lat, p.lng]);
    });
    setUserMarker();
    setTimeout(function () {
      map.invalidateSize();
      if (userLat != null && bounds.length) {
        var b = L.latLngBounds(bounds);
        b.extend([userLat, userLng]);
        map.fitBounds(b, { padding: [40, 40], maxZoom: 14 });
      }
    }, 100);
  }

  function renderList(list) {
    if (!list.length) {
      listEl.innerHTML =
        '<p class="empty">Aucun prestataire trouvé. Changez de filtre ou autorisez la position.</p>';
      return;
    }
    listEl.innerHTML = list
      .map(function (p) {
        return (
          '<article class="p-card' +
          (selected && selected.id === p.id ? ' active' : '') +
          '" data-id="' +
          p.id +
          '">' +
          '<div class="p-row">' +
          '<div class="p-main">' +
          '<div class="p-line1">' +
          '<span class="p-icon">' +
          escapeHtml(p.type_icon) +
          '</span>' +
          '<strong class="p-name">' +
          escapeHtml(p.nom) +
          '</strong>' +
          '</div>' +
          '<p class="p-meta">' +
          escapeHtml(p.zone || p.commune) +
          (p.adresse ? ' · ' + escapeHtml(p.adresse) : '') +
          '</p>' +
          '</div>' +
          (p.distance_summary || p.distance_label
            ? '<span class="p-dist">' +
              escapeHtml(p.distance_summary || p.distance_label) +
              '</span>'
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
      '</p>' +
      '<h2 id="fiche-nom">' +
      escapeHtml(p.nom) +
      '</h2>' +
      '<dl class="fiche-dl">' +
      '<div><dt>Zone</dt><dd>' +
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
    if (miniMap) {
      miniMap.remove();
      miniMap = null;
    }
    ficheMini.innerHTML = '';
    if (p.lat != null) {
      setTimeout(function () {
        miniMap = L.map(ficheMini, { zoomControl: false, attributionControl: false }).setView(
          [p.lat, p.lng],
          15
        );
        L.tileLayer(
          'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
          { maxZoom: 19 }
        ).addTo(miniMap);
        L.marker([p.lat, p.lng]).addTo(miniMap);
        setTimeout(function () {
          miniMap.invalidateSize();
        }, 80);
      }, 40);
    }
  }

  function closeFiche() {
    fiche.hidden = true;
    if (miniMap) {
      miniMap.remove();
      miniMap = null;
    }
  }

  if (ficheClose) ficheClose.addEventListener('click', closeFiche);
  if (ficheBackdrop) ficheBackdrop.addEventListener('click', closeFiche);
  if (btnBack) btnBack.addEventListener('click', exitSelection);

  document.querySelectorAll('.travel-chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      travelMode = chip.dataset.mode;
      document.querySelectorAll('.travel-chip').forEach(function (c) {
        c.classList.toggle('active', c === chip);
      });
      drawActiveRoute();
    });
  });

  function applyData(data) {
    items = data.results || [];
    var counts = data.counts || {};
    var total = data.total_zone || 0;
    document.querySelectorAll('[data-count-for]').forEach(function (el) {
      var key = el.getAttribute('data-count-for');
      el.textContent = key === 'tous' ? String(total) : String(counts[key] || 0);
    });
    if (data.sorted_by_distance) {
      setStatus(
        items.length +
          ' résultat' +
          (items.length > 1 ? 's' : '') +
          (data.distance_mode === 'driving' ? ' · distance voiture' : '') +
          ' · plus proche → plus loin'
      );
    } else setStatus('Activez la position pour trier par distance');
    updateTitle();
    if (!selected) {
      clearRoute();
      renderList(items);
      renderMarkers(items);
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

  function locate() {
    if (!navigator.geolocation) {
      setStatus('Géolocalisation indisponible.');
      load();
      return;
    }
    setStatus('Recherche de votre position…');
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        userLat = pos.coords.latitude;
        userLng = pos.coords.longitude;
        sessionStorage.setItem('sodeci_lat', String(userLat));
        sessionStorage.setItem('sodeci_lng', String(userLng));
        sessionStorage.setItem('sodeci_geo', '1');
        currentZone = '';
        if (zoneFilter) zoneFilter.value = '';
        if (zoneSuggest) zoneSuggest.hidden = true;
        load();
      },
      function () {
        setStatus('Position non partagée. Autorisez la localisation.');
        load();
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 20000 }
    );
  }

  document.querySelectorAll('.type-chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      if (selected) exitSelection();
      document.querySelectorAll('.type-chip').forEach(function (c) {
        c.classList.remove('active');
        c.setAttribute('aria-selected', 'false');
      });
      chip.classList.add('active');
      chip.setAttribute('aria-selected', 'true');
      currentType = chip.dataset.type;
      load();
    });
  });

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

  if (zoneFilter) {
    zoneFilter.addEventListener('input', function () {
      showSuggest(zoneFilter.value);
    });
  }
  if (btnClearZone) {
    btnClearZone.addEventListener('click', function () {
      if (selected) exitSelection();
      currentZone = '';
      if (zoneFilter) zoneFilter.value = '';
      if (zoneSuggest) zoneSuggest.hidden = true;
      locate();
    });
  }

  var heights = ['peek', 'mid', 'full'];
  function cycleHeight() {
    var cur = sheet.dataset.height || 'mid';
    sheet.dataset.height = heights[(heights.indexOf(cur) + 1) % heights.length];
    setTimeout(function () {
      if (map) map.invalidateSize();
    }, 280);
  }
  if (handle) {
    handle.addEventListener('click', cycleHeight);
    var startY = null;
    handle.addEventListener(
      'touchstart',
      function (e) {
        startY = e.touches[0].clientY;
      },
      { passive: true }
    );
    handle.addEventListener('touchend', function (e) {
      if (startY == null) return;
      var dy = e.changedTouches[0].clientY - startY;
      var idx = heights.indexOf(sheet.dataset.height || 'mid');
      if (dy < -40 && idx < heights.length - 1) sheet.dataset.height = heights[idx + 1];
      if (dy > 40 && idx > 0) sheet.dataset.height = heights[idx - 1];
      startY = null;
      setTimeout(function () {
        if (map) map.invalidateSize();
      }, 280);
    });
  }

  initMap();
  updateTitle();
  locate();
})();
