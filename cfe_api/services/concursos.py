from cfe_api.core.session import CFESession
from cfe_api.models.concurso import Concurso


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
    ):

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

        return [Concurso.from_dict(item) for item in response.json()]
