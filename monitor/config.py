from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MonitorConfig:
    db_path: str
    interval_seconds: int
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    log_level: str

    @classmethod
    def from_env(cls) -> "MonitorConfig":
        return cls(
            db_path=os.getenv("MONITOR_DB_PATH", "monitor.sqlite3"),
            interval_seconds=_get_int("MONITOR_INTERVAL_SECONDS", 300),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            log_level=os.getenv("MONITOR_LOG_LEVEL", "INFO"),
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
