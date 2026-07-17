from __future__ import annotations

import logging

from cfe_api.models.concurso import Concurso
from monitor.filtering import KeywordTerm, KeywordTermStore, match_concurso
from monitor.notifications.base import Notifier


logger = logging.getLogger(__name__)


class RelevantConcursoNotifier:
    def __init__(
        self,
        notifier: Notifier,
        terms: tuple[KeywordTerm, ...] | None = None,
        term_store: KeywordTermStore | None = None,
    ):
        self.notifier = notifier
        self.terms = terms or ()
        self.term_store = term_store
        self.evaluated_count = 0
        self.relevant_count = 0
        self.omitted_count = 0

    def send(self, message: str) -> None:
        self.notifier.send(message)

    def send_new_concurso(self, concurso: Concurso) -> None:
        self.evaluated_count += 1
        result = match_concurso(concurso, self._get_terms())

        if not result.is_relevant:
            self.omitted_count += 1
            return

        self.relevant_count += 1
        self.notifier.send_new_concurso(concurso)

    def _get_terms(self) -> tuple[KeywordTerm, ...]:
        if self.term_store is not None:
            return self.term_store.get_terms()

        return self.terms

    def flush_summary(self) -> None:
        if self.evaluated_count == 0:
            return

        logger.info("Filtro de relevancia - concursos evaluados: %s", self.evaluated_count)
        logger.info("Filtro de relevancia - concursos relevantes: %s", self.relevant_count)
        logger.info(
            "Filtro de relevancia - concursos omitidos para notificacion: %s",
            self.omitted_count,
        )
        self.evaluated_count = 0
        self.relevant_count = 0
        self.omitted_count = 0
