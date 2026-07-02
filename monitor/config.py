from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MonitorConfig:
    db_path: str
    interval_seconds: int
    cfe_cookie_header: str | None
    cfe_request_verification_token: str | None
    cfe_session_cache_path: str
    cfe_browser_profile_dir: str
    cfe_browser_bootstrap_enabled: bool
    cfe_browser_headless: bool
    cfe_browser_timeout_ms: int
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    log_level: str
    dashboard_host: str
    dashboard_port: int
    dashboard_refresh_seconds: int
    weather_enabled: bool
    weather_location_name: str
    weather_latitude: float
    weather_longitude: float
    weather_refresh_seconds: int
    weather_timeout_seconds: int

    @classmethod
    def from_env(cls) -> "MonitorConfig":
        return cls(
            db_path=os.getenv("MONITOR_DB_PATH", "data/monitor.sqlite3"),
            interval_seconds=_get_int("MONITOR_INTERVAL_SECONDS", 300),
            cfe_cookie_header=os.getenv("CFE_COOKIE_HEADER"),
            cfe_request_verification_token=os.getenv("CFE_REQUEST_VERIFICATION_TOKEN"),
            cfe_session_cache_path=os.getenv(
                "CFE_SESSION_CACHE_PATH",
                "data/cfe_session.json",
            ),
            cfe_browser_profile_dir=os.getenv(
                "CFE_BROWSER_PROFILE_DIR",
                "data/browser-profile",
            ),
            cfe_browser_bootstrap_enabled=_get_bool(
                "CFE_BROWSER_BOOTSTRAP_ENABLED",
                False,
            ),
            cfe_browser_headless=_get_bool("CFE_BROWSER_HEADLESS", False),
            cfe_browser_timeout_ms=_get_int("CFE_BROWSER_TIMEOUT_MS", 60000),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            log_level=os.getenv("MONITOR_LOG_LEVEL", "INFO"),
            dashboard_host=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
            dashboard_port=_get_int("DASHBOARD_PORT", 8000),
            dashboard_refresh_seconds=_get_int("DASHBOARD_REFRESH_SECONDS", 30),
            weather_enabled=_get_bool("WEATHER_ENABLED", True),
            weather_location_name=os.getenv("WEATHER_LOCATION_NAME", "Tampico"),
            weather_latitude=_get_float("WEATHER_LATITUDE", 22.2372),
            weather_longitude=_get_float("WEATHER_LONGITUDE", -97.87),
            weather_refresh_seconds=_get_int("WEATHER_REFRESH_SECONDS", 900),
            weather_timeout_seconds=_get_int("WEATHER_TIMEOUT_SECONDS", 10),
        )

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)


def load_env_file(path: str | Path = ".env") -> None:
    env_path = Path(path)

    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        clean_line = line.strip()

        if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
            continue

        key, value = clean_line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _get_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un entero.") from exc


def _get_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()

    if normalized in {"1", "true", "yes", "y", "on"}:
        return True

    if normalized in {"0", "false", "no", "n", "off"}:
        return False

    raise ValueError(f"{name} debe ser booleano: true/false.")


def _get_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser numerico.") from exc
