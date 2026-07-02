from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import requests

from monitor.config import MonitorConfig, load_env_file


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    enabled: bool
    provider: str
    location: str
    temperature_c: float | None
    condition: str
    icon: str
    observed_at: str | None
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OpenMeteoClient:
    def __init__(
        self,
        *,
        latitude: float,
        longitude: float,
        location_name: str,
        timeout_seconds: int = 10,
    ):
        self.latitude = latitude
        self.longitude = longitude
        self.location_name = location_name
        self.timeout_seconds = timeout_seconds

    def get_current_weather(self) -> WeatherSnapshot:
        response = requests.get(
            OPEN_METEO_FORECAST_URL,
            params={
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": "temperature_2m,weather_code,is_day",
                "timezone": "auto",
                "forecast_days": 1,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        current = payload.get("current") or {}
        weather_code = _safe_int(current.get("weather_code"))
        temperature = _safe_float(current.get("temperature_2m"))
        condition = describe_weather_code(weather_code)

        return WeatherSnapshot(
            enabled=True,
            provider="open_meteo",
            location=self.location_name,
            temperature_c=temperature,
            condition=condition,
            icon=icon_for_weather_code(weather_code),
            observed_at=current.get("time"),
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )


def get_configured_weather(config: MonitorConfig) -> WeatherSnapshot:
    if not config.weather_enabled:
        return weather_disabled_snapshot(config.weather_location_name)

    client = OpenMeteoClient(
        latitude=config.weather_latitude,
        longitude=config.weather_longitude,
        location_name=config.weather_location_name,
        timeout_seconds=config.weather_timeout_seconds,
    )

    return client.get_current_weather()


def weather_disabled_snapshot(location: str) -> WeatherSnapshot:
    return WeatherSnapshot(
        enabled=False,
        provider="open_meteo",
        location=location,
        temperature_c=None,
        condition="Clima pendiente",
        icon="unknown",
        observed_at=None,
        updated_at=datetime.now().isoformat(timespec="seconds"),
    )


def describe_weather_code(code: int | None) -> str:
    if code is None:
        return "Clima no disponible"

    if code == 0:
        return "Despejado"

    if code in {1, 2}:
        return "Parcialmente nublado"

    if code == 3:
        return "Nublado"

    if code in {45, 48}:
        return "Niebla"

    if code in {51, 53, 55, 56, 57}:
        return "Llovizna"

    if code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "Lluvia"

    if code in {71, 73, 75, 77, 85, 86}:
        return "Nieve"

    if code in {95, 96, 99}:
        return "Tormenta"

    return "Clima no disponible"


def icon_for_weather_code(code: int | None) -> str:
    if code is None:
        return "unknown"

    if code == 0:
        return "sunny"

    if code in {1, 2}:
        return "partly-cloudy"

    if code == 3:
        return "cloudy"

    if code in {45, 48}:
        return "fog"

    if code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
        return "rain"

    if code in {95, 96, 99}:
        return "storm"

    return "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cliente Open-Meteo del monitor CFE.")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Consulta Open-Meteo y muestra el clima actual configurado.",
    )

    return parser.parse_args()


def main() -> None:
    load_env_file()
    args = parse_args()

    if not args.test:
        raise SystemExit("Usa --test para consultar el clima configurado.")

    config = MonitorConfig.from_env()
    snapshot = get_configured_weather(config)
    print(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False))


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
