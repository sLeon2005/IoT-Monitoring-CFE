from __future__ import annotations

import ctypes
import json
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Protocol


DEFAULT_SYSFS_TEMP_PATHS = (
    Path("/sys/class/thermal/thermal_zone0/temp"),
    Path("/sys/class/hwmon/hwmon0/temp1_input"),
)
LINUX_UPTIME_PATH = Path("/proc/uptime")
LINUX_BOOT_ID_PATH = Path("/proc/sys/kernel/random/boot_id")
RUNTIME_STATE_KEY = "system_runtime_boots"


class RuntimeStateStore(Protocol):
    def get_monitor_value(self, key: str) -> str | None:
        ...

    def set_monitor_value(self, key: str, value: str) -> None:
        ...


def get_system_health(store: RuntimeStateStore | None = None) -> dict:
    uptime_seconds = read_current_uptime_seconds()
    boot_id = read_boot_id(uptime_seconds)
    temperature_c = read_temperature_celsius()
    total_uptime_seconds = _update_total_uptime_seconds(
        store=store,
        boot_id=boot_id,
        uptime_seconds=uptime_seconds,
    )

    return {
        "temperature_c": temperature_c,
        "uptime_seconds": uptime_seconds,
        "total_uptime_seconds": total_uptime_seconds,
    }


def read_temperature_celsius(
    sysfs_paths: tuple[Path, ...] = DEFAULT_SYSFS_TEMP_PATHS,
) -> float | None:
    sysfs_temperature = _read_sysfs_temperature(sysfs_paths)

    if sysfs_temperature is not None:
        return sysfs_temperature

    return _read_vcgencmd_temperature()


def read_current_uptime_seconds() -> float | None:
    system = platform.system().lower()

    if system == "linux":
        return _read_linux_uptime_seconds()

    if system == "windows":
        return _read_windows_uptime_seconds()

    return None


def read_boot_id(uptime_seconds: float | None) -> str | None:
    try:
        boot_id = LINUX_BOOT_ID_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        boot_id = ""

    if boot_id:
        return boot_id

    if uptime_seconds is None:
        return None

    boot_started_at = int((time.time() - uptime_seconds) // 60)
    return f"{platform.system().lower()}:{boot_started_at}"


def _update_total_uptime_seconds(
    *,
    store: RuntimeStateStore | None,
    boot_id: str | None,
    uptime_seconds: float | None,
) -> float | None:
    if store is None or boot_id is None or uptime_seconds is None:
        return uptime_seconds

    state = _load_runtime_state(store)
    boots = state.setdefault("boots", {})
    previous_boot_seconds = _safe_float(boots.get(boot_id), 0.0)
    boots[boot_id] = max(previous_boot_seconds, float(uptime_seconds))

    try:
        store.set_monitor_value(RUNTIME_STATE_KEY, json.dumps(state, sort_keys=True))
    except Exception:
        return sum(_safe_float(value, 0.0) for value in boots.values())

    return sum(_safe_float(value, 0.0) for value in boots.values())


def _load_runtime_state(store: RuntimeStateStore) -> dict:
    raw_state = store.get_monitor_value(RUNTIME_STATE_KEY)

    if not raw_state:
        return {"boots": {}}

    try:
        state = json.loads(raw_state)
    except json.JSONDecodeError:
        return {"boots": {}}

    if not isinstance(state, dict) or not isinstance(state.get("boots"), dict):
        return {"boots": {}}

    return state


def _read_sysfs_temperature(paths: tuple[Path, ...]) -> float | None:
    for path in paths:
        try:
            raw_value = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue

        try:
            value = float(raw_value)
        except ValueError:
            continue

        if abs(value) > 1000:
            value = value / 1000

        return value

    return None


def _read_vcgencmd_temperature() -> float | None:
    if shutil.which("vcgencmd") is None:
        return None

    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    match = re.search(r"temp=([+-]?\d+(?:\.\d+)?)", result.stdout)

    if match is None:
        return None

    return float(match.group(1))


def _read_linux_uptime_seconds() -> float | None:
    try:
        uptime_text = LINUX_UPTIME_PATH.read_text(encoding="utf-8").split()[0]
    except (OSError, IndexError):
        return None

    return _safe_float(uptime_text)


def _read_windows_uptime_seconds() -> float | None:
    try:
        milliseconds = ctypes.windll.kernel32.GetTickCount64()
    except (AttributeError, OSError):
        return None

    return float(milliseconds) / 1000


def _safe_float(value, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
