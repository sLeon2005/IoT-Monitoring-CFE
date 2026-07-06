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
const wifiIcon = document.querySelector("#wifi-icon");
const wifiSsid = document.querySelector("#wifi-ssid");
const activityBars = document.querySelector("#activity-bars");
const activityTotal = document.querySelector("#activity-total");

const placeholderWeather = {
  icon: "unknown",
  temperature_c: null,
  condition: "Clima pendiente",
};

let refreshSeconds = 30;
let weatherRefreshSeconds = 900;
const selectedDate = getSelectedDate();

const ENTITY_ALIASES = {
  aguascalientes: "aguascalientes",
  "baja california": "baja-california",
  "baja california sur": "baja-california-sur",
  campeche: "campeche",
  chiapas: "chiapas",
  chihuahua: "chihuahua",
  "ciudad de mexico": "ciudad-de-mexico",
  cdmx: "ciudad-de-mexico",
  coahuila: "coahuila",
  "coahuila de zaragoza": "coahuila",
  colima: "colima",
  durango: "durango",
  guanajuato: "guanajuato",
  guerrero: "guerrero",
  hidalgo: "hidalgo",
  jalisco: "jalisco",
  mexico: "estado-de-mexico",
  "estado de mexico": "estado-de-mexico",
  edomex: "estado-de-mexico",
  michoacan: "michoacan",
  "michoacan de ocampo": "michoacan",
  morelos: "morelos",
  nayarit: "nayarit",
  "nuevo leon": "nuevo-leon",
  oaxaca: "oaxaca",
  puebla: "puebla",
  queretaro: "queretaro",
  "quintana roo": "quintana-roo",
  "san luis potosi": "san-luis-potosi",
  sinaloa: "sinaloa",
  sonora: "sonora",
  tabasco: "tabasco",
  tamaulipas: "tamaulipas",
  tlaxcala: "tlaxcala",
  veracruz: "veracruz",
  "veracruz de ignacio de la llave": "veracruz",
  yucatan: "yucatan",
  zacatecas: "zacatecas",
};

const ENTITY_DISPLAY_NAMES = {
  "coahuila de zaragoza": "Coahuila",
  "michoacan de ocampo": "Michoac\u00e1n",
  "veracruz de ignacio de la llave": "Veracruz",
};

async function loadConcursos() {
  try {
    const params = new URLSearchParams({ limit: "30" });

    if (selectedDate) {
      params.set("date", selectedDate);
    }

    const response = await fetch(`/api/concursos?${params}`, { cache: "no-store" });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    refreshSeconds = payload.refresh_seconds || refreshSeconds;
    render(payload);
  } catch (error) {
    setMetricSource("Local error");
    statusLabel.textContent = "Sin conexión local";
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

async function loadWeather() {
  try {
    const response = await fetch("/api/weather", { cache: "no-store" });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    weatherRefreshSeconds = payload.refresh_seconds || weatherRefreshSeconds;
    renderWeather(payload);
  } catch (error) {
    renderWeather({
      ...placeholderWeather,
      condition: "Clima no disponible",
    });
  }
}

async function loadRecentPublicationStats() {
  try {
    const response = await fetch("/api/stats/recent-publications", {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    renderRecentPublicationStats(await response.json());
  } catch (error) {
    renderRecentPublicationStats({ days: buildEmptyRecentDays() });
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
    body.innerHTML = '<tr><td colspan="5" class="empty">No hay concursos guardados.</td></tr>';
  } else {
    const latest = items[0];
    const latestDate = parseDate(latest.fecha_publicacion || latest.detectado_en);
    metricLast.textContent = latestDate ? formatDateTime(latestDate.toISOString()) : "--";
    updateActivityStatus(latestDate);
    body.innerHTML = items.map(renderRow).join("");
  }

  renderSourceStatus(payload.source_status);
}

function renderRecentPublicationStats(payload) {
  const days = Array.isArray(payload.days) ? payload.days : [];
  const normalizedDays = days.length > 0 ? days : buildEmptyRecentDays();
  const total = normalizedDays.reduce(
    (sum, day) => sum + Math.max(0, Number(day.count) || 0),
    0,
  );
  const maxCount = Math.max(1, ...normalizedDays.map((day) => Number(day.count) || 0));

  activityTotal.textContent = `${total} ${total === 1 ? "concurso" : "concursos"}`;

  activityBars.innerHTML = normalizedDays
    .map((day) => {
      const count = Math.max(0, Number(day.count) || 0);
      const height = count === 0 ? 0 : Math.max(12, Math.round((count / maxCount) * 100));
      const classes = ["activity-day"];

      if (day.is_today) {
        classes.push("is-today");
      }

      return `
        <div class="${classes.join(" ")}">
          <div class="activity-bar-track">
            <span class="activity-bar-fill" style="height: ${height}%"></span>
          </div>
          <span class="activity-day-label">${escapeHtml(day.label || "")}</span>
        </div>
      `;
    })
    .join("");
}

function buildEmptyRecentDays() {
  const labels = ["L", "M", "X", "J", "V", "S", "D"];
  const today = new Date();
  const days = [];

  for (let offset = 6; offset >= 0; offset -= 1) {
    const date = new Date(today);
    date.setDate(today.getDate() - offset);

    days.push({
      label: labels[(date.getDay() + 6) % 7],
      count: 0,
      is_today: offset === 0,
    });
  }

  return days;
}

function renderRow(item) {
  return `
    <tr>
      <td><strong>${escapeHtml(item.numero)}</strong></td>
      <td>${renderEntityBadge(item.entidad_federativa)}</td>
      <td>${escapeHtml(item.tipo_procedimiento)}</td>
      <td>${formatPublicationDateTime(item.fecha_publicacion)}</td>
      <td>${escapeHtml(item.descripcion)}</td>
    </tr>
  `;
}

function renderEntityBadge(value) {
  const normalized = normalizeEntity(value);
  const label = escapeHtml(ENTITY_DISPLAY_NAMES[normalized] || value || "Sin entidad");
  const entityKey = ENTITY_ALIASES[normalized] || "unknown";

  return `<span class="entity-badge entity-${entityKey}">${label}</span>`;
}

function normalizeEntity(value) {
  return String(value ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\./g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function renderSourceStatus(sourceStatus) {
  const status = sourceStatus?.status || "unknown";
  const message = sourceStatus?.message || "Monitor sin estado registrado";

  if (status === "ok" || status === "connected") {
    setMetricSource("OK");
    return;
  }

  if (status === "blocked") {
    setMetricSource("Bloqueado");
    statusLabel.textContent = "CFE sin conexión";
    statusDetail.textContent = "Portal bloqueó la sesión HTTP";
    statusDot.style.background = "var(--red)";
    return;
  }

  if (status === "error") {
    setMetricSource("Error");
    statusLabel.textContent = "CFE con error";
    statusDetail.textContent = message;
    statusDot.style.background = "var(--red)";
    return;
  }

  setMetricSource("Sin datos");
}

function setMetricSource(value) {
  if (metricSource) {
    metricSource.textContent = value;
  }
}

function updateActivityStatus(latestDate) {
  if (!latestDate) {
    statusLabel.textContent = "Fecha no disponible";
    statusDetail.textContent = "Último concurso sin fecha";
    statusDot.style.background = "var(--yellow)";
    return;
  }

  const minutes = Math.floor((Date.now() - latestDate.getTime()) / 60000);
  statusDetail.textContent = `ÚLTIMO CONCURSO HACE ${formatAge(minutes)}`;

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

function formatPublicationDateTime(value) {
  const date = parseDate(value);

  if (!date) {
    return "--";
  }

  const datePart = new Intl.DateTimeFormat("es-MX", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
  const timePart = new Intl.DateTimeFormat("es-MX", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  })
    .format(date)
    .replace(/\s*a\.\s*m\./i, " a.m.")
    .replace(/\s*p\.\s*m\./i, " p.m.");

  return `${escapeHtml(datePart)}<br>${escapeHtml(timePart)}`;
}

function parseDate(value) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function getSelectedDate() {
  const date = new URLSearchParams(window.location.search).get("date");

  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return null;
  }

  return date;
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
  const temperature = current.temperature_c ?? current.temperature;

  weatherIcon.src = `/static/weather-icons/${icon}.svg`;
  weatherIcon.alt = current.condition || "Clima no disponible";
  weatherTemp.textContent = Number.isFinite(temperature)
    ? `${Math.round(temperature)}\u00b0C`
    : "--\u00b0C";
  weatherCondition.textContent = current.condition || "Clima pendiente";
}

function renderWifi(wifi) {
  const bars = normalizeWifiBars(wifi.bars);
  const ssid = wifi.connected ? wifi.ssid || "Red conectada" : "Sin red";

  wifiIcon.src = `/static/wifi-icons/wifi_${bars}.svg`;
  wifiIcon.alt = wifi.label || "Estado WiFi";

  if (wifiSsid) {
    wifiSsid.textContent = ssid;
    wifiSsid.title = ssid;
  }
}

function normalizeWifiBars(value) {
  const bars = Number(value);

  if (!Number.isFinite(bars)) {
    return 0;
  }

  return Math.max(0, Math.min(3, Math.round(bars)));
}

loadConcursos();
loadRecentPublicationStats();
loadWifiStatus();
loadWeather();
updateClock();
renderWeather(placeholderWeather);

setInterval(loadConcursos, refreshSeconds * 1000);
setInterval(loadRecentPublicationStats, refreshSeconds * 1000);
setInterval(loadWifiStatus, 30000);
setInterval(() => loadWeather(), weatherRefreshSeconds * 1000);
setInterval(updateClock, 1000);
