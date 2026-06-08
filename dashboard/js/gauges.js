const GaugesModule = (() => {
  const MAX_PTS = 24;
  const history = {
    voltage: [],
    current: [],
    temperature: [],
  };

  const CFG = {
    voltage: { min: 0, max: 15, warnAt: 13, dangerAt: 14.5 },
    current: { min: 0, max: 30, warnAt: 24, dangerAt: 28 },
    temperature: { min: 0, max: 100, warnAt: 70, dangerAt: 85 },
  };

  function getState(key, val) {
    const c = CFG[key];
    if (val >= c.dangerAt) return "danger";
    if (val >= c.warnAt) return "warning";
    return "normal";
  }

  function updateGauge(key, val) {
    const c = CFG[key];
    const state = getState(key, val);
    const pct = Math.min(100, Math.max(0, ((val - c.min) / (c.max - c.min)) * 100));

    const valEl = document.getElementById("val-" + key);
    if (valEl) {
      valEl.textContent = key === "temperature" ? val.toFixed(1) : val.toFixed(2);
      valEl.className = "gauge-value " + (state !== "normal" ? state : "");
    }

    const fillEl = document.getElementById("fill-" + key);
    if (fillEl) {
      fillEl.style.width = pct + "%";
      fillEl.className = "gauge-fill " + state;
    }

    const card = document.getElementById("gauge-" + key);
    if (card) {
      card.className = "gauge-card " + (state !== "normal" ? state : "");
    }

    history[key].push(val);
    if (history[key].length > MAX_PTS) {
      history[key].shift();
    }
    updateSparkline(key, state);
  }

  function updateSparkline(key, state) {
    const svg = document.getElementById("spark-" + key);
    if (!svg) return;

    const line = svg.querySelector("polyline.spark-line");
    if (!line) return;

    const pts = history[key];
    if (pts.length < 2) return;

    const c = CFG[key];
    const W = 200;
    const H = 40;
    const PAD = 3;
    const points = pts
      .map((v, i) => {
        const x = (i / (MAX_PTS - 1)) * W;
        const y = H - PAD - ((v - c.min) / (c.max - c.min)) * (H - PAD * 2);
        return x.toFixed(1) + "," + Math.max(PAD, Math.min(H - PAD, y)).toFixed(1);
      })
      .join(" ");

    line.setAttribute("points", points);
    svg.className = "sparkline-svg " + (state !== "normal" ? state : "");
  }

  function updateVibration(active) {
    const badge = document.getElementById("vib-badge");
    const card = document.getElementById("gauge-vibration");
    if (!badge) return;

    if (active) {
      badge.textContent = "ACTIVE";
      badge.className = "vibration-badge vib-active";
      if (card) card.className = "gauge-card danger";
    } else {
      badge.textContent = "NONE";
      badge.className = "vibration-badge vib-none";
      if (card) card.className = "gauge-card";
    }
  }

  return {
    updateGauge,
    updateVibration,
  };
})();
