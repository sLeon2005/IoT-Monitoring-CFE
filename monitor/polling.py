from __future__ import annotations

from datetime import date, datetime, timedelta


PRODUCTION_LOOKBACK_DAYS = 3


def build_poll_dates(
    fecha_publicacion: str | None,
    *,
    once: bool,
    reference_date: date | None = None,
) -> list[str]:
    if fecha_publicacion is not None:
        return [fecha_publicacion]

    today = reference_date or datetime.now().date()

    if once:
        return [today.isoformat()]

    return [
        (today - timedelta(days=offset)).isoformat()
        for offset in range(PRODUCTION_LOOKBACK_DAYS + 1)
    ]
