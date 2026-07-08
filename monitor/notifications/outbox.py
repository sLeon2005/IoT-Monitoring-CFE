from __future__ import annotations

import logging

from cfe_api.models.concurso import Concurso
from monitor.database.repository import ConcursoRepository


logger = logging.getLogger(__name__)


class OutboxConcursoNotifier:
    """Encola notificaciones para entrega posterior confiable."""

    def __init__(self, repository: ConcursoRepository, channel: str):
        self.repository = repository
        self.channel = channel

    def send(self, message: str) -> None:
        raise NotImplementedError(
            "OutboxConcursoNotifier solo soporta notificaciones de concursos."
        )

    def send_new_concurso(self, concurso: Concurso) -> None:
        inserted = self.repository.enqueue_notification(
            concurso_id=concurso.id,
            channel=self.channel,
        )

        if inserted:
            logger.info(
                "Notificacion encolada para concurso %s via %s.",
                concurso.numero,
                self.channel,
            )
        else:
            logger.debug(
                "La notificacion para concurso %s via %s ya estaba en outbox.",
                concurso.numero,
                self.channel,
            )
