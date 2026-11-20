(function () {
  const mapEl = document.getElementById('map');
  if (!mapEl || typeof L === 'undefined') return;

  const markersUrl = mapEl.dataset.markersUrl;
  const focusId = mapEl.dataset.focus;
  let markersData = [];

  const markersNode = document.getElementById('markers-data');
  if (markersNode) {
    try {
      markersData = JSON.parse(markersNode.textContent || '[]');
    } catch (e) {
      markersData = [];
    }
  }

  const map = L.map(mapEl, { maxZoom: 20 }).setView([5.36, -4.01], 7);
  if (window.SoinMapTiles) window.SoinMapTiles.addBaseTiles(map);
  else {
    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
      { maxZoom: 20, subdomains: 'abcd' }
    ).addTo(map);
  }

  const cluster = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 50 });
  map.addLayer(cluster);

  let markerById = {};
  let nearMarker = null;
  let userMarker = null;

  function popupHtml(m) {
    return (
      '<div class="map-popup">' +
      '<strong>' + escapeHtml(m.nom) + '</strong>' +
      '<div class="muted">' + escapeHtml(m.nature) + ' · ' + escapeHtml(m.commune) + '</div>' +
      (m.telephone ? '<div>' + escapeHtml(m.telephone) + '</div>' : '') +
      '<a href="' + m.url + '">Voir la fiche</a>' +
      '</div>'
    );
  }

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderMarkers(list) {
    cluster.clearLayers();
    markerById = {};
    const bounds = [];

    list.forEach(function (m) {
      if (m.lat == null || m.lng == null) return;
      const marker = L.marker([m.lat, m.lng]);
      marker.bindPopup(popupHtml(m));
      markerById[m.id] = marker;
      cluster.addLayer(marker);
      bounds.push([m.lat, m.lng]);
    });

    document.getElementById('map-count').textContent = String(list.length);

    if (focusId && markerById[focusId]) {
      const m = markerById[focusId];
      map.setView(m.getLatLng(), 15);
      setTimeout(function () { m.openPopup(); }, 400);
    } else if (bounds.length) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
    }
  }

  renderMarkers(markersData);

  function currentParams() {
    const params = new URLSearchParams();
    const direction = document.getElementById('filter-direction').value;
    const nature = document.getElementById('filter-nature').value;
    const q = document.getElementById('filter-q').value.trim();
    if (direction) params.set('direction', direction);
    if (nature) params.set('nature', nature);
    if (q) params.set('q', q);
    return params;
  }

  let filterTimer = null;
  function refreshMarkers() {
    const params = currentParams();
    fetch(markersUrl + '?' + params.toString(), { headers: { Accept: 'application/json' } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        markersData = data.markers || [];
        renderMarkers(markersData);
      })
      .catch(function () {});
  }

  ['filter-direction', 'filter-nature'].forEach(function (id) {
    document.getElementById(id).addEventListener('change', refreshMarkers);
  });
  document.getElementById('filter-q').addEventListener('input', function () {
    clearTimeout(filterTimer);
    filterTimer = setTimeout(refreshMarkers, 300);
  });

  const btnNear = document.getElementById('btn-near');
  const statusEl = document.getElementById('geo-status');
  const nearList = document.getElementById('near-list');
  const apiNear = btnNear.dataset.api;

  function setStatus(msg) {
    statusEl.textContent = msg || '';
  }

  btnNear.addEventListener('click', function () {
    if (!navigator.geolocation) {
      setStatus('La géolocalisation n’est pas disponible sur cet appareil.');
      return;
    }
    setStatus('Localisation en cours…');
    btnNear.disabled = true;

    navigator.geolocation.getCurrentPosition(
      function (pos) {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        const params = currentParams();
        params.set('lat', lat);
        params.set('lng', lng);
        params.set('limit', '10');

        if (userMarker) map.removeLayer(userMarker);
        userMarker = L.circleMarker([lat, lng], {
          radius: 9,
          color: '#0b3d5c',
          fillColor: '#2ec4b6',
          fillOpacity: 0.95,
          weight: 2,
        }).addTo(map).bindPopup('Vous êtes ici');

        fetch(apiNear + '?' + params.toString(), { headers: { Accept: 'application/json' } })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            const results = data.results || [];
            if (!results.length) {
              setStatus('Aucun prestataire géolocalisé trouvé.');
              btnNear.disabled = false;
              return;
            }

            const nearest = results[0];
            setStatus('Le plus proche : ' + nearest.nom + ' (' + nearest.distance_km + ' km)');

            if (nearMarker) map.removeLayer(nearMarker);
            nearMarker = L.marker([nearest.lat, nearest.lng], {
              zIndexOffset: 1000,
            }).addTo(map);
            const icon = nearMarker.getElement && nearMarker.getElement();
            if (icon) icon.classList.add('nearest-pulse');

            nearMarker.bindPopup(
              popupHtml(nearest) +
              '<div><strong>' + nearest.distance_km + ' km</strong></div>'
            ).openPopup();

            map.setView([nearest.lat, nearest.lng], 13);

            nearList.hidden = false;
            nearList.innerHTML =
              '<h3>Les plus proches</h3>' +
              results
                .map(function (r, i) {
                  return (
                    '<button type="button" class="near-item" data-lat="' + r.lat + '" data-lng="' + r.lng + '" data-id="' + r.id + '">' +
                    '<span class="near-rank">' + (i + 1) + '</span>' +
                    '<span class="near-body"><strong>' + escapeHtml(r.nom) + '</strong>' +
                    '<small>' + escapeHtml(r.nature) + ' · ' + r.distance_km + ' km</small></span>' +
                    '</button>'
                  );
                })
                .join('');

            nearList.querySelectorAll('.near-item').forEach(function (btn) {
              btn.addEventListener('click', function () {
                map.setView([parseFloat(btn.dataset.lat), parseFloat(btn.dataset.lng)], 15);
                const m = markerById[btn.dataset.id];
                if (m) m.openPopup();
              });
            });

            btnNear.disabled = false;
          })
          .catch(function () {
            setStatus('Erreur lors de la recherche de proximité.');
            btnNear.disabled = false;
          });
      },
      function () {
        setStatus('Impossible d’obtenir votre position. Autorisez la localisation.');
        btnNear.disabled = false;
      },
      { enableHighAccuracy: true, timeout: 12000 }
    );
  });

  if (window.location.hash === '#pres-de-moi') {
    setTimeout(function () { btnNear.click(); }, 600);
  }
})();
