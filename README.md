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
MONITOR_DB_PATH=monitor.sqlite3
MONITOR_INTERVAL_SECONDS=300
MONITOR_LOG_LEVEL=INFO
```

Telegram es opcional. Si no hay credenciales, el monitor sigue funcionando sin notificaciones.

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

## Notas de arquitectura

- `cfe_api` no conoce Telegram, SQLite, dashboard, GPIO ni Raspberry Pi.
- `monitor` no conoce el protocolo HTTP interno de CFE.
- El formato JSON de CFE se encapsula en `Concurso.from_dict()`.
- El codigo de aplicacion no debe leer campos como `item["Numero"]` directamente.
- `legacy/` solo contiene material de referencia historica.
