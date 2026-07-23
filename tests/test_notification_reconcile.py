from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from cfe_api.models.concurso import Concurso
from monitor.database.repository import ConcursoRepository
from monitor.filtering import KeywordTerm
from monitor.notifications.reconcile import reconcile_relevant_notifications


def make_concurso(concurso_id: int, descripcion: str) -> Concurso:
    return Concurso(
        id=concurso_id,
        numero=f"CFE-{concurso_id}",
        descripcion=descripcion,
        estado="Vigente",
        entidad_federativa="Tamaulipas",
        tipo_procedimiento="LP",
        tipo_contratacion="BIENES",
        fecha_publicacion=datetime(2026, 7, 23, 9, 0, 0),
        proveedor_adjudicado="",
        monto=0.0,
        fecha_limite_ofertas=None,
        fecha_fallo=None,
    )


class NotificationReconcileTests(unittest.TestCase):
    def test_new_filter_term_enqueues_historical_relevant_concurso_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ConcursoRepository(Path(temp_dir) / "monitor.sqlite3")
            repository.initialize()
            repository.save(make_concurso(1, "Arnes de proteccion contra caidas"))
            repository.save(make_concurso(2, "Servicio de limpieza general"))
            terms = (KeywordTerm(raw="arnes", normalized="arnes"),)

            first_result = reconcile_relevant_notifications(
                repository=repository,
                terms=terms,
                channel="telegram",
            )
            second_result = reconcile_relevant_notifications(
                repository=repository,
                terms=terms,
                channel="telegram",
            )

            self.assertEqual(first_result.evaluated, 2)
            self.assertEqual(first_result.relevant, 1)
            self.assertEqual(first_result.enqueued, 1)
            self.assertEqual(first_result.already_queued, 0)
            self.assertEqual(second_result.enqueued, 0)
            self.assertEqual(second_result.already_queued, 1)
            self.assertEqual(
                repository.count_notifications_by_status("telegram"),
                {"pending": 1},
            )
            self.assertEqual(
                repository.get_notification_status(
                    concurso_id=1,
                    channel="telegram",
                )["status"],
                "pending",
            )


if __name__ == "__main__":
    unittest.main()
