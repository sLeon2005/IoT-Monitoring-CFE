from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from cfe_api.models.concurso import Concurso


@dataclass(slots=True)
class NuevoConcursoDetectado:
    concurso: Concurso
    detectado_en: datetime
