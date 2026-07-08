from __future__ import annotations

from typing import TYPE_CHECKING, Any

from cfe_api.core.errors import CFEAPIError, CFEBlockedError
from cfe_api.core.utils import looks_like_waf_block, response_snippet
from cfe_api.models.concurso import Concurso

if TYPE_CHECKING:
    from cfe_api.core.session import CFESession


class ConcursosService:

    ENDPOINT = (
        "https://msc.cfe.mx/Aplicaciones/NCFE/" "Concursos/Procedure/getProcBusqueda"
    )

    def __init__(self, session: CFESession):
        self.session = session

    def buscar(
        self,
        fecha_publicacion: str | None = None,
        numero: str | None = None,
        descripcion: str | None = None,
    ) -> list[Concurso]:

        # Replica el payload enviado por el portal de CFE.
        # Solo modificamos la fecha; el resto son los valores por defecto.
        payload = {
            "__RequestVerificationToken": self.session.token,
            "TipoProcedimientoClave": "",
            "TipoContratacionClave": "",
            "IdEntidadFederativa": "0",
            "Numero": numero or "",
            "Descripcion": descripcion or "",
            "EstadoProcedimientoContratacionClave": "0",
            "FechaPublicacion": fecha_publicacion or "",
            "FechaPublicacionIni": "",
            "FechaPublicacionFin": "",
            "TestigoSocial": "2",
            "idCaracterProcedimiento": "0",
            "Modalidad": "0",
        }

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.session.HOME_URL,
        }

        response = self.session.post(
            self.ENDPOINT,
            data=payload,
            headers=headers,
        )

        self.session._raise_for_status(response, "consultar concursos")

        return _parse_concursos_response(response)


def _parse_concursos_response(response: Any) -> list[Concurso]:
    body = response.text

    if looks_like_waf_block(body):
        raise CFEBlockedError(
            "CFE devolvio una respuesta de bloqueo al consultar concursos. "
            f"Respuesta: {response_snippet(body)}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise CFEAPIError(
            "CFE no devolvio JSON valido al consultar concursos. "
            f"Content-Type: {response.headers.get('Content-Type', '')}. "
            f"Respuesta: {response_snippet(body)}"
        ) from exc

    if not isinstance(payload, list):
        raise CFEAPIError(
            "CFE devolvio un JSON inesperado al consultar concursos. "
            f"Se esperaba una lista y se recibio {type(payload).__name__}."
        )

    concursos: list[Concurso] = []

    for index, item in enumerate(payload):
        try:
            concursos.append(Concurso.from_dict(item))
        except ValueError as exc:
            raise CFEAPIError(
                "CFE devolvio un concurso con formato invalido "
                f"en la posicion {index}: {exc}"
            ) from exc

    return concursos
