"""
Funciones auxiliares compartidas por toda la aplicacion.
"""

import re
from datetime import datetime


ASPNET_DATE_PATTERN = re.compile(r"^/Date\((-?\d+)([+-]\d{4})?\)/$")


def parse_aspnet_date(value: str | None) -> datetime | None:
    """
    Convierte una fecha ASP.NET del formato:

        /Date(1782753588817)/
        /Date(1782753588817-0600)/

    a un objeto datetime local sin timezone, manteniendo el comportamiento
    historico del proyecto.

    Si el valor es None o no tiene el formato esperado,
    devuelve None.
    """

    if not value:
        return None

    match = ASPNET_DATE_PATTERN.match(value.strip())

    if match is None:
        return None

    timestamp_ms = int(match.group(1))

    return datetime.fromtimestamp(timestamp_ms / 1000)


def looks_like_waf_block(body: str | None) -> bool:
    if not body:
        return False

    normalized_body = body.lower()
    markers = (
        "NOINDEX, NOFOLLOW",
        "incap_ses",
        "visid_incap",
        "_Incapsula_Resource",
    )

    return any(marker.lower() in normalized_body for marker in markers)


def response_snippet(body: str | None, limit: int = 300) -> str:
    if not body:
        return ""

    return " ".join(body[:limit].split())
