from __future__ import annotations

import platform
import re
import subprocess
import unicodedata
from pathlib import Path


def get_wifi_status() -> dict:
    system = platform.system().lower()

    if system == "windows":
        return _get_windows_wifi_status()

    if system == "linux":
        return _get_linux_wifi_status()

    return _disconnected_status("Sistema no soportado")


def _get_windows_wifi_status() -> dict:
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            encoding="cp850",
            errors="ignore",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return _disconnected_status("WiFi no disponible")

    values = _parse_netsh_values(result.stdout)
    signal_text = (
        values.get("signal")
        or values.get("senal")
        or _find_signal_value(values)
    )

    if signal_text is None:
        return _disconnected_status("Sin senal")

    signal_match = re.search(r"(\d+)", signal_text)

    if signal_match is None:
        return _disconnected_status("Sin senal")

    signal_percent = int(signal_match.group(1))
    ssid = values.get("ssid")

    return _connected_status(signal_percent, ssid)


def _parse_netsh_values(output: str) -> dict[str, str]:
    values = {}

    for line in output.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        values[_normalize_key(key)] = value.strip()

    return values


def _normalize_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", "_", ascii_value.strip().lower())


def _find_signal_value(values: dict[str, str]) -> str | None:
    for key, value in values.items():
        if key.startswith("se") and "%" in value:
            return value

    return None


def _get_linux_wifi_status() -> dict:
    wireless_path = Path("/proc/net/wireless")

    if not wireless_path.exists():
        return _disconnected_status("WiFi no disponible")

    lines = wireless_path.read_text(encoding="utf-8", errors="ignore").splitlines()

    for line in lines[2:]:
        if ":" not in line:
            continue

        interface, data = line.split(":", 1)
        fields = data.split()

        if len(fields) < 3:
            continue

        try:
            quality = float(fields[1].strip("."))
        except ValueError:
            continue

        interface_name = interface.strip()
        signal_percent = round(max(0, min(100, quality / 70 * 100)))
        return _connected_status(signal_percent, _get_linux_ssid(interface_name))

    return _disconnected_status("Sin senal")


def _get_linux_ssid(interface: str) -> str | None:
    ssid = _run_linux_ssid_command(["iwgetid", interface, "--raw"])

    if ssid:
        return ssid

    nmcli_output = _run_linux_ssid_command(
        ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"]
    )

    if not nmcli_output:
        return None

    for line in nmcli_output.splitlines():
        active, _, ssid = line.partition(":")

        if active == "yes" and ssid:
            return ssid.replace(r"\:", ":")

    return None


def _run_linux_ssid_command(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    return result.stdout.strip() or None


def _connected_status(signal_percent: int, ssid: str | None) -> dict:
    level = _level_for_signal(signal_percent)

    return {
        "connected": signal_percent > 0,
        "ssid": ssid,
        "signal_percent": signal_percent,
        "bars": _bars_for_signal(signal_percent),
        "level": level,
        "label": _label_for_level(level),
    }


def _disconnected_status(label: str) -> dict:
    return {
        "connected": False,
        "ssid": None,
        "signal_percent": None,
        "bars": 0,
        "level": "none",
        "label": label,
    }


def _bars_for_signal(signal_percent: int) -> int:
    if signal_percent >= 70:
        return 3

    if signal_percent >= 35:
        return 2

    if signal_percent > 0:
        return 1

    return 0


def _level_for_signal(signal_percent: int) -> str:
    if signal_percent >= 70:
        return "good"

    if signal_percent >= 35:
        return "warning"

    if signal_percent > 0:
        return "poor"

    return "none"


def _label_for_level(level: str) -> str:
    labels = {
        "good": "WiFi estable",
        "warning": "WiFi medio",
        "poor": "WiFi debil",
        "none": "Sin senal",
    }

    return labels[level]
