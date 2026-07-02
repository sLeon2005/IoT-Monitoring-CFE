const body = document.querySelector("#concursos-body");
const metricCount = document.querySelector("#metric-count");
const metricLast = document.querySelector("#metric-last");
const metricUpdated = document.querySelector("#metric-updated");
const metricSource = document.querySelector("#metric-source");
const statusDot = document.querySelector("#status-dot");
const statusLabel = document.querySelector("#status-label");
const statusDetail = document.querySelector("#status-detail");
const clockTime = document.querySelector("#clock-time");
const clockDate = document.querySelector("#clock-date");
const weatherIcon = document.querySelector("#weather-icon");
const weatherTemp = document.querySelector("#weather-temp");
const weatherCondition = document.querySelector("#weather-condition");
const wifiEmoji = document.querySelector("#wifi-emoji");
const wifiLabel = document.querySelector("#wifi-label");

const placeholderWeather = {
  icon: "unknown",
  temperature: null,
  condition: "Clima pendiente",
};

let refreshSeconds = 30;

async function loadConcursos() {
  try {
    const response = await fetch("/api/concursos?limit=30", { cache: "no-store" });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    refreshSeconds = payload.refresh_seconds || refreshSeconds;
    render(payload);
  } catch (error) {
    metricSource.textContent = "Local error";
    statusLabel.textContent = "Sin conexion local";
    statusDetail.textContent = "No fue posible leer SQLite";
    statusDot.style.background = "var(--red)";
  }
}

async function loadWifiStatus() {
  try {
    const response = await fetch("/api/system/wifi", { cache: "no-store" });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    renderWifi(await response.json());
  } catch (error) {
    renderWifi({
      connected: false,
      signal_percent: null,
      label: "WiFi no disponible",
      level: "none",
    });
  }
}

function render(payload) {
  const items = payload.items || [];
  metricCount.textContent = String(items.length);
  metricUpdated.textContent = formatDateTime(payload.generated_at);

  if (items.length === 0) {
    metricLast.textContent = "--";
    statusLabel.textContent = "Sin concursos";
    statusDetail.textContent = `Sin publicaciones para ${payload.fecha_publicacion || "hoy"}`;
    statusDot.style.background = "var(--yellow)";
    body.innerHTML = '<tr><td colspan="6" class="empty">No hay concursos guardados.</td></tr>';
  } else {
    const latest = items[0];
    const latestDate = parseDate(latest.fecha_publicacion || latest.detectado_en);
    metricLast.textContent = latestDate ? formatDateTime(latestDate.toISOString()) : "--";
    updateActivityStatus(latestDate);
    body.innerHTML = items.map(renderRow).join("");
  }

  renderSourceStatus(payload.source_status);
}

function renderRow(item) {
  return `
    <tr>
      <td><strong>${escapeHtml(item.numero)}</strong></td>
      <td>${escapeHtml(item.entidad_federativa)}</td>
      <td><span class="badge">${escapeHtml(item.estado)}</span></td>
      <td>${escapeHtml(item.tipo_procedimiento)}</td>
      <td>${escapeHtml(formatDateTime(item.fecha_publicacion))}</td>
      <td>${escapeHtml(item.descripcion)}</td>
    </tr>
  `;
}

function renderSourceStatus(sourceStatus) {
  const status = sourceStatus?.status || "unknown";
  const message = sourceStatus?.message || "Monitor sin estado registrado";

  if (status === "ok" || status === "connected") {
    metricSource.textContent = "OK";
    return;
  }

  if (status === "blocked") {
    metricSource.textContent = "Bloqueado";
    statusLabel.textContent = "CFE sin conexion";
    statusDetail.textContent = "Portal bloqueo la sesion HTTP";
    statusDot.style.background = "var(--red)";
    return;
  }

  if (status === "error") {
    metricSource.textContent = "Error";
    statusLabel.textContent = "CFE con error";
    statusDetail.textContent = message;
    statusDot.style.background = "var(--red)";
    return;
  }

  metricSource.textContent = "Sin datos";
}

function updateActivityStatus(latestDate) {
  if (!latestDate) {
    statusLabel.textContent = "Fecha no disponible";
    statusDetail.textContent = "Ultimo concurso sin fecha";
    statusDot.style.background = "var(--yellow)";
    return;
  }

  const minutes = Math.floor((Date.now() - latestDate.getTime()) / 60000);
  statusDetail.textContent = `Ultimo concurso hace ${formatAge(minutes)}`;

  if (minutes < 15) {
    statusLabel.textContent = "Actividad reciente";
    statusDot.style.background = "var(--green)";
  } else if (minutes < 90) {
    statusLabel.textContent = "Actividad moderada";
    statusDot.style.background = "var(--yellow)";
  } else {
    statusLabel.textContent = "Sin concursos recientes";
    statusDot.style.background = "var(--red)";
  }
}

function formatAge(minutes) {
  if (minutes < 1) {
    return "menos de 1 minuto";
  }

  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;

  if (rest === 0) {
    return `${hours} h`;
  }

  return `${hours} h ${rest} min`;
}

function formatDateTime(value) {
  const date = parseDate(value);

  if (!date) {
    return "--";
  }

  return new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function parseDate(value) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function updateClock() {
  const now = new Date();

  clockTime.textContent = new Intl.DateTimeFormat("es-MX", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(now);

  clockDate.textContent = new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(now);
}

function renderWeather(weather) {
  const current = weather || placeholderWeather;
  const icon = current.icon || "unknown";

  weatherIcon.src = `/static/weather-icons/${icon}.svg`;
  weatherIcon.alt = current.condition || "Clima no disponible";
  weatherTemp.textContent = Number.isFinite(current.temperature)
    ? `${Math.round(current.temperature)}\u00b0C`
    : "--\u00b0C";
  weatherCondition.textContent = current.condition || "Clima pendiente";
}

function renderWifi(wifi) {
  wifiEmoji.textContent = emojiForWifiLevel(wifi.level);
  wifiLabel.textContent = wifi.label || "WiFi pendiente";
}

function emojiForWifiLevel(level) {
  const emojis = {
    good: "\u{1F7E2}",
    warning: "\u{1F7E1}",
    poor: "\u{1F534}",
    none: "\u274C",
  };

  return emojis[level] || emojis.none;
}

loadConcursos();
loadWifiStatus();
updateClock();
renderWeather(placeholderWeather);

setInterval(loadConcursos, refreshSeconds * 1000);
setInterval(loadWifiStatus, 30000);
setInterval(updateClock, 1000);
