(function () {
  const wizard = document.getElementById('wizard');
  const explorer = document.getElementById('explorer');
  if (!wizard || !explorer) return;

  const stepZone = document.getElementById('step-zone');
  const stepType = document.getElementById('step-type');
  const dot1 = document.getElementById('dot-1');
  const dot2 = document.getElementById('dot-2');
  const zoneLabel = document.getElementById('zone-chosen-label');
  const apiUrl = explorer.dataset.api;
  const resultsList = document.getElementById('results-list');
  const explorerTitle = document.getElementById('explorer-title');
  const explorerMeta = document.getElementById('explorer-meta');
  const geoStatus = document.getElementById('geo-status');
  const liveQ = document.getElementById('live-q');
  const btnNear = document.getElementById('btn-near');
  const btnChange = document.getElementById('btn-change');
  const btnReset = document.getElementById('btn-reset-choices');
  const mapEl = document.getElementById('map');

  let state = {
    direction: '',
    directionLabel: '',
    type: '',
    typeLabel: '',
    q: '',
    lat: null,
    lng: null,
  };

  let map = null;
  let markersLayer = null;
  let userMarker = null;
  let searchTimer = null;

  function showStep(step) {
    stepZone.hidden = step !== 1;
    stepType.hidden = step !== 2;
    dot1.classList.toggle('active', step >= 1);
    dot2.classList.toggle('active', step >= 2);
  }

  function openWizard() {
    wizard.hidden = false;
    explorer.hidden = true;
    if (btnReset) btnReset.hidden = true;
    showStep(1);
    state.type = '';
    state.typeLabel = '';
    liveQ.value = '';
    state.q = '';
  }

  function openExplorer() {
    wizard.hidden = true;
    explorer.hidden = false;
    if (btnReset) btnReset.hidden = false;
    explorerTitle.textContent = state.typeLabel + ' · ' + state.directionLabel;
    ensureMap();
    locateThenSearch(true);
  }

  function ensureMap() {
    if (!mapEl || typeof L === 'undefined') {
      geoStatus.textContent = 'Impossible de charger la carte. Vérifiez votre connexion.';
      return;
    }
    if (map) {
      setTimeout(function () {
        map.invalidateSize();
      }, 80);
      return;
    }

    map = L.map(mapEl, { scrollWheelZoom: true }).setView([5.36, -4.01], 8);
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      attribution: 'Tuiles &copy; Esri',
    }).addTo(map);
    markersLayer = L.layerGroup().addTo(map);

    setTimeout(function () {
      map.invalidateSize();
    }, 120);
    setTimeout(function () {
      map.invalidateSize();
    }, 400);
  }

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderList(items) {
    if (!items.length) {
      resultsList.innerHTML = '<p class="empty">Aucun prestataire pour ce choix.</p>';
      return;
    }
    resultsList.innerHTML = items
      .map(function (p, i) {
        const dist =
          p.distance_km != null
            ? '<span class="dist">' + p.distance_km + ' km</span>'
            : '';
        const tel = p.telephone
          ? '<a class="chip" href="tel:' +
            escapeHtml(String(p.telephone).replace(/[\s/]/g, '')) +
            '">' +
            escapeHtml(p.telephone) +
            '</a>'
          : '';
        return (
          '<article class="result-card reveal" style="--i:' +
          i +
          '" data-id="' +
          p.id +
          '" data-lat="' +
          (p.lat || '') +
          '" data-lng="' +
          (p.lng || '') +
          '">' +
          '<div class="result-top">' +
          '<span class="badge">' +
          escapeHtml(p.nature) +
          '</span>' +
          dist +
          '</div>' +
          '<strong class="result-name">' +
          escapeHtml(p.nom) +
          '</strong>' +
          '<p class="muted">' +
          escapeHtml(p.commune) +
          (p.secteur ? ' · ' + escapeHtml(p.secteur) : '') +
          '</p>' +
          (p.adresse ? '<p class="addr">' + escapeHtml(p.adresse) + '</p>' : '') +
          '<div class="result-actions">' +
          tel +
          (p.maps_url
            ? '<a class="chip accent" href="' +
              escapeHtml(p.maps_url) +
              '" target="_blank" rel="noopener">Itinéraire</a>'
            : '') +
          '<a class="chip" href="' +
          escapeHtml(p.url) +
          '">Fiche</a>' +
          '</div></article>'
        );
      })
      .join('');

    resultsList.querySelectorAll('.result-card').forEach(function (card) {
      card.addEventListener('click', function (e) {
        if (e.target.closest('a')) return;
        const lat = parseFloat(card.dataset.lat);
        const lng = parseFloat(card.dataset.lng);
        if (!map || Number.isNaN(lat) || Number.isNaN(lng)) return;
        map.setView([lat, lng], 15);
      });
    });
  }

  function renderMarkers(markers) {
    if (!map || !markersLayer) return;
    markersLayer.clearLayers();
    const bounds = [];

    markers.forEach(function (m) {
      if (m.lat == null || m.lng == null) return;
      const marker = L.marker([m.lat, m.lng]);
      marker.bindPopup(
        '<strong>' +
          escapeHtml(m.nom) +
          '</strong><br><span class="muted">' +
          escapeHtml(m.nature) +
          ' · ' +
          escapeHtml(m.commune) +
          '</span>' +
          (m.distance_km != null ? '<br><strong>' + m.distance_km + ' km</strong>' : '') +
          (m.telephone ? '<br>' + escapeHtml(m.telephone) : '') +
          '<br><a href="' +
          escapeHtml(m.url) +
          '">Fiche</a>'
      );
      markersLayer.addLayer(marker);
      bounds.push([m.lat, m.lng]);
    });

    if (userMarker) {
      // keep user marker above
    }

    setTimeout(function () {
      map.invalidateSize();
      if (bounds.length === 1) {
        map.setView(bounds[0], 13);
      } else if (bounds.length > 1) {
        map.fitBounds(bounds, { padding: [36, 36], maxZoom: 13 });
      }
    }, 60);
  }

  function setUserOnMap(lat, lng) {
    if (!map) return;
    if (userMarker) map.removeLayer(userMarker);
    userMarker = L.circleMarker([lat, lng], {
      radius: 10,
      color: '#0b3d5c',
      fillColor: '#2ec4b6',
      fillOpacity: 0.95,
      weight: 2,
    })
      .addTo(map)
      .bindPopup('Vous êtes ici');
  }

  function search() {
    const params = new URLSearchParams();
    params.set('direction', state.direction);
    params.set('type', state.type);
    if (state.q) params.set('q', state.q);
    if (state.lat != null && state.lng != null) {
      params.set('lat', state.lat);
      params.set('lng', state.lng);
    }

    explorerMeta.textContent = 'Chargement…';
    fetch(apiUrl + '?' + params.toString(), { headers: { Accept: 'application/json' } })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        const results = data.results || [];
        const markers = data.markers || [];
        explorerMeta.textContent =
          data.count +
          ' prestataire' +
          (data.count > 1 ? 's' : '') +
          (state.lat != null ? ' · triés par distance' : '');
        renderList(results);
        renderMarkers(markers);
        if (state.lat != null) setUserOnMap(state.lat, state.lng);
      })
      .catch(function () {
        explorerMeta.textContent = 'Erreur de chargement';
        geoStatus.textContent = 'Impossible de charger les résultats.';
      });
  }

  function locateThenSearch(auto) {
    if (!navigator.geolocation) {
      geoStatus.textContent = auto
        ? 'Géolocalisation indisponible — résultats par zone.'
        : 'Géolocalisation indisponible sur cet appareil.';
      search();
      return;
    }

    geoStatus.textContent = 'Localisation en cours…';
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        state.lat = pos.coords.latitude;
        state.lng = pos.coords.longitude;
        geoStatus.textContent = 'Position trouvée — les plus proches en tête.';
        search();
      },
      function () {
        geoStatus.textContent = auto
          ? 'Position non autorisée — résultats de votre zone.'
          : 'Impossible d’obtenir votre position. Autorisez la localisation.';
        search();
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  stepZone.querySelectorAll('[data-direction]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      state.direction = btn.dataset.direction;
      state.directionLabel = btn.dataset.label;
      zoneLabel.textContent = 'Zone : ' + state.directionLabel;
      showStep(2);
      stepType.classList.add('reveal');
    });
  });

  stepType.querySelectorAll('[data-type]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      state.type = btn.dataset.type;
      state.typeLabel = btn.dataset.label;
      openExplorer();
    });
  });

  document.getElementById('back-to-zone').addEventListener('click', function () {
    showStep(1);
  });

  btnChange.addEventListener('click', openWizard);
  if (btnReset) btnReset.addEventListener('click', openWizard);

  btnNear.addEventListener('click', function () {
    locateThenSearch(false);
  });

  liveQ.addEventListener('input', function () {
    state.q = liveQ.value.trim();
    clearTimeout(searchTimer);
    searchTimer = setTimeout(search, 280);
  });

  showStep(1);
})();
