"""
Funciones auxiliares compartidas por toda la aplicación.
"""

import re
from datetime import datetime


def parse_aspnet_date(value: str | None) -> datetime | None:
    """
    Convierte una fecha ASP.NET del formato:

        /Date(1782753588817)/

    a un objeto datetime.

    Si el valor es None o no tiene el formato esperado,
    devuelve None.
    """

    if not value:
        return None

    match = re.search(r"\d+", value)

    if match is None:
        return None

    timestamp_ms = int(match.group())

    return datetime.fromtimestamp(timestamp_ms / 1000)