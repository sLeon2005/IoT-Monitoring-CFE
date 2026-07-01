from __future__ import annotations

import json
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from monitor.config import MonitorConfig, load_env_file
from monitor.database.repository import ConcursoRepository


PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = (PACKAGE_DIR / "static").resolve()


class DashboardServer(ThreadingHTTPServer):
    def __init__(self, server_address, config: MonitorConfig):
        super().__init__(server_address, DashboardRequestHandler)
        self.config = config
        self.repository = ConcursoRepository(config.db_path)
        self.repository.initialize()


class DashboardRequestHandler(BaseHTTPRequestHandler):
    server: DashboardServer

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/":
            self._send_static_file("index.html", "text/html; charset=utf-8")
            return

        if parsed_url.path.startswith("/static/"):
            self._send_static_file(
                parsed_url.path.removeprefix("/static/"),
                _content_type_for(parsed_url.path),
            )
            return

        if parsed_url.path == "/api/concursos":
            self._send_concursos(parsed_url.query)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        return

    def _send_static_file(self, filename: str, content_type: str) -> None:
        file_path = (STATIC_DIR / filename).resolve()

        if STATIC_DIR not in file_path.parents and file_path != STATIC_DIR:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        if not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_concursos(self, query: str) -> None:
        params = parse_qs(query)
        limit = _parse_limit(params.get("limit", ["50"])[0])
        fecha_publicacion = params.get(
            "date",
            [datetime.now().strftime("%Y-%m-%d")],
        )[0]
        rows = self.server.repository.list_by_publication_date(
            fecha_publicacion=fecha_publicacion,
            limit=limit,
        )
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "fecha_publicacion": fecha_publicacion,
            "refresh_seconds": self.server.config.dashboard_refresh_seconds,
            "source_status": self.server.repository.get_monitor_status(),
            "count": len(rows),
            "items": [_row_to_dict(row) for row in rows],
        }
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def _parse_limit(value: str) -> int:
    try:
        limit = int(value)
    except ValueError:
        return 50

    return max(1, min(limit, 200))


def _content_type_for(path: str) -> str:
    if path.endswith(".css"):
        return "text/css; charset=utf-8"

    if path.endswith(".js"):
        return "application/javascript; charset=utf-8"

    if path.endswith(".svg"):
        return "image/svg+xml"

    return "application/octet-stream"


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "numero": row["numero"],
        "descripcion": row["descripcion"],
        "estado": row["estado"],
        "entidad_federativa": row["entidad_federativa"],
        "tipo_procedimiento": row["tipo_procedimiento"],
        "tipo_contratacion": row["tipo_contratacion"],
        "fecha_publicacion": row["fecha_publicacion"],
        "proveedor_adjudicado": row["proveedor_adjudicado"],
        "monto": row["monto"],
        "fecha_limite_ofertas": row["fecha_limite_ofertas"],
        "fecha_fallo": row["fecha_fallo"],
        "detectado_en": row["detectado_en"],
    }


def main() -> None:
    load_env_file()
    config = MonitorConfig.from_env()
    server = DashboardServer((config.dashboard_host, config.dashboard_port), config)
    url = f"http://{config.dashboard_host}:{config.dashboard_port}"

    print(f"Dashboard CFE disponible en {url}")
    server.serve_forever()


if __name__ == "__main__":
    main()
