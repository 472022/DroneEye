const MapModule = (() => {
  let map;
  let marker;
  let trail;
  const trailPts = [];
  const MAX_TRAIL = 60;

  function init() {
    const el = document.getElementById("gps-map");
    if (!el || typeof L === "undefined") return;

    map = L.map("gps-map", {
      zoomControl: true,
      scrollWheelZoom: false,
      attributionControl: false,
    });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: "CartoDB",
      maxZoom: 19,
    }).addTo(map);

    const droneIcon = L.divIcon({
      className: "",
      html: '<div style="width:13px;height:13px;background:#38bdf8;border:2px solid #fff;border-radius:50%;box-shadow:0 0 12px rgba(56,189,248,0.9)"></div>',
      iconSize: [13, 13],
      iconAnchor: [6, 6],
    });

    marker = L.marker([18.5234, 73.8567], { icon: droneIcon }).addTo(map);
    trail = L.polyline([], {
      color: "#38bdf8",
      weight: 2,
      opacity: 0.45,
      dashArray: "5 5",
    }).addTo(map);

    map.setView([18.5234, 73.8567], 15);
  }

  function updatePosition(lat, lng) {
    if (!map || (!lat && !lng)) return;
    if (lat === 0 && lng === 0) return;

    const ll = [lat, lng];
    marker.setLatLng(ll);

    trailPts.push(ll);
    if (trailPts.length > MAX_TRAIL) {
      trailPts.shift();
    }
    trail.setLatLngs(trailPts);

    map.panTo(ll, {
      animate: true,
      duration: 0.5,
    });

    const coordEl = document.getElementById("map-coords");
    if (coordEl) {
      coordEl.textContent = lat.toFixed(6) + " N,  " + lng.toFixed(6) + " E";
    }

    const fixEl = document.getElementById("gps-fix-status");
    if (fixEl) {
      fixEl.textContent = "FIXED";
      fixEl.style.color = "var(--success)";
    }
  }

  document.addEventListener("DOMContentLoaded", init);

  return {
    updatePosition,
  };
})();
