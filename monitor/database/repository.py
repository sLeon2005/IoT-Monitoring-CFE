from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from cfe_api.models.concurso import Concurso


@dataclass(frozen=True, slots=True)
class NotificationOutboxItem:
    id: int
    concurso: Concurso
    channel: str
    status: str
    attempts: int
    next_attempt_at: str
    last_error: str | None


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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concurso_id INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at TEXT NOT NULL,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    sent_at TEXT,
                    UNIQUE(concurso_id, channel),
                    FOREIGN KEY(concurso_id) REFERENCES concursos(id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_notification_outbox_due
                ON notification_outbox(status, channel, next_attempt_at)
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

    def list_recent(self, limit: int = 100) -> list[sqlite3.Row]:
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

    def get_latest(self) -> Concurso | None:
        rows = self.list_recent(limit=1)

        if not rows:
            return None

        return self._row_to_concurso(rows[0])

    def list_by_publication_date(
        self,
        fecha_publicacion: str,
        limit: int | None = 100,
    ) -> list[sqlite3.Row]:
        query = """
            SELECT *
            FROM concursos
            WHERE substr(fecha_publicacion, 1, 10) = ?
            ORDER BY COALESCE(fecha_publicacion, detectado_en) DESC
            """
        params: tuple[str] | tuple[str, int] = (fecha_publicacion,)

        if limit is not None:
            query += " LIMIT ?"
            params = (fecha_publicacion, limit)

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()

        return rows

    def list_by_publication_date_range(
        self,
        start_date: date,
        end_date: date,
        limit: int | None = 100,
    ) -> list[sqlite3.Row]:
        query = """
            SELECT *
            FROM concursos
            WHERE substr(fecha_publicacion, 1, 10) BETWEEN ? AND ?
            ORDER BY COALESCE(fecha_publicacion, detectado_en) DESC
            """
        params: tuple[str, str] | tuple[str, str, int] = (
            start_date.isoformat(),
            end_date.isoformat(),
        )

        if limit is not None:
            query += " LIMIT ?"
            params = (
                start_date.isoformat(),
                end_date.isoformat(),
                limit,
            )

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()

        return rows

    def count_by_publication_date(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT substr(fecha_publicacion, 1, 10) AS publication_date,
                       COUNT(*) AS total
                FROM concursos
                WHERE substr(fecha_publicacion, 1, 10) BETWEEN ? AND ?
                GROUP BY publication_date
                """,
                (start_date.isoformat(), end_date.isoformat()),
            ).fetchall()

        return {row["publication_date"]: row["total"] for row in rows}

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

    def enqueue_notification(
        self,
        concurso_id: int,
        channel: str,
        next_attempt_at: datetime | None = None,
    ) -> bool:
        now = datetime.now().isoformat(timespec="seconds")
        due_at = (
            next_attempt_at.isoformat(timespec="seconds")
            if next_attempt_at
            else now
        )

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO notification_outbox (
                    concurso_id,
                    channel,
                    status,
                    attempts,
                    next_attempt_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, 'pending', 0, ?, ?, ?)
                """,
                (concurso_id, channel, due_at, now, now),
            )

        return cursor.rowcount > 0

    def list_due_notifications(
        self,
        *,
        channel: str,
        due_at: datetime,
        limit: int = 20,
    ) -> list[NotificationOutboxItem]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    n.id AS notification_id,
                    n.channel AS notification_channel,
                    n.status AS notification_status,
                    n.attempts AS notification_attempts,
                    n.next_attempt_at AS notification_next_attempt_at,
                    n.last_error AS notification_last_error,
                    c.id AS concurso_id,
                    c.numero AS concurso_numero,
                    c.descripcion AS concurso_descripcion,
                    c.estado AS concurso_estado,
                    c.entidad_federativa AS concurso_entidad_federativa,
                    c.tipo_procedimiento AS concurso_tipo_procedimiento,
                    c.tipo_contratacion AS concurso_tipo_contratacion,
                    c.fecha_publicacion AS concurso_fecha_publicacion,
                    c.proveedor_adjudicado AS concurso_proveedor_adjudicado,
                    c.monto AS concurso_monto,
                    c.fecha_limite_ofertas AS concurso_fecha_limite_ofertas,
                    c.fecha_fallo AS concurso_fecha_fallo
                FROM notification_outbox n
                JOIN concursos c ON c.id = n.concurso_id
                WHERE n.channel = ?
                  AND n.status = 'pending'
                  AND n.next_attempt_at <= ?
                ORDER BY n.next_attempt_at ASC, n.id ASC
                LIMIT ?
                """,
                (channel, due_at.isoformat(timespec="seconds"), limit),
            ).fetchall()

        return [self._row_to_notification_outbox_item(row) for row in rows]

    def mark_notification_sent(self, notification_id: int) -> None:
        now = datetime.now().isoformat(timespec="seconds")

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE notification_outbox
                SET status = 'sent',
                    updated_at = ?,
                    sent_at = ?,
                    last_error = NULL
                WHERE id = ?
                """,
                (now, now, notification_id),
            )

    def mark_notification_failed(
        self,
        notification_id: int,
        *,
        error_message: str,
        next_attempt_at: datetime,
        final: bool = False,
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        status = "failed" if final else "pending"

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE notification_outbox
                SET status = ?,
                    attempts = attempts + 1,
                    next_attempt_at = ?,
                    last_error = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    next_attempt_at.isoformat(timespec="seconds"),
                    error_message[:500],
                    now,
                    notification_id,
                ),
            )

    def count_notifications_by_status(self, channel: str) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT status, COUNT(*) AS total
                FROM notification_outbox
                WHERE channel = ?
                GROUP BY status
                """,
                (channel,),
            ).fetchall()

        return {row["status"]: row["total"] for row in rows}

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

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

    @staticmethod
    def _text_to_datetime(value: str | None) -> datetime | None:
        if value is None:
            return None

        return datetime.fromisoformat(value)

    @classmethod
    def _row_to_concurso(cls, row: sqlite3.Row) -> Concurso:
        return Concurso(
            id=row["id"],
            numero=row["numero"],
            descripcion=row["descripcion"],
            estado=row["estado"],
            entidad_federativa=row["entidad_federativa"],
            tipo_procedimiento=row["tipo_procedimiento"],
            tipo_contratacion=row["tipo_contratacion"],
            fecha_publicacion=cls._text_to_datetime(row["fecha_publicacion"]),
            proveedor_adjudicado=row["proveedor_adjudicado"],
            monto=row["monto"],
            fecha_limite_ofertas=cls._text_to_datetime(row["fecha_limite_ofertas"]),
            fecha_fallo=cls._text_to_datetime(row["fecha_fallo"]),
        )

    @classmethod
    def _row_to_notification_outbox_item(
        cls,
        row: sqlite3.Row,
    ) -> NotificationOutboxItem:
        concurso = Concurso(
            id=row["concurso_id"],
            numero=row["concurso_numero"],
            descripcion=row["concurso_descripcion"],
            estado=row["concurso_estado"],
            entidad_federativa=row["concurso_entidad_federativa"],
            tipo_procedimiento=row["concurso_tipo_procedimiento"],
            tipo_contratacion=row["concurso_tipo_contratacion"],
            fecha_publicacion=cls._text_to_datetime(row["concurso_fecha_publicacion"]),
            proveedor_adjudicado=row["concurso_proveedor_adjudicado"],
            monto=row["concurso_monto"],
            fecha_limite_ofertas=cls._text_to_datetime(
                row["concurso_fecha_limite_ofertas"]
            ),
            fecha_fallo=cls._text_to_datetime(row["concurso_fecha_fallo"]),
        )

        return NotificationOutboxItem(
            id=row["notification_id"],
            concurso=concurso,
            channel=row["notification_channel"],
            status=row["notification_status"],
            attempts=row["notification_attempts"],
            next_attempt_at=row["notification_next_attempt_at"],
            last_error=row["notification_last_error"],
        )
