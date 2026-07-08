# AGENTS.md

Guia para agentes de IA trabajando en este repositorio.

## Proyecto

IoT Monitoring CFE es un sistema de monitoreo autonomo para concursos publicos de CFE.

El sistema esta pensado para ejecutarse en una Raspberry Pi y alimentar:

- SDK interna para consumir el portal de CFE.
- Monitor periodico.
- SQLite historico.
- Dashboard web local para pantalla HDMI.
- Notificaciones por Telegram, filtradas por relevancia.
- Clima actual via API externa sencilla.
- Indicadores de estado y, en el futuro, GPIO para torreta luminosa.

## Arquitectura

El proyecto se divide en dos capas principales:

- `cfe_api/`: SDK interna. Su unica responsabilidad es hablar con el portal de CFE.
- `monitor/`: aplicacion operativa. Consume la SDK, guarda historico, emite eventos, actualiza dashboard y notifica.

Reglas estrictas:

- `cfe_api` no debe conocer Telegram, SQLite, dashboard, GPIO, Raspberry Pi ni systemd.
- `monitor` no debe conocer detalles internos del protocolo HTTP de CFE.
- El dashboard nunca consulta CFE directamente; siempre lee SQLite.
- El codigo de aplicacion no debe acceder directamente a campos crudos del JSON de CFE, como `item["Numero"]`.
- Toda conversion del JSON de CFE debe vivir en `Concurso.from_dict()`.
- Toda conversion auxiliar de fechas debe vivir en `cfe_api/core/utils.py`.
- El filtro de relevancia vive en `monitor/filtering.py`; no duplicar logica de filtrado en dashboard o Telegram.
- No guardar tokens, cookies, chat IDs ni secretos en codigo versionado.

## Estructura Relevante

```text
cfe_api/
  core/
    session.py           sesion HTTP requests, cookies, CSRF
    browser_session.py   bootstrap opcional con Chromium/Playwright
    errors.py            errores esperados del SDK
    utils.py             utilidades compartidas de la SDK
  models/
    concurso.py          dataclass Concurso y conversion desde JSON CFE
  services/
    concursos.py         endpoint getProcBusqueda
  main.py                demo manual de la SDK

monitor/
  config.py              configuracion desde .env
  cfe_session.py         resolucion de sesion CFE para monitor
  filtering.py           filtro de concursos relevantes por terminos configurables
  monitor.py             orquestador de polling y eventos
  main.py                CLI principal del monitor
  events.py              eventos del dominio del monitor
  database/
    repository.py        persistencia SQLite
    inspect.py           inspeccion manual de SQLite
  dashboard/
    app.py               servidor web local
    state.py             estado runtime del dashboard, como vista all/relevant
    static/              HTML/CSS/JS e iconos
  notifications/
    base.py              contrato comun de notificadores
    dispatcher.py        despacha notificaciones pendientes desde SQLite
    outbox.py            encola notificaciones relevantes antes de enviarlas
    relevant.py          decorador que solo notifica concursos relevantes
    telegram.py          notificador Telegram y CLI de prueba
  weather/
    open_meteo.py        cliente de clima actual Open-Meteo
  system/
    network.py           estado WiFi Windows/Linux

config/
  filters/
    include.txt          terminos para concursos relevantes

tools/
  diagnose_environment.py diagnostico local sin consultar CFE ni Telegram

```

## Configuracion

La configuracion local vive en `.env`. Este archivo no debe versionarse.

Variables principales:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
MONITOR_DB_PATH=data/monitor.sqlite3
MONITOR_INTERVAL_SECONDS=300
MONITOR_LOG_LEVEL=INFO
CFE_COOKIE_HEADER=
CFE_REQUEST_VERIFICATION_TOKEN=
CFE_SESSION_CACHE_PATH=data/cfe_session.json
CFE_BROWSER_PROFILE_DIR=data/browser-profile
CFE_BROWSER_BOOTSTRAP_ENABLED=false
CFE_BROWSER_HEADLESS=false
CFE_BROWSER_TIMEOUT_MS=60000
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8000
DASHBOARD_REFRESH_SECONDS=120
WEATHER_ENABLED=true
WEATHER_LOCATION_NAME=Tampico
WEATHER_LATITUDE=22.2372
WEATHER_LONGITUDE=-97.8700
WEATHER_REFRESH_SECONDS=900
WEATHER_TIMEOUT_SECONDS=10
```

Notas:

- `CFE_COOKIE_HEADER` y `CFE_REQUEST_VERIFICATION_TOKEN` pueden dejarse vacios si se usa bootstrap por navegador.
- `data/cfe_session.json` es cache local de cookies/token y no debe versionarse.
- `data/monitor.sqlite3` es la base local SQLite y no debe versionarse.
- Playwright/Chromium se usa para obtener sesion CFE cuando el acceso directo con `requests` es bloqueado.
- Open-Meteo se usa para clima actual; no requiere API key.
- `config/filters/include.txt` se versiona porque define el giro relevante del proyecto; no debe contener secretos.

## Comandos Utiles

Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
```

Instalar Chromium para bootstrap por navegador:

```powershell
python -m playwright install chromium
```

Diagnosticar entorno local sin consultar CFE ni enviar Telegram:

```powershell
python -m tools.diagnose_environment
```

Ejecutar pruebas unitarias:

```powershell
python -m unittest discover
```

Compilar/verificar imports:

```powershell
python -m compileall cfe_api monitor
```

Ejecutar monitor una vez:

```powershell
python -m monitor.main --once
```

Ejecutar monitor para fecha especifica:

```powershell
python -m monitor.main --once --date 2026-07-01
```

La fecha usa formato `YYYY-MM-DD` y se aplica a `fecha_publicacion`.

Ejecutar monitor continuo:

```powershell
python -m monitor.main
```

Inspeccionar SQLite:

```powershell
python -m monitor.database.inspect --limit 10
```

Probar Telegram sin consultar CFE:

```powershell
python -m monitor.notifications.telegram --test
```

Enviar por Telegram el concurso mas reciente ya guardado en SQLite:

```powershell
python -m monitor.main --notify-existing-latest
```

Este comando respeta el filtro de relevancia; si el ultimo concurso no coincide, no envia Telegram.

Ejecutar dashboard local:

```powershell
python -m monitor.dashboard.app
```

Abrir:

```text
http://127.0.0.1:8000
```

Probar clima actual:

```powershell
python -m monitor.weather.open_meteo --test
```

## Sesion CFE

Flujo actual:

1. Si `.env` trae `CFE_COOKIE_HEADER` y `CFE_REQUEST_VERIFICATION_TOKEN`, se usan esos valores.
2. Si no hay valores manuales, se intenta usar `data/cfe_session.json`.
3. Si no hay cache y `CFE_BROWSER_BOOTSTRAP_ENABLED=true`, se abre Chromium con Playwright.
4. El navegador carga el portal, extrae cookies y `__RequestVerificationToken`, y guarda la cache.
5. Si CFE responde `403`, el monitor invalida la cache para renovarla.

No automatizar resolucion de captchas o validaciones visuales. Si CFE muestra una validacion interactiva, el usuario debe resolverla manualmente en la ventana del navegador.

## Dashboard

El dashboard:

- Lee datos desde SQLite.
- Muestra concursos por fecha de publicacion; por defecto usa la fecha actual.
- Permite vista de todos los concursos (`all`) o solo relevantes (`relevant`).
- Muestra conteos de totales/relevantes y grafica de publicaciones recientes.
- Muestra estado del monitor desde la tabla `monitor_status`.
- Muestra reloj, clima actual via `/api/weather` y estado WiFi.
- No debe consultar el portal CFE.
- Usa branding EEPAT desde `monitor/dashboard/static/brand/`.

Columnas actuales:

- Numero
- Entidad
- Estado
- Tipo
- Publicacion
- Descripcion

No agregar monto/proveedor al dashboard salvo que el usuario lo pida explicitamente.

APIs actuales del dashboard:

- `GET /api/concursos?date=YYYY-MM-DD&view=all|relevant&limit=100`
- `GET /api/dashboard/state`
- `POST /api/dashboard/mode/next`
- `GET /api/stats/recent-publications`
- `GET /api/system/wifi`
- `GET /api/weather`

Reglas:

- `view` solo puede ser `all` o `relevant`; la lista canonica vive en `monitor/dashboard/state.py`.
- El filtrado de `view=relevant` debe usar `monitor.filtering`, no expresiones nuevas en JS.
- JS del dashboard solo consume endpoints locales; no debe leer SQLite, CFE ni Open-Meteo directamente.

## Filtros de Relevancia

El filtro de relevancia vive en `monitor/filtering.py` y carga terminos desde:

```text
config/filters/include.txt
```

Reglas:

- Una palabra o frase por linea; lineas vacias y comentarios con `#` se ignoran.
- La comparacion normaliza minusculas, acentos y puntuacion.
- El filtro se aplica sobre `Concurso.descripcion`.
- Mantener el archivo de terminos pequeno, legible y orientado al giro electrico.
- No mover filtros a `cfe_api`; la SDK debe regresar concursos sin criterio operativo.

## Telegram

Telegram vive en `monitor/notifications/telegram.py`.

Reglas:

- Token y chat ID siempre desde `.env`.
- `send_new_concurso(concurso)` debe recibir un objeto `Concurso`, no diccionarios crudos.
- Las notificaciones automaticas del monitor deben pasar por `RelevantConcursoNotifier`.
- `RelevantConcursoNotifier` solo debe decidir relevancia y delegar el envio.
- Las notificaciones relevantes deben persistirse en `notification_outbox` antes de enviarse.
- El envio real de pendientes debe pasar por `NotificationDispatcher`.
- `python -m monitor.notifications.telegram --test` debe seguir funcionando como prueba rapida.
- `python -m monitor.main --notify-existing-latest` debe servir para probar formato con datos reales ya guardados y tambien respetar relevancia.
- No enviar Telegram para concursos no relevantes salvo que el usuario lo pida explicitamente.

## Clima

El clima vive en `monitor/weather/open_meteo.py`.

Reglas:

- Consultar solo clima actual de una ubicacion fija.
- No guardar clima en SQLite.
- No consultar clima desde `cfe_api`.
- No requerir API key.
- Si la API falla, el dashboard debe poder quedarse con placeholder.
- El dashboard debe consumir clima por `/api/weather`, no llamar Open-Meteo desde JS.

## SQLite

SQLite vive por defecto en:

```text
data/monitor.sqlite3
```

El repositorio principal es `monitor/database/repository.py`.

Reglas:

- No consultar SQLite directamente desde el dashboard fuera del repositorio/API del dashboard.
- No guardar datos historicos en archivos sueltos.
- Mantener metodos de lectura claros para casos de uso reales, como `list_recent`, `list_by_publication_date`, `count_by_publication_date`, `get_latest`.
- `monitor_status` guarda estado operativo para el dashboard; actualizarlo desde `monitor/main.py` cuando cambie la salud del monitor.

## WiFi / Sistema

El estado de WiFi vive en `monitor/system/network.py`.

Reglas:

- Debe funcionar en Windows y Linux/Raspberry Pi con degradacion segura.
- El payload debe incluir `connected`, `ssid`, `signal_percent`, `bars`, `level` y `label`.
- El dashboard usa iconos `wifi_0.svg` a `wifi_3.svg` desde `monitor/dashboard/static/wifi-icons/`.
- Si no se puede obtener SSID o senal, regresar estado desconectado/placeholder en vez de romper el dashboard.

## Estilo de Cambios

- Mantener responsabilidades separadas.
- Preferir cambios pequenos y localizados.
- No introducir frameworks nuevos sin necesidad.
- Usar `apply_patch` para ediciones manuales.
- No borrar ni revertir cambios del usuario.
- No hacer commits salvo que el usuario lo pida explicitamente.
- Antes de cerrar cambios de codigo, correr `python -m unittest discover` y `python -m compileall cfe_api monitor tools tests`.

## Futuro Cercano

Prioridades probables:

1. Robustecer ejecucion en Raspberry Pi.
2. Crear servicios `systemd` para monitor y dashboard.
3. Configurar Chromium kiosk en HDMI.
4. Implementar torreta GPIO.
5. Agregar alertas operativas sin spam para errores CFE/Telegram.
6. Agregar estadisticas historicas mas completas sobre SQLite.
