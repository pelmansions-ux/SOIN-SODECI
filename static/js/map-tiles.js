/**
 * Fond de carte détaillé sans clé API.
 * OSM France / HOT (rues, labels) → OSM → Esri en secours.
 * (Carto Voyager demande désormais une API key — ne plus l’utiliser.)
 */
(function (global) {
  function addBaseTiles(map) {
    if (!map || typeof L === 'undefined') return null;

    var layers = [
      {
        url: 'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
        options: {
          maxZoom: 20,
          subdomains: 'abc',
          attribution: '&copy; OpenStreetMap, HOT',
        },
      },
      {
        url: 'https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png',
        options: {
          maxZoom: 20,
          subdomains: 'abc',
          attribution: '&copy; OpenStreetMap France',
        },
      },
      {
        url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        options: {
          maxZoom: 19,
          attribution: '&copy; OpenStreetMap',
        },
      },
      {
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        options: { maxZoom: 19, attribution: 'Esri' },
      },
    ];

    function attach(i) {
      if (i >= layers.length) return null;
      var spec = layers[i];
      var next = L.tileLayer(spec.url, spec.options);
      var errors = 0;
      next.on('tileerror', function () {
        errors += 1;
        if (errors >= 4 && i + 1 < layers.length) {
          map.removeLayer(next);
          attach(i + 1);
        }
      });
      next.addTo(map);
      return next;
    }

    return attach(0);
  }

  global.SoinMapTiles = { addBaseTiles: addBaseTiles };
})(window);
