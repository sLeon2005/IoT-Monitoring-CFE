from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from monitor.database.repository import ConcursoRepository
from monitor.notifications.base import Notifier


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NotificationDispatchResult:
    attempted: int
    sent: int
    failed: int
    pending: int
    permanently_failed: int


class NotificationDispatcher:
    def __init__(
        self,
        *,
        repository: ConcursoRepository,
        notifier: Notifier,
        channel: str,
        batch_limit: int = 20,
        max_attempts: int = 10,
    ):
        self.repository = repository
        self.notifier = notifier
        self.channel = channel
        self.batch_limit = batch_limit
        self.max_attempts = max_attempts

    def dispatch_due(self) -> NotificationDispatchResult:
        now = datetime.now()
        pending_items = self.repository.list_due_notifications(
            channel=self.channel,
            due_at=now,
            limit=self.batch_limit,
        )
        sent = 0
        failed = 0

        for item in pending_items:
            try:
                self.notifier.send_new_concurso(item.concurso)
            except Exception as exc:
                failed += 1
                attempt_number = item.attempts + 1
                final = attempt_number >= self.max_attempts
                next_attempt_at = now + _retry_delay(attempt_number)
                self.repository.mark_notification_failed(
                    item.id,
                    error_message=_safe_error_message(exc),
                    next_attempt_at=next_attempt_at,
                    final=final,
                )
                logger.warning(
                    "No fue posible enviar notificacion %s via %s "
                    "(intento %s/%s).",
                    item.id,
                    self.channel,
                    attempt_number,
                    self.max_attempts,
                )
                continue

            self.repository.mark_notification_sent(item.id)
            sent += 1
            logger.info(
                "Notificacion %s enviada via %s para concurso %s.",
                item.id,
                self.channel,
                item.concurso.numero,
            )

        statuses = self.repository.count_notifications_by_status(self.channel)

        return NotificationDispatchResult(
            attempted=len(pending_items),
            sent=sent,
            failed=failed,
            pending=statuses.get("pending", 0),
            permanently_failed=statuses.get("failed", 0),
        )


def _retry_delay(attempt_number: int) -> timedelta:
    minutes_by_attempt = (1, 5, 15, 60, 360)
    index = min(max(attempt_number, 1), len(minutes_by_attempt)) - 1

    return timedelta(minutes=minutes_by_attempt[index])


def _safe_error_message(exc: Exception) -> str:
    message = " ".join(str(exc).split())

    if not message:
        return exc.__class__.__name__

    return message
