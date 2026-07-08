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

        if not isinstance(data, dict):
            raise ValueError("El concurso CFE debe ser un objeto JSON.")

        return cls(
            id=_get_required_int(data, "Id"),
            numero=_get_required_text(data, "Numero"),
            descripcion=_get_required_text(data, "Descripcion"),
            estado=_get_text(data, "EstadoProcedimiento"),
            entidad_federativa=_get_text(data, "EntidadFederativa"),
            tipo_procedimiento=_get_text(data, "TipoProcedimientoClave"),
            tipo_contratacion=_get_text(data, "TipoContratacionClave"),
            fecha_publicacion=parse_aspnet_date(
                _get_optional_text(data, "FechaPublicacion")
            ),
            proveedor_adjudicado=_get_text(data, "NombProveedorAdjudicado"),
            monto=_get_float(data, "MONTO"),
            fecha_limite_ofertas=parse_aspnet_date(
                _get_optional_text(data, "FechaLimiteOfertas")
            ),
            fecha_fallo=parse_aspnet_date(_get_optional_text(data, "FechaFallo")),
        )


def _get_required_text(data: dict, key: str) -> str:
    value = data.get(key)

    if value is None:
        raise ValueError(f"CFE no devolvio el campo requerido {key}.")

    text = str(value).strip()

    if not text:
        raise ValueError(f"CFE devolvio vacio el campo requerido {key}.")

    return text


def _get_optional_text(data: dict, key: str) -> str | None:
    value = data.get(key)

    if value is None:
        return None

    text = str(value).strip()

    return text or None


def _get_text(data: dict, key: str) -> str:
    return _get_optional_text(data, key) or ""


def _get_required_int(data: dict, key: str) -> int:
    value = data.get(key)

    if value is None or value == "":
        raise ValueError(f"CFE no devolvio el campo requerido {key}.")

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"CFE devolvio {key} con formato invalido.") from exc


def _get_float(data: dict, key: str) -> float:
    value = data.get(key)

    if value in (None, ""):
        return 0.0

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return 0.0

        if "," in value and "." not in value:
            value = value.replace(",", ".")
        else:
            value = value.replace(",", "")

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"CFE devolvio {key} con formato invalido.") from exc
