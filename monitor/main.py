from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime

from monitor.config import MonitorConfig, load_env_file
from monitor.monitor import CFEMonitor
from monitor.notifications.telegram import TelegramNotifier


logger = logging.getLogger(__name__)


def build_notifiers(config: MonitorConfig):
    if config.telegram_enabled:
        return [
            TelegramNotifier(
                bot_token=config.telegram_bot_token,
                chat_id=config.telegram_chat_id,
            )
        ]

    logger.info("Telegram deshabilitado: faltan credenciales.")
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor de concursos CFE.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Ejecuta una sola consulta y termina.",
    )
    parser.add_argument(
        "--date",
        dest="fecha_publicacion",
        type=parse_date,
        help="Fecha de publicacion a consultar en formato YYYY-MM-DD.",
    )

    return parser.parse_args()


def parse_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "La fecha debe tener formato YYYY-MM-DD."
        ) from exc

    return value


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def main() -> None:
    load_env_file()
    args = parse_args()
    config = MonitorConfig.from_env()
    configure_logging(config.log_level)

    logger.info("Iniciando monitor CFE")
    logger.info("Base SQLite: %s", config.db_path)
    logger.info("Intervalo: %s segundos", config.interval_seconds)
    monitor: CFEMonitor | None = None

    while True:
        if monitor is None:
            try:
                monitor = CFEMonitor.create(
                    db_path=config.db_path,
                    notifiers=build_notifiers(config),
                )
                logger.info("Sesion CFE inicializada correctamente.")
            except Exception:
                logger.exception("No fue posible inicializar la sesion CFE.")

                if args.once:
                    break

                time.sleep(config.interval_seconds)
                continue

        try:
            eventos = monitor.poll(fecha_publicacion=args.fecha_publicacion)
            logger.info("Ciclo completado. Eventos emitidos: %s", len(eventos))
        except Exception:
            logger.exception("Error durante el ciclo de monitoreo.")
            monitor = None

        if args.once:
            break

        time.sleep(config.interval_seconds)


if __name__ == "__main__":
    main()
