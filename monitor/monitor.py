from __future__ import annotations

import logging
from datetime import datetime

from cfe_api.core.session import CFESession
from cfe_api.models.concurso import Concurso
from cfe_api.services.concursos import ConcursosService
from monitor.database.repository import ConcursoRepository
from monitor.events import NuevoConcursoDetectado
from monitor.notifications.base import Notifier


logger = logging.getLogger(__name__)


class CFEMonitor:
    def __init__(
        self,
        concursos_service: ConcursosService,
        repository: ConcursoRepository,
        notifiers: list[Notifier] | None = None,
    ):
        self.concursos_service = concursos_service
        self.repository = repository
        self.notifiers = notifiers or []

    @classmethod
    def create(
        cls,
        db_path: str,
        notifiers: list[Notifier] | None = None,
        cfe_cookie_header: str | None = None,
        cfe_request_verification_token: str | None = None,
    ) -> "CFEMonitor":
        session = CFESession(
            cookie_header=cfe_cookie_header,
            csrf_token=cfe_request_verification_token,
        )
        session.initialize()

        repository = ConcursoRepository(db_path)
        repository.initialize()

        return cls(
            concursos_service=ConcursosService(session),
            repository=repository,
            notifiers=notifiers,
        )

    def poll(self, fecha_publicacion: str | None = None) -> list[NuevoConcursoDetectado]:
        fecha = fecha_publicacion or datetime.now().strftime("%Y-%m-%d")
        logger.info("Consultando concursos CFE para fecha_publicacion=%s", fecha)

        concursos = self.concursos_service.buscar(fecha_publicacion=fecha)
        logger.info("CFE devolvio %s concursos", len(concursos))

        nuevos = self._detect_new(concursos)
        logger.info("Concursos nuevos detectados: %s", len(nuevos))

        eventos = [
            NuevoConcursoDetectado(concurso=concurso, detectado_en=datetime.now())
            for concurso in nuevos
        ]

        for evento in eventos:
            self._emit(evento)

        return eventos

    def _detect_new(self, concursos: list[Concurso]) -> list[Concurso]:
        return self.repository.save_many(concursos)

    def _emit(self, event: NuevoConcursoDetectado) -> None:
        for notifier in self.notifiers:
            try:
                notifier.send_new_concurso(event.concurso)
            except Exception:
                logger.exception(
                    "Error notificando concurso nuevo: %s",
                    event.concurso.numero,
                )
