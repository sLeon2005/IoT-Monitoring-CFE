from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from cfe_api.models.concurso import Concurso


class ConcursoRepository:
    """Persistencia historica de concursos detectados."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS concursos (
                    id INTEGER PRIMARY KEY,
                    numero TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    estado TEXT NOT NULL,
                    entidad_federativa TEXT NOT NULL,
                    tipo_procedimiento TEXT NOT NULL,
                    tipo_contratacion TEXT NOT NULL,
                    fecha_publicacion TEXT,
                    proveedor_adjudicado TEXT NOT NULL,
                    monto REAL NOT NULL,
                    fecha_limite_ofertas TEXT,
                    fecha_fallo TEXT,
                    detectado_en TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_concursos_fecha_publicacion
                ON concursos(fecha_publicacion)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_status (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

    def exists(self, concurso_id: int) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM concursos WHERE id = ? LIMIT 1",
                (concurso_id,),
            ).fetchone()

        return row is not None

    def save(self, concurso: Concurso) -> bool:
        detected_at = datetime.now().isoformat(timespec="seconds")

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO concursos (
                    id,
                    numero,
                    descripcion,
                    estado,
                    entidad_federativa,
                    tipo_procedimiento,
                    tipo_contratacion,
                    fecha_publicacion,
                    proveedor_adjudicado,
                    monto,
                    fecha_limite_ofertas,
                    fecha_fallo,
                    detectado_en
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    concurso.id,
                    concurso.numero,
                    concurso.descripcion,
                    concurso.estado,
                    concurso.entidad_federativa,
                    concurso.tipo_procedimiento,
                    concurso.tipo_contratacion,
                    self._datetime_to_text(concurso.fecha_publicacion),
                    concurso.proveedor_adjudicado,
                    concurso.monto,
                    self._datetime_to_text(concurso.fecha_limite_ofertas),
                    self._datetime_to_text(concurso.fecha_fallo),
                    detected_at,
                ),
            )

        return cursor.rowcount > 0

    def save_many(self, concursos: list[Concurso]) -> list[Concurso]:
        nuevos = []

        for concurso in concursos:
            if self.save(concurso):
                nuevos.append(concurso)

        return nuevos

    def list_recent(self, limit: int = 50) -> list[sqlite3.Row]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM concursos
                ORDER BY COALESCE(fecha_publicacion, detectado_en) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return rows

    def list_by_publication_date(
        self,
        fecha_publicacion: str,
        limit: int = 50,
    ) -> list[sqlite3.Row]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM concursos
                WHERE substr(fecha_publicacion, 1, 10) = ?
                ORDER BY COALESCE(fecha_publicacion, detectado_en) DESC
                LIMIT ?
                """,
                (fecha_publicacion, limit),
            ).fetchall()

        return rows

    def set_monitor_status(self, status: str, message: str) -> None:
        updated_at = datetime.now().isoformat(timespec="seconds")

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO monitor_status(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (
                    ("status", status),
                    ("message", message),
                    ("updated_at", updated_at),
                ),
            )

    def get_monitor_status(self) -> dict[str, str | None]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT key, value FROM monitor_status"
            ).fetchall()

        values = {row["key"]: row["value"] for row in rows}

        return {
            "status": values.get("status", "unknown"),
            "message": values.get("message", "Monitor sin estado registrado."),
            "updated_at": values.get("updated_at"),
        }

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row

        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _datetime_to_text(value: datetime | None) -> str | None:
        if value is None:
            return None

        return value.isoformat(timespec="seconds")
