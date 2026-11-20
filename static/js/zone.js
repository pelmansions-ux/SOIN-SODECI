(function () {
  const input = document.getElementById('zone-input');
  const list = document.getElementById('zone-list');
  const empty = document.getElementById('zone-empty');
  const status = document.getElementById('zone-status');
  const btnGeo = document.getElementById('btn-geo-zone');
  if (!input || !list) return;

  let zones = [];
  try {
    zones = JSON.parse(document.getElementById('zones-data').textContent || '[]');
  } catch (e) {
    zones = [];
  }

  function go(zone) {
    window.location.href = '/resultats/?zone=' + encodeURIComponent(zone);
  }

  function render(filter) {
    const q = (filter || '').trim().toLowerCase();
    const matches = zones.filter(function (z) {
      return !q || String(z.zone).toLowerCase().indexOf(q) !== -1;
    });

    list.innerHTML = matches
      .map(function (z) {
        return (
          '<li><button type="button" class="zone-row" data-zone="' +
          escapeAttr(z.zone) +
          '" role="option"><span class="zone-name">' +
          escapeHtml(z.zone) +
          '</span><span class="zone-count">' +
          z.total +
          '</span></button></li>'
        );
      })
      .join('');

    empty.hidden = matches.length > 0;
    list.querySelectorAll('.zone-row').forEach(function (btn) {
      btn.addEventListener('click', function () {
        go(btn.dataset.zone);
      });
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }
  function escapeAttr(s) {
    return escapeHtml(s).replace(/"/g, '&quot;');
  }

  input.addEventListener('input', function () {
    render(input.value);
  });

  list.querySelectorAll('.zone-row').forEach(function (btn) {
    btn.addEventListener('click', function () {
      go(btn.dataset.zone);
    });
  });

  btnGeo.addEventListener('click', function () {
    if (!navigator.geolocation) {
      status.textContent = 'Géolocalisation indisponible sur cet appareil.';
      return;
    }
    status.textContent = 'Recherche de votre position…';
    btnGeo.disabled = true;

    navigator.geolocation.getCurrentPosition(
      function (pos) {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        // Trouver la zone la plus proche via centres approximatifs des zones listées
        // On envoie lat/lng en sessionStorage pour l'écran résultats
        sessionStorage.setItem('sodeci_lat', String(lat));
        sessionStorage.setItem('sodeci_lng', String(lng));
        sessionStorage.setItem('sodeci_geo', '1');

        // Heuristique : privilégier une zone Abidjan si position proche d'Abidjan
        let best = zones[0];
        // Sans coords par zone côté client, on ouvre YOPOUGON/COCODY selon longitude
        const prefer = lng < -4.04 ? 'YOPOUGON' : lng > -3.97 ? 'COCODY' : 'ABOBO';
        const found = zones.find(function (z) {
          return String(z.zone).toUpperCase().indexOf(prefer) !== -1;
        });
        best = found || zones[0];
        status.textContent = 'Position trouvée — ouverture de ' + best.zone + '…';
        setTimeout(function () {
          go(best.zone);
        }, 350);
      },
      function () {
        status.textContent =
          'Position non partagée. Pas de souci : choisissez votre quartier dans la liste.';
        btnGeo.disabled = false;
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  });
})();
