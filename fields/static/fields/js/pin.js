/* Field picker: click the map (needs internet for tiles) or type coordinates. */
(function () {
  "use strict";
  var latIn = document.getElementById("lat"), lonIn = document.getElementById("lon");
  var radIn = document.getElementById("radius"), radOut = document.getElementById("radius-out");
  var map = L.map("pickmap").setView([parseFloat(latIn.value), parseFloat(lonIn.value)], 12);
  // Satellite view by default (easier to recognise your field); street map as an alternative.
  var satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19,
    attribution: "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
    referrerPolicy: "strict-origin-when-cross-origin"
  });
  var streets = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, attribution: "&copy; OpenStreetMap contributors",
    // OSM tile policy requires a Referer; send the origin only (never the path)
    referrerPolicy: "strict-origin-when-cross-origin"
  });
  satellite.addTo(map);
  var labels = JSON.parse(document.getElementById("map-labels").textContent);
  var base = {}; base[labels.satellite] = satellite; base[labels.streets] = streets;
  L.control.layers(base, null, { collapsed: false }).addTo(map);
  var SAT = "#FFD54A", STREET = "#1E6B8C";
  var circle = L.circle(map.getCenter(), { radius: parseFloat(radIn.value), color: SAT, weight: 3, fillOpacity: 0.12 }).addTo(map);
  map.on("baselayerchange", function (e) { circle.setStyle({ color: e.layer === satellite ? SAT : STREET }); });
  function sync() {
    var lat = parseFloat(latIn.value), lon = parseFloat(lonIn.value);
    if (isFinite(lat) && isFinite(lon)) { circle.setLatLng([lat, lon]); }
    circle.setRadius(parseFloat(radIn.value));
    radOut.textContent = radIn.value;
  }
  map.on("click", function (e) {
    latIn.value = e.latlng.lat.toFixed(4);
    lonIn.value = e.latlng.lng.toFixed(4);
    sync();
  });
  [latIn, lonIn, radIn].forEach(function (i) { i.addEventListener("input", sync); });
  sync();
})();
