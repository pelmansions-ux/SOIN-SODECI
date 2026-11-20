(function () {
  const el = document.getElementById('mini-map');
  if (!el || typeof L === 'undefined') return;

  const lat = parseFloat(el.dataset.lat);
  const lng = parseFloat(el.dataset.lng);
  const name = el.dataset.name || 'Prestataire';

  const map = L.map(el, { zoomControl: true, scrollWheelZoom: false, maxZoom: 20 }).setView(
    [lat, lng],
    16
  );
  if (window.SoinMapTiles) window.SoinMapTiles.addBaseTiles(map);
  else {
    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
      { maxZoom: 20, subdomains: 'abcd' }
    ).addTo(map);
  }
  L.marker([lat, lng]).addTo(map).bindPopup(name);
  setTimeout(function () { map.invalidateSize(); }, 150);
})();
