from __future__ import annotations

import logging
from dataclasses import dataclass

from monitor.database.repository import ConcursoRepository
from monitor.filtering import KeywordTerm, match_concurso


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NotificationReconcileResult:
    evaluated: int
    relevant: int
    enqueued: int
    already_queued: int


def reconcile_relevant_notifications(
    *,
    repository: ConcursoRepository,
    terms: tuple[KeywordTerm, ...],
    channel: str = "telegram",
) -> NotificationReconcileResult:
    """Ensure every currently relevant stored concurso has an outbox row."""

    evaluated = 0
    relevant = 0
    enqueued = 0
    already_queued = 0

    for concurso in repository.list_all_concursos():
        evaluated += 1

        if not match_concurso(concurso, terms).is_relevant:
            continue

        relevant += 1

        if repository.enqueue_notification(concurso_id=concurso.id, channel=channel):
            enqueued += 1
        else:
            already_queued += 1

    if enqueued > 0:
        logger.info(
            "Conciliacion de notificaciones %s: %s concursos relevantes encolados.",
            channel,
            enqueued,
        )

    return NotificationReconcileResult(
        evaluated=evaluated,
        relevant=relevant,
        enqueued=enqueued,
        already_queued=already_queued,
    )
