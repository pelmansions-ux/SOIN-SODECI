(function () {
  const el = document.getElementById('mini-map');
  if (!el || typeof L === 'undefined') return;

  const lat = parseFloat(el.dataset.lat);
  const lng = parseFloat(el.dataset.lng);
  const name = el.dataset.name || 'Prestataire';

  const map = L.map(el, { zoomControl: true, scrollWheelZoom: false }).setView([lat, lng], 15);
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Tuiles &copy; Esri',
  }).addTo(map);
  L.marker([lat, lng]).addTo(map).bindPopup(name);
  setTimeout(function () { map.invalidateSize(); }, 150);
})();
