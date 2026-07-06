from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cfe_api.models.concurso import Concurso
    from cfe_api.services.concursos import ConcursosService
    from monitor.config import MonitorConfig


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LookupResult:
    numero_buscado: str
    encontrado: bool
    numero_cfe: str
    nombre_evento: str
    fecha_publicacion: str
    estado: str
    entidad_federativa: str
    resultados_cfe: int
    nota: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Resuelve nombres de eventos/concursos CFE a partir de sus numeros."
        )
    )
    parser.add_argument(
        "numeros",
        nargs="*",
        help="Numeros de evento a buscar.",
    )
    parser.add_argument(
        "-i",
        "--input-file",
        type=Path,
        help=(
            "Archivo con numeros de evento. Acepta un numero por linea o CSV simple."
        ),
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("table", "csv", "json"),
        default="table",
        help="Formato de salida. Por defecto: table.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Archivo de salida. Si se omite, imprime en consola.",
    )
    parser.add_argument(
        "--refresh-session",
        action="store_true",
        help="Invalida la cache de sesion CFE antes de consultar.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Nivel de log para stderr. Por defecto usa MONITOR_LOG_LEVEL.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from cfe_api.core.errors import CFEAPIError
    from monitor.config import MonitorConfig, load_env_file

    load_env_file()
    config = MonitorConfig.from_env()
    configure_logging(args.log_level or config.log_level)

    numeros = collect_numbers(args.numeros, args.input_file)
    if not numeros:
        raise SystemExit("No se recibieron numeros de evento para buscar.")

    if args.refresh_session:
        from monitor.cfe_session import invalidate_cached_cfe_session

        invalidate_cached_cfe_session(config)

    try:
        results = resolve_event_names(config, numeros)
    except CFEAPIError as exc:
        raise SystemExit(str(exc)) from exc

    output = format_results(results, args.format)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8-sig")
        print(f"Resultado guardado en: {args.output}")
    else:
        print(output)

    if any(not result.encontrado for result in results):
        raise SystemExit(1)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stderr,
    )


def collect_numbers(cli_numbers: list[str], input_file: Path | None) -> list[str]:
    numbers = [number.strip() for number in cli_numbers if number.strip()]

    if input_file is not None:
        numbers.extend(read_numbers_file(input_file))

    return numbers


def read_numbers_file(path: Path) -> list[str]:
    raw_text = path.read_text(encoding="utf-8-sig")
    numbers: list[str] = []

    for row in csv.reader(io.StringIO(raw_text)):
        if not row:
            continue

        first_cell = row[0].strip()
        if first_cell.startswith("#"):
            continue

        numbers.extend(cell.strip() for cell in row if cell.strip())

    return numbers


def resolve_event_names(
    config: MonitorConfig,
    numeros: list[str],
) -> list[LookupResult]:
    from cfe_api.core.errors import CFEBlockedError
    from monitor.cfe_session import invalidate_cached_cfe_session

    try:
        service = create_concursos_service(config)
        return lookup_all(service, numeros)
    except CFEBlockedError:
        invalidate_cached_cfe_session(config)

        if not can_retry_with_browser_session(config):
            raise

        logger.info("CFE bloqueo la sesion. Reintentando con sesion renovada.")
        service = create_concursos_service(config)
        return lookup_all(service, numeros)


def create_concursos_service(config: MonitorConfig) -> ConcursosService:
    from cfe_api.core.session import CFESession
    from cfe_api.services.concursos import ConcursosService
    from monitor.cfe_session import resolve_cfe_session_data

    session_data = resolve_cfe_session_data(config)
    session = CFESession(
        cookie_header=(
            session_data.cookie_header if session_data is not None else None
        ),
        csrf_token=(
            session_data.request_verification_token
            if session_data is not None
            else None
        ),
    )
    session.initialize()

    return ConcursosService(session)


def can_retry_with_browser_session(config: MonitorConfig) -> bool:
    has_manual_session = bool(
        config.cfe_cookie_header and config.cfe_request_verification_token
    )

    return config.cfe_browser_bootstrap_enabled and not has_manual_session


def lookup_all(
    service: ConcursosService,
    numeros: list[str],
) -> list[LookupResult]:
    cache: dict[str, LookupResult] = {}
    results: list[LookupResult] = []

    for numero in numeros:
        if numero not in cache:
            cache[numero] = lookup_one(service, numero)

        results.append(cache[numero])

    return results


def lookup_one(service: ConcursosService, numero: str) -> LookupResult:
    concursos = service.buscar(numero=numero)

    if not concursos:
        return empty_result(
            numero=numero,
            resultados_cfe=0,
            nota="Sin resultados en CFE.",
        )

    concurso = select_concurso(concursos, numero)

    if concurso is None:
        return empty_result(
            numero=numero,
            resultados_cfe=len(concursos),
            nota="CFE devolvio multiples resultados sin coincidencia exacta.",
        )

    note = ""
    if len(concursos) > 1:
        note = "Se uso la coincidencia exacta entre multiples resultados."

    return LookupResult(
        numero_buscado=numero,
        encontrado=True,
        numero_cfe=concurso.numero,
        nombre_evento=concurso.descripcion,
        fecha_publicacion=format_datetime(concurso.fecha_publicacion),
        estado=concurso.estado,
        entidad_federativa=concurso.entidad_federativa,
        resultados_cfe=len(concursos),
        nota=note,
    )


def select_concurso(concursos: list[Concurso], numero: str) -> Concurso | None:
    normalized_number = normalize_number(numero)
    exact_matches = [
        concurso
        for concurso in concursos
        if normalize_number(concurso.numero) == normalized_number
    ]

    if len(exact_matches) == 1:
        return exact_matches[0]

    if len(concursos) == 1:
        return concursos[0]

    return None


def normalize_number(value: str) -> str:
    return "".join(value.casefold().split())


def empty_result(
    numero: str,
    resultados_cfe: int,
    nota: str,
) -> LookupResult:
    return LookupResult(
        numero_buscado=numero,
        encontrado=False,
        numero_cfe="",
        nombre_evento="",
        fecha_publicacion="",
        estado="",
        entidad_federativa="",
        resultados_cfe=resultados_cfe,
        nota=nota,
    )


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return ""

    return value.isoformat(sep=" ", timespec="seconds")


def format_results(results: list[LookupResult], output_format: str) -> str:
    rows = [result_to_dict(result) for result in results]

    if output_format == "csv":
        return format_csv(rows)

    if output_format == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2)

    return format_table(rows)


def result_to_dict(result: LookupResult) -> dict[str, str | int | bool]:
    return {
        "numero_buscado": result.numero_buscado,
        "encontrado": result.encontrado,
        "numero_cfe": result.numero_cfe,
        "nombre_evento": result.nombre_evento,
        "fecha_publicacion": result.fecha_publicacion,
        "estado": result.estado,
        "entidad_federativa": result.entidad_federativa,
        "resultados_cfe": result.resultados_cfe,
        "nota": result.nota,
    }


def format_csv(rows: list[dict[str, str | int | bool]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=list(rows[0].keys()),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)

    return output.getvalue().rstrip()


def format_table(rows: list[dict[str, str | int | bool]]) -> str:
    columns = (
        "numero_buscado",
        "encontrado",
        "numero_cfe",
        "nombre_evento",
        "nota",
    )
    table_rows = [
        {
            column: shorten(str(row[column]), 80)
            for column in columns
        }
        for row in rows
    ]
    widths = {
        column: max(len(column), *(len(row[column]) for row in table_rows))
        for column in columns
    }
    lines = [
        " | ".join(column.ljust(widths[column]) for column in columns),
        "-+-".join("-" * widths[column] for column in columns),
    ]

    for row in table_rows:
        lines.append(
            " | ".join(row[column].ljust(widths[column]) for column in columns)
        )

    return "\n".join(lines)


def shorten(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value

    return f"{value[: max_length - 3]}..."


if __name__ == "__main__":
    main()
