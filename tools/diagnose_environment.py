from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from monitor.config import MonitorConfig, load_env_file
from monitor.filtering import DEFAULT_INCLUDE_KEYWORDS_PATH, load_keyword_terms


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 10)


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    status: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnostica el entorno local del monitor CFE sin consultar CFE."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime el resultado en JSON para automatizaciones.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = run_checks()

    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        print_human_results(results)

    if any(result.status == "fail" for result in results):
        raise SystemExit(1)


def run_checks() -> list[CheckResult]:
    load_env_file(PROJECT_ROOT / ".env")

    results = [
        check_python_version(),
        check_required_imports(),
        check_env_files(),
        check_config(),
        check_cfe_session_config(),
        check_filter_terms(),
        check_database_path(),
        check_playwright_browser_hint(),
    ]

    return results


def check_python_version() -> CheckResult:
    current = sys.version_info[:3]
    current_text = ".".join(str(part) for part in current)
    minimum_text = ".".join(str(part) for part in MIN_PYTHON)

    if current < MIN_PYTHON:
        return CheckResult(
            "python",
            "fail",
            f"Python {current_text}; se requiere {minimum_text} o superior.",
        )

    return CheckResult("python", "ok", f"Python {current_text} en {platform.system()}.")


def check_required_imports() -> CheckResult:
    missing = [
        module
        for module in ("requests", "bs4")
        if importlib.util.find_spec(module) is None
    ]

    if missing:
        return CheckResult(
            "dependencies",
            "fail",
            "Faltan dependencias: "
            + ", ".join(missing)
            + ". Ejecuta: python -m pip install -r requirements.txt",
        )

    return CheckResult("dependencies", "ok", "Dependencias base disponibles.")


def check_env_files() -> CheckResult:
    env_example = PROJECT_ROOT / ".env.example"
    env_file = PROJECT_ROOT / ".env"

    if not env_example.exists():
        return CheckResult("env", "fail", "Falta .env.example.")

    if not env_file.exists():
        return CheckResult(
            "env",
            "warn",
            "No existe .env. Copia .env.example a .env para ejecucion local.",
        )

    return CheckResult("env", "ok", ".env y .env.example presentes.")


def check_config() -> CheckResult:
    try:
        MonitorConfig.from_env()
    except ValueError as exc:
        return CheckResult("config", "fail", str(exc))

    return CheckResult("config", "ok", "Configuracion parsea correctamente.")


def check_cfe_session_config() -> CheckResult:
    config = MonitorConfig.from_env()
    has_cookie = bool(config.cfe_cookie_header)
    has_token = bool(config.cfe_request_verification_token)

    if has_cookie != has_token:
        return CheckResult(
            "cfe_session",
            "fail",
            "CFE_COOKIE_HEADER y CFE_REQUEST_VERIFICATION_TOKEN deben configurarse juntos.",
        )

    if has_cookie and has_token:
        return CheckResult(
            "cfe_session",
            "ok",
            "Sesion CFE manual configurada en .env.",
        )

    if Path(config.cfe_session_cache_path).exists():
        return CheckResult(
            "cfe_session",
            "ok",
            f"Cache de sesion CFE encontrada en {config.cfe_session_cache_path}.",
        )

    if config.cfe_browser_bootstrap_enabled:
        return CheckResult(
            "cfe_session",
            "warn",
            "Sin sesion manual/cache; se intentara bootstrap con navegador al consultar CFE.",
        )

    return CheckResult(
        "cfe_session",
        "warn",
        "Sin sesion manual/cache y bootstrap deshabilitado; CFE puede bloquear la sesion directa.",
    )


def check_filter_terms() -> CheckResult:
    if not DEFAULT_INCLUDE_KEYWORDS_PATH.exists():
        return CheckResult(
            "filters",
            "fail",
            f"Falta archivo de filtros: {DEFAULT_INCLUDE_KEYWORDS_PATH}.",
        )

    terms = load_keyword_terms()

    if not terms:
        return CheckResult("filters", "warn", "El filtro de relevancia no tiene terminos.")

    return CheckResult("filters", "ok", f"{len(terms)} terminos de relevancia cargados.")


def check_database_path() -> CheckResult:
    config = MonitorConfig.from_env()
    db_path = Path(config.db_path)
    db_parent = db_path.parent

    if db_parent.exists():
        return CheckResult("database", "ok", f"Directorio SQLite listo: {db_parent}.")

    return CheckResult(
        "database",
        "warn",
        f"Directorio SQLite no existe aun: {db_parent}. El monitor lo creara al iniciar.",
    )


def check_playwright_browser_hint() -> CheckResult:
    config = MonitorConfig.from_env()

    if importlib.util.find_spec("playwright") is None:
        if config.cfe_browser_bootstrap_enabled:
            return CheckResult(
                "playwright",
                "fail",
                "Bootstrap CFE esta habilitado pero Playwright no esta instalado.",
            )

        return CheckResult(
            "playwright",
            "warn",
            "Playwright no esta instalado; solo hace falta si usas bootstrap por navegador.",
        )

    if config.cfe_browser_bootstrap_enabled:
        return CheckResult(
            "playwright",
            "ok",
            "Playwright instalado. Verifica Chromium con: python -m playwright install chromium",
        )

    return CheckResult(
        "playwright",
        "ok",
        "Playwright instalado; bootstrap por navegador esta deshabilitado.",
    )


def print_human_results(results: list[CheckResult]) -> None:
    labels = {
        "ok": "OK",
        "warn": "WARN",
        "fail": "FAIL",
    }

    print("Diagnostico de entorno IoT Monitoring CFE\n")

    for result in results:
        print(f"[{labels[result.status]}] {result.name}: {result.message}")


if __name__ == "__main__":
    main()
