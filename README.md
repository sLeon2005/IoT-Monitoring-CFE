# IoT Monitoring CFE

Sistema de monitoreo autonomo para concursos publicos de CFE.

El proyecto esta dividido en dos capas:

- `cfe_api`: SDK interna para hablar con el portal de CFE.
- `monitor`: motor de monitoreo que consume la SDK, guarda historico y emite eventos.

## Estructura

```text
cfe_api/
  core/            infraestructura HTTP, sesion y token CSRF
  models/          modelos tipados del dominio
  services/        endpoints del portal CFE
  main.py          demo manual de la SDK

monitor/
  dashboard/       dashboard web local para HDMI/kiosk
  database/        persistencia SQLite
  notifications/   notificadores externos
  config.py        configuracion desde entorno/.env
  events.py        eventos del monitor
  main.py          proceso principal
  monitor.py       orquestador del monitoreo

legacy/
  api_scan.py      script historico de ingenieria inversa

```

## Configuracion

Copia `.env.example` a `.env` y ajusta los valores necesarios:

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

Telegram es opcional. Si no hay credenciales, el monitor sigue funcionando sin notificaciones.

Probar Telegram sin consultar CFE:

```powershell
python -m monitor.notifications.telegram --test
```

Enviar un texto especifico:

```powershell
python -m monitor.notifications.telegram --test --message "Monitor CFE en linea"
```

## Ejecutar la SDK

Desde la raiz del proyecto:

```powershell
python -m cfe_api.main
```

Tambien se puede ejecutar el archivo directamente:

```powershell
python cfe_api/main.py
```

## Ejecutar el monitor

Una sola consulta para la fecha actual:

```powershell
python -m monitor.main --once
```

Una sola consulta para una fecha especifica:

```powershell
python -m monitor.main --once --date 2026-07-01
```

Modo continuo:

```powershell
python -m monitor.main
```

El monitor consulta CFE, guarda concursos en SQLite y solo emite eventos para concursos nuevos.

Probar la notificacion de concurso usando el registro mas reciente ya guardado en SQLite:

```powershell
python -m monitor.main --notify-existing-latest
```

Este comando no consulta CFE ni marca el concurso como nuevo; solo sirve para validar
el formato y envio de Telegram con datos reales.

Si CFE bloquea temporalmente la sesion HTTP con `403`, el monitor registra el estado como
`blocked`, conserva los datos historicos y reintenta en el siguiente ciclo.

Si el navegador abre el portal pero Python recibe `403`, existen dos opciones.

La opcion manual es copiar a `.env`:

```env
CFE_COOKIE_HEADER=nombre=valor; otro=valor
CFE_REQUEST_VERIFICATION_TOKEN=token_del_input_oculto
```

El token corresponde al input `__RequestVerificationToken` de la pagina de concursos.
Estos valores no deben versionarse.

La opcion automatizada usa Chromium mediante Playwright para abrir el portal, esperar el
input oculto, extraer cookies y guardar una sesion local en `data/cfe_session.json`.

Instala dependencias:

```powershell
pip install playwright
python -m playwright install chromium
```

Activa el bootstrap en `.env`:

```env
CFE_BROWSER_BOOTSTRAP_ENABLED=true
CFE_BROWSER_HEADLESS=false
CFE_SESSION_CACHE_PATH=data/cfe_session.json
CFE_BROWSER_PROFILE_DIR=data/browser-profile
```

Despues ejecuta el monitor normalmente:

```powershell
python -m monitor.main --once
```

En el primer arranque puede abrirse una ventana de Chromium. Si CFE muestra una validacion
visual, resuelvela en esa ventana; el monitor continuara cuando aparezca el token del portal.
Si la sesion cacheada vence y CFE responde `403`, el monitor borra la cache para renovarla
en el siguiente ciclo.

## Ejecutar el dashboard

El dashboard lee SQLite y no consulta CFE directamente.
Por defecto muestra solo concursos publicados hoy.
Tambien muestra el estado de conexion del monitor contra CFE.

```powershell
python -m monitor.dashboard.app
```

Luego abre:

```text
http://127.0.0.1:8000
```

En Raspberry Pi se puede abrir esa URL con Chromium en modo kiosk para mostrarla por HDMI.

El dashboard consulta clima actual mediante Open-Meteo y usa placeholder si la API falla.
La tabla de pantalla muestra solo datos operativos: numero, entidad, estado, tipo,
fecha de publicacion y descripcion.
El indicador WiFi usa `netsh` en Windows y `/proc/net/wireless` en Raspberry/Linux.

## Clima

El clima usa Open-Meteo para consultar condiciones actuales de una sola ubicacion.
No requiere API key y no guarda historico.

Probar comunicacion con la API:

```powershell
python -m monitor.weather.open_meteo --test
```

La respuesta se normaliza a un formato interno con ubicacion, temperatura, condicion e icono.
El dashboard consume esa informacion desde:

```text
/api/weather
```

## Inspeccionar SQLite

Listar concursos guardados:

```powershell
python -m monitor.database.inspect
```

Limitar la cantidad de filas:

```powershell
python -m monitor.database.inspect --limit 10
```

Usar una base especifica:

```powershell
python -m monitor.database.inspect --db data/monitor.sqlite3
```

## Notas de arquitectura

- `cfe_api` no conoce Telegram, SQLite, dashboard, GPIO ni Raspberry Pi.
- `monitor` no conoce el protocolo HTTP interno de CFE.
- El formato JSON de CFE se encapsula en `Concurso.from_dict()`.
- El codigo de aplicacion no debe leer campos como `item["Numero"]` directamente.
- `legacy/` solo contiene material de referencia historica.
