from __future__ import annotations

import unittest
from datetime import datetime

from cfe_api.models.concurso import Concurso
from monitor.notifications.telegram import format_new_concurso_message


def make_concurso(fecha_publicacion: datetime | None) -> Concurso:
    return Concurso(
        id=1,
        numero="CFE-001",
        descripcion="Arnes de proteccion contra caidas",
        estado="Vigente",
        entidad_federativa="Tamaulipas",
        tipo_procedimiento="LP",
        tipo_contratacion="BIENES",
        fecha_publicacion=fecha_publicacion,
        proveedor_adjudicado="",
        monto=0.0,
        fecha_limite_ofertas=None,
        fecha_fallo=None,
    )


class TelegramMessageTests(unittest.TestCase):
    def test_omits_publication_hint_when_sent_near_publication_time(self) -> None:
        message = format_new_concurso_message(
            make_concurso(datetime(2026, 7, 23, 9, 0)),
            sent_at=datetime(2026, 7, 23, 9, 39),
        )

        self.assertNotIn("Publicado:", message)

    def test_includes_time_when_sent_late_same_day(self) -> None:
        message = format_new_concurso_message(
            make_concurso(datetime(2026, 7, 23, 9, 0)),
            sent_at=datetime(2026, 7, 23, 9, 41),
        )

        self.assertIn("<b>Publicado:</b> 09:00", message)

    def test_includes_relative_day_when_publication_was_yesterday(self) -> None:
        message = format_new_concurso_message(
            make_concurso(datetime(2026, 7, 22, 17, 30)),
            sent_at=datetime(2026, 7, 23, 9, 0),
        )

        self.assertIn("<b>Publicado:</b> ayer 17:30", message)

    def test_includes_relative_day_when_publication_was_two_days_ago(self) -> None:
        message = format_new_concurso_message(
            make_concurso(datetime(2026, 7, 21, 17, 30)),
            sent_at=datetime(2026, 7, 23, 9, 0),
        )

        self.assertIn("<b>Publicado:</b> antier 17:30", message)

    def test_includes_month_and_day_without_year_for_older_publication(self) -> None:
        message = format_new_concurso_message(
            make_concurso(datetime(2026, 7, 20, 17, 30)),
            sent_at=datetime(2026, 7, 23, 9, 0),
        )

        self.assertIn("<b>Publicado:</b> 20 jul 17:30", message)


if __name__ == "__main__":
    unittest.main()
