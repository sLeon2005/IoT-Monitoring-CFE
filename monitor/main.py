from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime

from cfe_api.core.errors import CFEAPIError, CFEBlockedError
from monitor.cfe_session import invalidate_cached_cfe_session, resolve_cfe_session_data
from monitor.config import MonitorConfig, load_env_file
from monitor.database.repository import ConcursoRepository
from monitor.filtering import load_keyword_terms, match_concurso
from monitor.monitor import CFEMonitor
from monitor.notifications.dispatcher import (
    NotificationDispatcher,
    NotificationDispatchResult,
)
from monitor.notifications.outbox import OutboxConcursoNotifier
from monitor.notifications.relevant import RelevantConcursoNotifier
from monitor.notifications.telegram import TelegramNotifier


logger = logging.getLogger(__name__)


def build_notifiers(
    config: MonitorConfig,
    repository: ConcursoRepository,
):
    if config.telegram_enabled:
        keyword_terms = load_keyword_terms()
        outbox_notifier = OutboxConcursoNotifier(
            repository=repository,
            channel="telegram",
        )
        return [
            RelevantConcursoNotifier(
                notifier=outbox_notifier,
                terms=keyword_terms,
            )
        ]

    logger.info("Telegram deshabilitado: faltan credenciales.")
    return []


def build_notification_dispatcher(
    config: MonitorConfig,
    repository: ConcursoRepository,
) -> NotificationDispatcher | None:
    if not config.telegram_enabled:
        return None

    telegram_notifier = TelegramNotifier(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
    )

    return NotificationDispatcher(
        repository=repository,
        notifier=telegram_notifier,
        channel="telegram",
    )


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
    parser.add_argument(
        "--notify-existing-latest",
        action="store_true",
        help="Envia por Telegram el concurso mas reciente guardado en SQLite.",
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
    repository = ConcursoRepository(config.db_path)
    repository.initialize()

    if args.notify_existing_latest:
        notify_existing_latest(repository, config)
        return

    notification_dispatcher = build_notification_dispatcher(config, repository)
    retried_with_browser_session = False

    while True:
        pre_poll_dispatch = dispatch_pending_notifications(notification_dispatcher)

        if monitor is None:
            try:
                cfe_session_data = resolve_cfe_session_data(config)
                monitor = CFEMonitor.create(
                    db_path=config.db_path,
                    notifiers=build_notifiers(config, repository),
                    cfe_cookie_header=(
                        cfe_session_data.cookie_header
                        if cfe_session_data is not None
                        else None
                    ),
                    cfe_request_verification_token=(
                        cfe_session_data.request_verification_token
                        if cfe_session_data is not None
                        else None
                    ),
                )
                logger.info("Sesion CFE inicializada correctamente.")
                repository.set_monitor_status(
                    "connected",
                    "Sesion CFE inicializada correctamente.",
                )
            except CFEBlockedError as exc:
                logger.warning("CFE bloqueo la sesion HTTP: %s", exc)
                invalidate_cached_cfe_session(config)

                if _can_retry_with_browser_session(config, retried_with_browser_session):
                    retried_with_browser_session = True
                    logger.info("Reintentando con una sesion CFE renovada por navegador.")
                    continue

                repository.set_monitor_status(
                    "blocked",
                    "CFE bloqueo la sesion HTTP. Se reintentara despues.",
                )

                if args.once:
                    break

                time.sleep(config.interval_seconds)
                continue
            except CFEAPIError as exc:
                logger.warning("Error esperado al inicializar CFE: %s", exc)
                repository.set_monitor_status("error", str(exc))

                if args.once:
                    break

                time.sleep(config.interval_seconds)
                continue
            except Exception:
                logger.exception("No fue posible inicializar la sesion CFE.")
                repository.set_monitor_status(
                    "error",
                    "No fue posible inicializar la sesion CFE.",
                )

                if args.once:
                    break

                time.sleep(config.interval_seconds)
                continue

        try:
            eventos = monitor.poll(fecha_publicacion=args.fecha_publicacion)
            post_poll_dispatch = dispatch_pending_notifications(notification_dispatcher)
            dispatch_result = post_poll_dispatch or pre_poll_dispatch
            status_message = _cycle_status_message(len(eventos), dispatch_result)
            logger.info(status_message)
            retried_with_browser_session = False
            repository.set_monitor_status(
                "ok",
                status_message,
            )
        except CFEBlockedError as exc:
            logger.warning("CFE bloqueo la consulta HTTP: %s", exc)
            invalidate_cached_cfe_session(config)
            monitor = None

            if _can_retry_with_browser_session(config, retried_with_browser_session):
                retried_with_browser_session = True
                logger.info("Reintentando con una sesion CFE renovada por navegador.")
                continue

            repository.set_monitor_status(
                "blocked",
                "CFE bloqueo la consulta HTTP. Se reintentara despues.",
            )
        except CFEAPIError as exc:
            logger.warning("Error esperado durante consulta CFE: %s", exc)
            repository.set_monitor_status("error", str(exc))
            monitor = None
        except Exception:
            logger.exception("Error durante el ciclo de monitoreo.")
            repository.set_monitor_status(
                "error",
                "Error durante el ciclo de monitoreo.",
            )
            monitor = None

        if args.once:
            break

        time.sleep(config.interval_seconds)


def _can_retry_with_browser_session(
    config: MonitorConfig,
    retry_used: bool,
) -> bool:
    has_manual_session = bool(
        config.cfe_cookie_header and config.cfe_request_verification_token
    )

    return (
        config.cfe_browser_bootstrap_enabled
        and not retry_used
        and not has_manual_session
    )


def dispatch_pending_notifications(
    dispatcher: NotificationDispatcher | None,
) -> NotificationDispatchResult | None:
    if dispatcher is None:
        return None

    try:
        result = dispatcher.dispatch_due()
    except Exception:
        logger.exception("Error despachando notificaciones pendientes.")
        return None

    if result.attempted > 0:
        logger.info(
            "Notificaciones Telegram procesadas: %s enviadas, %s fallidas, "
            "%s pendientes.",
            result.sent,
            result.failed,
            result.pending,
        )

    return result


def _cycle_status_message(
    event_count: int,
    dispatch_result: NotificationDispatchResult | None,
) -> str:
    message = f"Ciclo completado. Eventos emitidos: {event_count}."

    if dispatch_result is None:
        return message

    if (
        dispatch_result.attempted == 0
        and dispatch_result.pending == 0
        and dispatch_result.permanently_failed == 0
    ):
        return message

    return (
        f"{message} Telegram: {dispatch_result.sent} enviadas, "
        f"{dispatch_result.failed} fallidas, "
        f"{dispatch_result.pending} pendientes, "
        f"{dispatch_result.permanently_failed} fallidas permanentes."
    )


def notify_existing_latest(
    repository: ConcursoRepository,
    config: MonitorConfig,
) -> None:
    if not config.telegram_enabled:
        raise SystemExit(
            "Telegram no esta configurado. Revisa TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID."
        )

    concurso = repository.get_latest()

    if concurso is None:
        raise SystemExit("No hay concursos guardados en SQLite para notificar.")

    keyword_terms = load_keyword_terms()
    filter_result = match_concurso(concurso, keyword_terms)

    if not filter_result.is_relevant:
        raise SystemExit(
            "El concurso mas reciente no coincide con el filtro de relevancia. "
            "No se envio Telegram."
        )

    notifier = TelegramNotifier(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id,
    )
    notifier.send_new_concurso(concurso)
    print(f"Concurso existente enviado por Telegram: {concurso.numero}")


if __name__ == "__main__":
    main()
