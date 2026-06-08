const AlertsModule = (() => {
  let count = 0;

  function fmtTime(iso) {
    try {
      return new Date(iso).toLocaleTimeString("en-GB", { hour12: false });
    } catch {
      return "--:--:--";
    }
  }

  function rowHTML(a) {
    const risk = (a.risk || "NONE").toLowerCase();
    const conf = a.confidence ? (a.confidence * 100).toFixed(1) + "%" : "--";
    const lat = typeof a.lat === "number" ? a.lat.toFixed(4) + "N" : "--";
    const lng = typeof a.lng === "number" ? a.lng.toFixed(4) + "E" : "--";
    const v = typeof a.voltage === "number" ? a.voltage.toFixed(1) + "kV" : "";
    const t = typeof a.temperature === "number" ? a.temperature.toFixed(0) + "C" : "";

    return `<div class="alert-row ${risk}" data-id="${a.id || ""}">
      <div class="alert-time">${fmtTime(a.timestamp)}</div>
      <div class="alert-content">
        <span class="alert-badge ${risk}">${a.risk || "UNKNOWN"}</span>
        <span class="alert-label">${a.label || "Fault"}</span>
        <span class="alert-confidence">${conf}</span>
      </div>
      <div class="alert-meta">${lat} ${lng}${v ? " &middot; " + v : ""}${t ? " &middot; " + t : ""}</div>
    </div>`;
  }

  function updateCount() {
    const badge = document.getElementById("alert-count");
    if (badge) badge.textContent = count;
  }

  function loadInitial(arr) {
    count = arr.length;
    const list = document.getElementById("alert-list");
    if (!list) return;

    if (!arr.length) {
      list.innerHTML = '<div class="alert-empty">No alerts &mdash; system nominal</div>';
    } else {
      list.innerHTML = arr.map(rowHTML).join("");
    }
    updateCount();
  }

  function addAlert(a) {
    count++;
    const list = document.getElementById("alert-list");
    if (!list) return;

    const empty = list.querySelector(".alert-empty");
    if (empty) empty.remove();

    const div = document.createElement("div");
    div.innerHTML = rowHTML(a);
    list.insertBefore(div.firstElementChild, list.firstChild);
    updateCount();

    const panel = document.getElementById("alert-panel");
    if (panel) {
      panel.classList.add("flash");
      setTimeout(() => panel.classList.remove("flash"), 700);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("alert-clear-btn");
    if (btn) {
      btn.addEventListener("click", () => {
        fetch("/api/alerts/clear", { method: "POST" }).then(() => {
          count = 0;
          loadInitial([]);
        });
      });
    }
  });

  return {
    loadInitial,
    addAlert,
  };
})();
