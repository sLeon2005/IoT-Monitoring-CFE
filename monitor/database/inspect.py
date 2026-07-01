from __future__ import annotations

import argparse
from pathlib import Path

from monitor.config import MonitorConfig, load_env_file
from monitor.database.repository import ConcursoRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspecciona concursos guardados en SQLite."
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        help="Ruta de la base SQLite. Por defecto usa MONITOR_DB_PATH.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Cantidad maxima de concursos a mostrar.",
    )

    return parser.parse_args()


def main() -> None:
    load_env_file()
    args = parse_args()
    config = MonitorConfig.from_env()
    db_path = Path(args.db_path or config.db_path)

    if not db_path.exists():
        print(f"No existe la base SQLite: {db_path}")
        return

    repository = ConcursoRepository(db_path)
    rows = repository.list_recent(limit=args.limit)

    if not rows:
        print(f"No hay concursos guardados en {db_path}.")
        return

    print(f"Base SQLite: {db_path}")
    print(f"Concursos mostrados: {len(rows)}\n")
    print_table(rows)


def print_table(rows) -> None:
    columns = [
        ("numero", "Numero", 18),
        ("entidad_federativa", "Entidad", 18),
        ("estado", "Estado", 14),
        ("tipo_procedimiento", "Tipo", 10),
        ("fecha_publicacion", "Publicacion", 19),
        ("monto", "Monto", 14),
        ("descripcion", "Descripcion", 48),
    ]

    header = "  ".join(label.ljust(width) for _, label, width in columns)
    separator = "  ".join("-" * width for _, _, width in columns)

    print(header)
    print(separator)

    for row in rows:
        values = [
            _format_value(row[key], width)
            for key, _, width in columns
        ]
        print("  ".join(values))


def _format_value(value, width: int) -> str:
    if value is None:
        text = ""
    elif isinstance(value, float):
        text = f"{value:,.2f}"
    else:
        text = str(value)

    text = " ".join(text.split())

    if len(text) > width:
        return text[: width - 3] + "..."

    return text.ljust(width)


if __name__ == "__main__":
    main()
