from dataclasses import dataclass
from datetime import datetime

from cfe_api.core.utils import parse_aspnet_date


@dataclass(slots=True)
class Concurso:
    id: int
    numero: str
    descripcion: str
    estado: str
    entidad_federativa: str
    tipo_procedimiento: str
    tipo_contratacion: str
    fecha_publicacion: datetime | None
    proveedor_adjudicado: str
    monto: float
    fecha_limite_ofertas: datetime | None
    fecha_fallo: datetime | None

    @classmethod
    def from_dict(cls, data: dict) -> "Concurso":
        """
        Construye un objeto Concurso a partir del JSON
        devuelto por el portal de CFE.
        """

        return cls(
            id=data["Id"],
            numero=data["Numero"],
            descripcion=data["Descripcion"],
            estado=data["EstadoProcedimiento"],
            entidad_federativa=data["EntidadFederativa"],
            tipo_procedimiento=data["TipoProcedimientoClave"],
            tipo_contratacion=data["TipoContratacionClave"],
            fecha_publicacion=parse_aspnet_date(data["FechaPublicacion"]),
            proveedor_adjudicado=data["NombProveedorAdjudicado"],
            monto=data["MONTO"],
            fecha_limite_ofertas=parse_aspnet_date(data["FechaLimiteOfertas"]),
            fecha_fallo=parse_aspnet_date(data["FechaFallo"]),
        )
