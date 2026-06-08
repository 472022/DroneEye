(function () {
  const socket = io(window.location.origin);
  let frameCount = 0;
  let settingsCloseTimer;

  socket.on("connect", () => {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) overlay.style.display = "none";

    setPill("pill-esp32", "warning", "CONNECTING");
    fetch("/api/data").then((r) => r.json()).then(applyData).catch(() => {});
    fetch("/api/detection").then((r) => r.json()).then(applyDetection).catch(() => {});
    fetch("/api/alerts").then((r) => r.json()).then((d) => AlertsModule.loadInitial(d)).catch(() => {});
    fetch("/api/status").then((r) => r.json()).then(applyStatus).catch(() => {});
  });

  socket.on("disconnect", () => setPill("pill-esp32", "offline", "OFFLINE"));

  socket.on("sensor_update", (d) => {
    applyData(d);
    MapModule.updatePosition(d.lat, d.lng);
  });

  socket.on("detection_update", (d) => applyDetection(d));

  socket.on("new_alert", (a) => {
    AlertsModule.addAlert(a);
    playBeep(a.risk);
  });

  socket.on("connection_lost", () => {
    setPill("pill-esp32", "offline", "OFFLINE");
    showBanner("ESP32 connection lost - no data received for 10s");
  });

  function applyData(d) {
    GaugesModule.updateGauge("voltage", d.voltage || 0);
    GaugesModule.updateGauge("current", d.current || 0);
    GaugesModule.updateGauge("temperature", d.temperature || 0);
    GaugesModule.updateVibration(!!d.vibration);

    const gpsEl = document.getElementById("gps-overlay");
    if (gpsEl && d.lat) {
      gpsEl.textContent = "GPS: " + d.lat.toFixed(4) + "N  " + d.lng.toFixed(4) + "E";
    }

    if (d.connected) setPill("pill-esp32", "online", "ESP32");
    if (d.lat && d.lat !== 0) setPill("pill-gps", "online", "GPS FIXED");
    frameCount++;
  }

  function applyDetection(d) {
    const badge = document.getElementById("risk-badge");
    const fill = document.getElementById("conf-fill");
    const label = document.getElementById("det-label");
    const panel = document.getElementById("detection-panel");
    const tsEl = document.getElementById("det-timestamp");
    if (!badge) return;

    const risk = (d.risk || "NONE").toLowerCase();
    const riskMap = {
      none: "NO FAULT",
      medium: "MEDIUM RISK",
      high: "HIGH RISK",
    };

    badge.textContent = riskMap[risk] || d.risk;
    badge.className = "risk-badge " + risk;

    const conf = (d.confidence || 0) * 100;
    if (fill) {
      fill.style.width = conf + "%";
      fill.className = "conf-fill " + risk;
    }

    if (label) label.textContent = d.label || "--";
    if (panel) panel.className = "panel risk-" + risk;
    if (tsEl && d.timestamp) {
      tsEl.textContent = new Date(d.timestamp).toLocaleTimeString("en-GB");
    }

    setPill("pill-ai", "online", "AI ACTIVE");
  }

  function applyStatus(s) {
    if (s.esp32_connected) setPill("pill-esp32", "online", "ESP32");
    else setPill("pill-esp32", "offline", "OFFLINE");

    if (s.camera_online) setPill("pill-camera", "online", "LIVE");
    else setPill("pill-camera", "offline", "CAMERA");

    if (s.detector_loaded) setPill("pill-ai", "online", "AI MODEL");
    else setPill("pill-ai", "warning", "MOCK MODE");

    const camLabel = document.getElementById("cam-ip-label");
    if (camLabel && s.cam_ip && s.cam_ip !== "not set") camLabel.textContent = s.cam_ip;

    const settingCam = document.getElementById("s-cam-ip");
    const settingEsp = document.getElementById("s-esp32-ip");
    if (settingCam) settingCam.value = s.cam_ip && s.cam_ip !== "not set" ? s.cam_ip : "";
    if (settingEsp) settingEsp.value = s.esp32_ip && s.esp32_ip !== "not set" ? s.esp32_ip : "";
  }

  function setPill(id, state, text) {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = "status-pill " + state;
    el.textContent = text;
  }

  function updateClock() {
    const el = document.getElementById("top-clock");
    if (el) {
      el.textContent = new Date().toLocaleTimeString("en-GB", { hour12: false });
    }
  }

  setInterval(updateClock, 1000);
  updateClock();

  setInterval(() => {
    const el = document.getElementById("fps-counter");
    if (el) el.textContent = frameCount + " fps";
    frameCount = 0;
  }, 1000);

  setInterval(() => {
    fetch("/api/status").then((r) => r.json()).then(applyStatus).catch(() => {});
  }, 10000);

  document.addEventListener("DOMContentLoaded", () => {
    const gear = document.getElementById("settings-btn");
    const panel = document.getElementById("settings-panel");
    const close = document.getElementById("settings-close");
    const save = document.getElementById("settings-save");
    const test = document.getElementById("settings-test");
    const threshold = document.getElementById("s-threshold");
    const thresholdValue = document.getElementById("s-threshold-val");

    if (gear) gear.addEventListener("click", () => toggleSettings(panel));
    if (close) close.addEventListener("click", () => closeSettings(panel));

    if (save) {
      save.addEventListener("click", () => {
        const body = {
          esp32_ip: getInputValue("s-esp32-ip"),
          cam_ip: getInputValue("s-cam-ip"),
          threshold: parseFloat(getInputValue("s-threshold") || "0.45"),
          cooldown: parseInt(getInputValue("s-cooldown") || "10", 10),
        };

        fetch("/api/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        })
          .then(() => showToast("Settings applied", "success"))
          .catch(() => showToast("Failed to save", "error"));
      });
    }

    if (test) {
      test.addEventListener("click", () => {
        fetch("/api/status")
          .then((r) => r.json())
          .then((s) => {
            showToast(
              "ESP32: " + (s.esp32_connected ? "ONLINE" : "OFFLINE") + " | CAM: " + (s.camera_online ? "LIVE" : "OFFLINE"),
              s.esp32_connected ? "success" : "error",
            );
          })
          .catch(() => showToast("Cannot reach server", "error"));
      });
    }

    if (threshold && thresholdValue) {
      thresholdValue.textContent = parseFloat(threshold.value).toFixed(2);
      threshold.addEventListener("input", () => {
        thresholdValue.textContent = parseFloat(threshold.value).toFixed(2);
      });
    }
  });

  function toggleSettings(panel) {
    if (!panel) return;
    if (panel.classList.contains("open")) {
      closeSettings(panel);
    } else {
      openSettings(panel);
    }
  }

  function openSettings(panel) {
    clearTimeout(settingsCloseTimer);
    panel.hidden = false;
    panel.setAttribute("aria-hidden", "false");
    requestAnimationFrame(() => panel.classList.add("open"));
  }

  function closeSettings(panel) {
    if (!panel) return;
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
    clearTimeout(settingsCloseTimer);
    settingsCloseTimer = setTimeout(() => {
      if (!panel.classList.contains("open")) panel.hidden = true;
    }, 300);
  }

  function getInputValue(id) {
    const el = document.getElementById(id);
    return el ? el.value : "";
  }

  function showToast(msg, type = "success") {
    const t = document.getElementById("toast");
    if (!t) return;

    t.textContent = msg;
    t.className = "show " + type;
    setTimeout(() => {
      t.className = type;
    }, 3200);
  }

  window.showToast = showToast;

  function showBanner(msg) {
    let b = document.getElementById("conn-banner");
    if (!b) {
      b = document.createElement("div");
      b.id = "conn-banner";
      b.style.cssText = "position:fixed;top:52px;left:0;right:0;background:rgba(239,68,68,0.18);color:#fca5a5;text-align:center;padding:8px;font-size:13px;z-index:400;border-bottom:1px solid rgba(239,68,68,0.3)";
      document.body.appendChild(b);
    }

    b.textContent = msg;
    b.style.display = "block";
    socket.once("sensor_update", () => {
      if (b) b.style.display = "none";
    });
  }

  let audioCtx;

  function playBeep(risk) {
    try {
      if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();

      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.frequency.value = risk === "HIGH" ? 880 : 540;
      gain.gain.setValueAtTime(0.18, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(
        0.001,
        audioCtx.currentTime + (risk === "HIGH" ? 0.25 : 0.12),
      );
      osc.start();
      osc.stop(audioCtx.currentTime + 0.25);
    } catch (e) {}
  }
})();
