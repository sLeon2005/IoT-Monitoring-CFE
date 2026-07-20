from __future__ import annotations

import argparse
import csv
import math
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "temperature_log.csv"
DEFAULT_SYSFS_PATHS = (
    Path("/sys/class/thermal/thermal_zone0/temp"),
    Path("/sys/class/hwmon/hwmon0/temp1_input"),
)


@dataclass(frozen=True, slots=True)
class TemperatureReading:
    timestamp: datetime
    celsius: float
    source: str
    elapsed_seconds: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitorea temperatura del equipo en terminal para pruebas temporales."
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=60.0,
        help="Segundos entre muestras. Default: 60.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=0,
        help="Numero de muestras. 0 significa correr hasta Ctrl+C.",
    )
    parser.add_argument(
        "--source",
        choices=("auto", "sysfs", "vcgencmd"),
        default="auto",
        help="Fuente de temperatura. Default: auto.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"CSV de salida. Default: {DEFAULT_OUTPUT_PATH}.",
    )
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="No guardar CSV, solo imprimir en terminal.",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=30,
        help="Muestras recientes usadas para escalar barras ASCII. Default: 30.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Genera lecturas falsas para probar la grafica sin sensor disponible.",
    )

    args = parser.parse_args()

    if args.interval_seconds <= 0:
        parser.error("--interval-seconds debe ser mayor a 0.")

    if args.samples < 0:
        parser.error("--samples no puede ser negativo.")

    if args.window < 2:
        parser.error("--window debe ser 2 o mayor.")

    return args


def main() -> None:
    args = parse_args()

    print("Monitor temporal de temperatura")
    print("Ctrl+C para detener. CSV:", "deshabilitado" if args.no_output else args.output)
    print()

    readings: list[TemperatureReading] = []
    started_at = time.monotonic()

    try:
        sample_number = 0
        while args.samples == 0 or sample_number < args.samples:
            sample_number += 1
            elapsed = time.monotonic() - started_at
            celsius, source = read_demo_temperature(sample_number) if args.demo else read_temperature(args.source)
            reading = TemperatureReading(
                timestamp=datetime.now(),
                celsius=celsius,
                source=source,
                elapsed_seconds=elapsed,
            )
            readings.append(reading)

            if not args.no_output:
                append_csv(args.output, reading)

            print(render_reading(sample_number, reading, readings[-args.window :]))

            if args.samples != 0 and sample_number >= args.samples:
                break

            time.sleep(args.interval_seconds)
    except KeyboardInterrupt:
        print("\nMonitoreo detenido.")
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


def read_temperature(source: str) -> tuple[float, str]:
    errors: list[str] = []

    if source in {"auto", "sysfs"}:
        try:
            return read_sysfs_temperature(DEFAULT_SYSFS_PATHS)
        except RuntimeError as exc:
            errors.append(str(exc))
            if source == "sysfs":
                raise

    if source in {"auto", "vcgencmd"}:
        try:
            return read_vcgencmd_temperature()
        except RuntimeError as exc:
            errors.append(str(exc))
            if source == "vcgencmd":
                raise

    detail = " ".join(errors) if errors else "Sin fuentes configuradas."
    raise RuntimeError(
        "No pude leer temperatura del equipo. "
        "En Raspberry Pi normalmente funciona /sys/class/thermal/thermal_zone0/temp "
        "o vcgencmd measure_temp. "
        f"Detalle: {detail}"
    )


def read_sysfs_temperature(paths: Iterable[Path]) -> tuple[float, str]:
    checked: list[str] = []

    for path in paths:
        checked.append(str(path))
        if not path.exists():
            continue

        raw_value = path.read_text(encoding="utf-8").strip()
        try:
            value = float(raw_value)
        except ValueError as exc:
            raise RuntimeError(f"Valor sysfs invalido en {path}: {raw_value!r}") from exc

        if abs(value) > 1000:
            value = value / 1000

        return value, f"sysfs:{path}"

    raise RuntimeError("No encontre sensor sysfs en: " + ", ".join(checked))


def read_vcgencmd_temperature() -> tuple[float, str]:
    if shutil.which("vcgencmd") is None:
        raise RuntimeError("vcgencmd no esta disponible en PATH.")

    result = subprocess.run(
        ["vcgencmd", "measure_temp"],
        check=False,
        capture_output=True,
        text=True,
        timeout=3,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"vcgencmd fallo con codigo {result.returncode}: {stderr}")

    return parse_vcgencmd_output(result.stdout), "vcgencmd"


def parse_vcgencmd_output(output: str) -> float:
    match = re.search(r"temp=([+-]?\d+(?:\.\d+)?)", output)

    if not match:
        raise RuntimeError(f"No pude parsear salida de vcgencmd: {output!r}")

    return float(match.group(1))


def read_demo_temperature(sample_number: int) -> tuple[float, str]:
    wave = math.sin(sample_number / 3) * 1.8
    drift = min(sample_number * 0.08, 4.0)
    return round(38.0 + wave + drift, 2), "demo"


def append_csv(path: Path, reading: TemperatureReading) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0

    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if write_header:
            writer.writerow(("timestamp", "elapsed_seconds", "celsius", "source"))

        writer.writerow(
            (
                reading.timestamp.isoformat(timespec="seconds"),
                f"{reading.elapsed_seconds:.1f}",
                f"{reading.celsius:.2f}",
                reading.source,
            )
        )


def render_reading(
    sample_number: int,
    reading: TemperatureReading,
    recent_readings: list[TemperatureReading],
) -> str:
    recent_values = [sample.celsius for sample in recent_readings]
    minimum = min(recent_values)
    maximum = max(recent_values)
    span = max(maximum - minimum, 1.0)
    width = 40
    bar_length = max(1, round(((reading.celsius - minimum) / span) * width))
    bar = "#" * bar_length
    clock = reading.timestamp.strftime("%H:%M:%S")
    elapsed_min = reading.elapsed_seconds / 60

    return (
        f"muestra {sample_number:03d} | +{elapsed_min:05.1f} min | {clock} | "
        f"{reading.celsius:5.1f} C | {bar}"
    )


if __name__ == "__main__":
    main()
