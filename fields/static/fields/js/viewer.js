/* AquaPin viewer: map + season slider + advice panel. All dynamic text uses textContent. */
(function () {
  "use strict";
  var data = JSON.parse(document.getElementById("viewer-data").textContent);
  var cfg = JSON.parse(document.getElementById("viewer-config").textContent);
  var T = JSON.parse(document.getElementById("i18n").textContent);
  var days = data.days;
  var frames = {};
  data.frames.forEach(function (f) { frames[f.date] = f; });
  var $ = function (id) { return document.getElementById(id); };
  var fmt = function (s, o) { return s.replace(/\{(\w+)\}/g, function (_, k) { return o[k]; }); };
  var fmtDate = function (iso) {
    return new Date(iso + "T00:00:00Z").toLocaleDateString(cfg.lang, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
  };

  /* ---- map: Sentinel-2 true-colour chip as basemap, NDVI frame on top ---- */
  var center = [data.lat, data.lon];
  var bounds = data.base_bounds || (data.frames[0] && data.frames[0].bounds) || L.latLng(center).toBounds(data.radius_m * 6);
  var map = L.map("map", { attributionControl: false, zoomSnap: 0.25, minZoom: 10, maxZoom: 19 });
  map.fitBounds(bounds);
  if (data.base && data.base_bounds) {
    L.imageOverlay(cfg.assetBase + data.base, data.base_bounds, { className: "px" }).addTo(map);
  }
  L.circle(center, { radius: data.radius_m, color: "#1D2620", weight: 2, fill: false, dashArray: "6 4" }).addTo(map);
  var overlay = null, shownFrame = null;
  function showFrame(f) {
    if (shownFrame === (f && f.date)) { return; }
    shownFrame = f ? f.date : null;
    if (overlay) { map.removeLayer(overlay); overlay = null; }
    if (f) {
      overlay = L.imageOverlay(cfg.assetBase + f.file, f.bounds, { opacity: 0.85, className: "px" }).addTo(map);
    }
  }

  /* ---- chart: deficit vs allowed, rain bars, irrigation ticks ---- */
  var W = 640, H = 150, PAD = 6;
  var svgNS = "http://www.w3.org/2000/svg";
  var chart = $("chart");
  var maxDef = Math.max.apply(null, days.map(function (d) { return Math.max(d.dr + d.irrig, d.raw); })) * 1.08 || 1;
  var maxRain = Math.max.apply(null, days.map(function (d) { return d.rain; })) || 1;
  var xOf = function (i) { return PAD + (W - 2 * PAD) * (days.length > 1 ? i / (days.length - 1) : 0); };
  var yOf = function (v) { return H - PAD - (H - 2 * PAD) * (v / maxDef); };
  function el(name, attrs) {
    var e = document.createElementNS(svgNS, name);
    Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }
  var barW = Math.max((W - 2 * PAD) / days.length, 1);
  days.forEach(function (d, i) {
    if (d.rain > 0) {
      var h = (H * 0.28) * (d.rain / maxRain);
      chart.appendChild(el("rect", { "class": "rain", x: xOf(i) - barW / 2, y: H - PAD - h, width: barW, height: h }));
    }
  });
  chart.appendChild(el("polyline", { "class": "raw", points: days.map(function (d, i) { return xOf(i) + "," + yOf(d.raw); }).join(" ") }));
  chart.appendChild(el("polyline", { "class": "dr", points: days.map(function (d, i) { return xOf(i) + "," + yOf(d.dr + d.irrig); }).join(" ") }));
  days.forEach(function (d, i) {
    if (d.irrig > 0) { chart.appendChild(el("line", { "class": "irr", x1: xOf(i), x2: xOf(i), y1: PAD, y2: H - PAD })); }
  });
  var cursor = el("line", { "class": "cursor", x1: 0, x2: 0, y1: 0, y2: H });
  chart.appendChild(cursor);

  /* ---- observations table (screen readers, and a plain-text fallback) ---- */
  var tbody = document.querySelector("#obs-table tbody");
  data.frames.forEach(function (f) {
    var tr = document.createElement("tr");
    [fmtDate(f.date), f.ndvi === null ? "-" : f.ndvi.toFixed(2)].forEach(function (t) {
      var td = document.createElement("td"); td.textContent = t; tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  /* ---- advice panel ---- */
  var slider = $("slider");
  slider.max = String(days.length - 1);
  /* ---- irrigation days: clickable list, so the advice is never hidden in the timeline ---- */
  var evBox = $("events");
  var evDays = [];
  days.forEach(function (d, i) { if (d.irrig > 0) { evDays.push(i); } });
  if (!evDays.length) { evBox.textContent = T.events_none; evBox.className = "note"; }
  evDays.forEach(function (i) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "chip";
    b.textContent = new Date(days[i].date + "T00:00:00Z").toLocaleDateString(cfg.lang, { day: "numeric", month: "short", timeZone: "UTC" }) + " · " + Math.round(days[i].irrig) + " mm";
    b.addEventListener("click", function () { stop(); idx = i; setDay(i); });
    evBox.appendChild(b);
  });
  var assumptions = $("assumptions");
  ((data.advice_final && data.advice_final.assumptions) || []).forEach(function (a) {
    var li = document.createElement("li"); li.textContent = a; assumptions.appendChild(li);
  });
  function why(rows) {
    var dl = $("why-list");
    dl.textContent = "";
    rows.forEach(function (r) {
      var dt = document.createElement("dt"); dt.textContent = r[0];
      var dd = document.createElement("dd"); dd.textContent = r[1];
      dl.appendChild(dt); dl.appendChild(dd);
    });
  }
  function setDay(i) {
    var d = days[i];
    var f = d.frame ? frames[d.frame] : null;
    showFrame(f);
    $("date").textContent = fmtDate(d.date);
    var irrigate = d.decision === "irrigate";
    var dec = $("decision");
    dec.textContent = irrigate ? T.irrigate : T.wait;
    dec.className = "decision" + (irrigate ? " irrigate" : "");
    $("amount").textContent = irrigate ? fmt(T.mm_line, { mm: Math.round(d.irrig), m3: Math.round(d.irrig * 10) }) : "";
    var badge = $("conf-badge");
    badge.textContent = T.confidence + ": " + T["conf_" + d.confidence];
    badge.className = "badge " + d.confidence;
    $("conf-reason").textContent = d.age === null ? T.conf_reason_none : fmt(T.conf_reason, { age: d.age });
    $("frame-caption").textContent = f ? fmt(T.frame_age, { date: fmtDate(f.date) }) + " · NDVI " + (f.ndvi === null ? "-" : f.ndvi.toFixed(2)) : T.no_image;
    var rain3 = 0;
    for (var k = 1; k <= 3 && i + k < days.length; k++) { rain3 += days[i + k].rain; }
    why([
      [T.why_kcb, d.kcb.toFixed(2) + " (" + (f ? T.why_src_sat : T.why_src_table) + ")"],
      [T.why_dr, (d.dr + d.irrig).toFixed(0) + " mm"],
      [T.why_raw, d.raw.toFixed(0) + " mm"],
      [T.why_rain, rain3.toFixed(0) + " mm"],
      [T.why_ver, (data.advice_final && data.advice_final.pipeline_version) || "-"]
    ]);
    var x = xOf(i);
    cursor.setAttribute("x1", x); cursor.setAttribute("x2", x);
    slider.value = String(i);
    var nd = f && f.ndvi !== null ? f.ndvi.toFixed(2) : "-";
    slider.setAttribute("aria-valuetext", fmtDate(d.date) + ", NDVI " + nd);
    $("summary").textContent = fmt(T.summary, { date: fmtDate(d.date), ndvi: nd, dr: (d.dr + d.irrig).toFixed(0), raw: d.raw.toFixed(0), rain: d.rain.toFixed(0), et0: d.et0.toFixed(1) });
  }

  /* ---- playback ---- */
  var timer = null, idx = 0;
  var playBtn = $("play");
  function stop() { if (timer) { clearInterval(timer); timer = null; } playBtn.textContent = T.play; }
  function play() {
    if (idx >= days.length - 1) { idx = 0; }
    playBtn.textContent = T.pause;
    function tick() {
      idx += 1; setDay(idx);
      if (idx >= days.length - 1) { stop(); return; }
      if (days[idx].irrig > 0) {  /* linger on every irrigation advice so it is seen */
        clearInterval(timer);
        timer = setTimeout(function () { timer = setInterval(tick, 55); }, 1600);
      }
    }
    timer = setInterval(tick, 55);
  }
  playBtn.addEventListener("click", function () { if (timer) { stop(); } else { play(); } });
  slider.addEventListener("input", function () { stop(); idx = parseInt(slider.value, 10); setDay(idx); });
  slider.addEventListener("keydown", function (e) {
    var step = e.key === "PageUp" ? 7 : e.key === "PageDown" ? -7 : 0;
    if (step) {
      e.preventDefault(); stop();
      idx = Math.min(Math.max(idx + step, 0), days.length - 1); setDay(idx);
    }
  });
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  idx = cfg.autoplay ? 0 : days.length - 1;
  setDay(idx);
  if (cfg.autoplay && !reduce) { play(); }
})();
