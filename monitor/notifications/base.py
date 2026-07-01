from __future__ import annotations

from typing import Protocol

from cfe_api.models.concurso import Concurso


class Notifier(Protocol):
    def send(self, message: str) -> None:
        ...

    def send_new_concurso(self, concurso: Concurso) -> None:
        ...
