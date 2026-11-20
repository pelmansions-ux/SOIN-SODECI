/**
 * Fond de carte détaillé (style proche Google Maps) — sans clé API.
 * Carto Voyager = rues, labels, POI lisibles. Fallback OSM FR puis Esri.
 */
(function (global) {
  function addBaseTiles(map) {
    if (!map || typeof L === 'undefined') return null;

    var layers = [
      {
        url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
        options: {
          maxZoom: 20,
          subdomains: 'abcd',
          attribution: '&copy; OpenStreetMap &copy; CARTO',
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
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        options: { maxZoom: 19, attribution: 'Esri' },
      },
    ];

    var idx = 0;
    var layer = null;

    function attach(i) {
      if (i >= layers.length) return null;
      var spec = layers[i];
      var next = L.tileLayer(spec.url, spec.options);
      var errors = 0;
      next.on('tileerror', function () {
        errors += 1;
        if (errors >= 4 && i + 1 < layers.length) {
          map.removeLayer(next);
          layer = attach(i + 1);
        }
      });
      next.addTo(map);
      return next;
    }

    layer = attach(idx);
    return layer;
  }

  global.SoinMapTiles = { addBaseTiles: addBaseTiles };
})(window);
