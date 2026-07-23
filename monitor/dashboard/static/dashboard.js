const body = document.querySelector("#concursos-body");
const metricCount = document.querySelector("#metric-count");
const metricCountLabel = document.querySelector("#metric-count-label");
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
const tableMode = document.querySelector("#table-mode");
const systemHealthTag = document.querySelector("#system-health-tag");

const placeholderWeather = {
  icon: "unknown",
  temperature_c: null,
  condition: "Clima pendiente",
};

let refreshSeconds = 30;
let weatherRefreshSeconds = 900;
let dashboardView = "all";
const selectedDate = getSelectedDate();
const selectedView = getSelectedView();

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
    dashboardView = selectedView || (await loadDashboardState());
    const params = new URLSearchParams({ limit: "25" });

    if (selectedDate) {
      params.set("date", selectedDate);
    }

    params.set("view", dashboardView);

    const response = await fetch(`/api/concursos?${params}`, { cache: "no-store" });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    await ensureRelevantCount(payload);
    refreshSeconds = payload.refresh_seconds || refreshSeconds;
    render(payload);
  } catch (error) {
    setMetricSource("Local error");
    statusLabel.textContent = "Sin conexión local";
    statusDetail.textContent = "No fue posible leer SQLite";
    statusDot.style.background = "var(--red)";
  }
}

async function ensureRelevantCount(payload) {
  if (Number.isFinite(payload.relevant_count)) {
    return;
  }

  if ((payload.view || dashboardView) === "relevant") {
    payload.relevant_count = Array.isArray(payload.items) ? payload.items.length : 0;
    return;
  }

  const params = new URLSearchParams({ limit: "25", view: "relevant" });

  if (selectedDate) {
    params.set("date", selectedDate);
  }

  const response = await fetch(`/api/concursos?${params}`, { cache: "no-store" });

  if (!response.ok) {
    payload.relevant_count = 0;
    return;
  }

  const relevantPayload = await response.json();
  payload.relevant_count = Number.isFinite(relevantPayload.relevant_count)
    ? relevantPayload.relevant_count
    : Number.isFinite(relevantPayload.count)
      ? relevantPayload.count
      : Array.isArray(relevantPayload.items)
        ? relevantPayload.items.length
        : 0;
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

async function loadDashboardState() {
  const response = await fetch("/api/dashboard/state", { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const payload = await response.json();

  if (payload.view === "relevant" || payload.view === "all") {
    return payload.view;
  }

  return "all";
}

function render(payload) {
  const items = payload.items || [];
  const view = payload.view || dashboardView;
  const totalCount = Number.isFinite(payload.total_count) ? payload.total_count : items.length;
  const relevantCount = Number.isFinite(payload.relevant_count)
    ? payload.relevant_count
    : view === "relevant"
      ? items.length
      : 0;
  const metricTotalCount = Number.isFinite(payload.metric_total_count)
    ? payload.metric_total_count
    : totalCount;
  const metricRelevantCount = Number.isFinite(payload.metric_relevant_count)
    ? payload.metric_relevant_count
    : relevantCount;
  const isRelevantView = view === "relevant";

  renderMetricCounts({
    totalCount: metricTotalCount,
    relevantCount: metricRelevantCount,
  });
  renderTableMode({ view, dateRange: payload.date_range });
  metricUpdated.textContent = formatDateTime(payload.generated_at);

  if (items.length === 0) {
    const rangeDays = getDateRangeDays(payload.date_range);
    metricLast.textContent = "--";
    statusLabel.textContent = isRelevantView ? "Sin relevantes" : "Sin concursos";
    statusDetail.textContent = isRelevantView
      ? `${totalCount} publicados en \u00faltimos ${rangeDays} d\u00edas`
      : `Sin publicaciones para ${payload.fecha_publicacion || "hoy"}`;
    statusDot.style.background = "var(--yellow)";
    body.innerHTML = `<tr><td colspan="5" class="empty">${escapeHtml(
      isRelevantView
        ? `No hay concursos relevantes en los \u00faltimos ${rangeDays} d\u00edas.`
        : "No hay concursos guardados.",
    )}</td></tr>`;
  } else {
    const latest = items[0];
    const latestDate = parseDate(latest.fecha_publicacion || latest.detectado_en);
    metricLast.textContent = latestDate ? formatDateTime(latestDate.toISOString()) : "--";
    updateActivityStatus(latestDate, isRelevantView);
    body.innerHTML = renderRows(items, isRelevantView);
  }

  renderSourceStatus(payload.source_status);
}

function renderTableMode({ view, dateRange }) {
  if (!tableMode) {
    return;
  }

  const rangeDays = getDateRangeDays(dateRange);

  tableMode.textContent =
    view === "relevant"
      ? "Mostrando relevantes recientes"
      : "Mostrando todos los concursos";
}

async function loadSystemHealth() {
  if (!systemHealthTag) {
    return;
  }

  try {
    const response = await fetch("/api/system/health", { cache: "no-store" });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    renderSystemHealth(await response.json());
  } catch (error) {
    systemHealthTag.textContent = "-- C | -- | total --";
  }
}

function renderMetricCounts({ totalCount, relevantCount }) {
  metricCountLabel.textContent = selectedDate
    ? "CONCURSOS PUBLICADOS / RELEVANTES"
    : "PUBLICADOS HOY / RELEVANTES";
  metricCount.innerHTML = `
    <span class="metric-count-pair">
      <span><b>${totalCount}</b><small>publicados</small></span>
      <span><b>${relevantCount}</b><small>relevantes</small></span>
    </span>
  `;
}

function pluralizeConcursos(count) {
  return count === 1 ? "concurso" : "concursos";
}

function renderRecentPublicationStats(payload) {
  const days = Array.isArray(payload.days) ? payload.days : [];
  const normalizedDays = days.length > 0 ? days : buildEmptyRecentDays();
  const total = normalizedDays.reduce(
    (sum, day) => sum + Math.max(0, Number(day.count) || 0),
    0,
  );
  const maxCount = Math.max(1, ...normalizedDays.map((day) => Number(day.count) || 0));

  activityTotal.innerHTML = `ÚLTIMOS 7 DÍAS: <span class="activity-count-number">${total}</span> ${pluralizeConcursos(total).toUpperCase()} EN TOTAL`;

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

function renderRows(items, useDayBands) {
  let currentDateKey = null;
  let currentBand = 0;

  return items
    .map((item) => {
      if (!useDayBands) {
        return renderRow(item);
      }

      const dateKey = getPublicationDateKey(item);

      if (dateKey !== currentDateKey) {
        currentDateKey = dateKey;
        currentBand += 1;
      }

      const bandClass =
        currentBand % 2 === 0
          ? "publication-day-band-b"
          : "publication-day-band-a";
      return renderRow(item, bandClass);
    })
    .join("");
}

function renderRow(item, rowClass = "") {
  const classAttribute = rowClass ? ` class="${escapeHtml(rowClass)}"` : "";

  return `
    <tr${classAttribute}>
      <td><strong>${escapeHtml(item.numero)}</strong></td>
      <td>${renderEntityBadge(item.entidad_federativa)}</td>
      <td>${escapeHtml(item.tipo_procedimiento)}</td>
      <td>${formatPublicationDateTime(item.fecha_publicacion)}</td>
      <td>${escapeHtml(item.descripcion)}</td>
    </tr>
  `;
}

function getPublicationDateKey(item) {
  const rawDate = item.fecha_publicacion || item.detectado_en;
  return String(rawDate || "").slice(0, 10) || "sin-fecha";
}

function getDateRangeDays(dateRange) {
  const days = Number(dateRange?.days);

  if (!Number.isFinite(days) || days < 1) {
    return 1;
  }

  return Math.round(days);
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

function updateActivityStatus(latestDate, isRelevantView = false) {
  if (!latestDate) {
    statusLabel.textContent = "Fecha no disponible";
    statusDetail.textContent = "Último concurso sin fecha";
    statusDot.style.background = "var(--yellow)";
    return;
  }

  const minutes = Math.floor((Date.now() - latestDate.getTime()) / 60000);
  statusDetail.textContent = `ÚLTIMO CONCURSO HACE ${formatAge(minutes)}`;

  if (minutes < 60) {
    statusLabel.textContent = "Actividad reciente";
    statusDot.style.background = "var(--green)";
  } else if (minutes <= 180) {
    statusLabel.textContent = "Actividad moderada";
    statusDot.style.background = "var(--yellow)";
  } else {
    statusLabel.textContent = isRelevantView
      ? "Sin concursos relevantes recientes"
      : "Sin concursos recientes";
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
  const rawDate = new URLSearchParams(window.location.search).get("date");
  const date = rawDate?.split(/[?&]/)[0];

  if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return null;
  }

  return date;
}

function getSelectedView() {
  const view = new URLSearchParams(window.location.search).get("view");

  if (view === "all" || view === "relevant") {
    return view;
  }

  return null;
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

function renderSystemHealth(health) {
  if (!systemHealthTag) {
    return;
  }

  const temperature = toFiniteNumber(health?.temperature_c);
  const uptimeSeconds = toFiniteNumber(health?.uptime_seconds);
  const totalUptimeSeconds = toFiniteNumber(health?.total_uptime_seconds);
  const temperatureText = temperature !== null
    ? `${Math.round(temperature)}C`
    : "-- C";
  const uptimeText = uptimeSeconds !== null
    ? formatCompactDuration(uptimeSeconds)
    : "--";
  const totalText = totalUptimeSeconds !== null
    ? `${Math.floor(totalUptimeSeconds / 3600)}h`
    : "--";

  systemHealthTag.textContent = `${temperatureText} | ${uptimeText} | total ${totalText}`;
}

function toFiniteNumber(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);

  return Number.isFinite(number) ? number : null;
}

function formatCompactDuration(seconds) {
  const totalMinutes = Math.max(0, Math.floor(seconds / 60));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  return `${hours}h ${minutes}m`;
}

loadConcursos();
loadRecentPublicationStats();
loadWifiStatus();
loadSystemHealth();
loadWeather();
updateClock();
renderWeather(placeholderWeather);

setInterval(loadConcursos, refreshSeconds * 1000);
setInterval(loadRecentPublicationStats, refreshSeconds * 1000);
setInterval(loadWifiStatus, 30000);
setInterval(loadSystemHealth, 60000);
setInterval(() => loadWeather(), weatherRefreshSeconds * 1000);
setInterval(updateClock, 1000);
