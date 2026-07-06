from __future__ import annotations

import logging

from cfe_api.models.concurso import Concurso
from monitor.filtering import KeywordTerm, match_concurso
from monitor.notifications.base import Notifier


logger = logging.getLogger(__name__)


class RelevantConcursoNotifier:
    def __init__(self, notifier: Notifier, terms: tuple[KeywordTerm, ...]):
        self.notifier = notifier
        self.terms = terms

    def send(self, message: str) -> None:
        self.notifier.send(message)

    def send_new_concurso(self, concurso: Concurso) -> None:
        result = match_concurso(concurso, self.terms)

        if not result.is_relevant:
            logger.info(
                "Concurso omitido por filtro de relevancia: %s",
                concurso.numero,
            )
            return

        logger.info(
            "Concurso relevante para notificar: %s matches=%s",
            concurso.numero,
            ", ".join(result.matches),
        )
        self.notifier.send_new_concurso(concurso)
