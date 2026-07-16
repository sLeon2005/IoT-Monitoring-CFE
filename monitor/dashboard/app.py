from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from monitor.config import MonitorConfig, load_env_file
from monitor.database.repository import ConcursoRepository
from monitor.dashboard.state import AVAILABLE_VIEWS, DashboardState, is_valid_view
from monitor.filtering import load_keyword_terms, match_description
from monitor.system.network import get_wifi_status
from monitor.weather.open_meteo import get_configured_weather, weather_disabled_snapshot


PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = (PACKAGE_DIR / "static").resolve()
RELEVANT_VIEW_WINDOW_DAYS = 5


class DashboardServer(ThreadingHTTPServer):
    def __init__(self, server_address, config: MonitorConfig):
        super().__init__(server_address, DashboardRequestHandler)
        self.config = config
        self.repository = ConcursoRepository(config.db_path)
        self.repository.initialize()
        self.dashboard_state = DashboardState()
        self.keyword_terms = load_keyword_terms()


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

        if parsed_url.path == "/api/dashboard/state":
            self._send_dashboard_state()
            return

        if parsed_url.path == "/api/stats/recent-publications":
            self._send_recent_publication_stats()
            return

        if parsed_url.path == "/api/system/wifi":
            self._send_json(get_wifi_status())
            return

        if parsed_url.path == "/api/weather":
            self._send_weather()
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/api/dashboard/mode/next":
            view = self.server.dashboard_state.next_view()
            self._send_dashboard_state(view=view)
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

    def _send_json(self, payload: dict) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_concursos(self, query: str) -> None:
        params = parse_qs(query)
        limit = _parse_limit(params["limit"][0]) if "limit" in params else None
        view = params.get("view", [self.server.dashboard_state.get_view()])[0]

        if not is_valid_view(view):
            self.send_error(HTTPStatus.BAD_REQUEST, "Vista no soportada.")
            return

        fecha_publicacion = params.get(
            "date",
            [datetime.now().strftime("%Y-%m-%d")],
        )[0]
        publication_date = _parse_publication_date(fecha_publicacion)

        if publication_date is None:
            self.send_error(HTTPStatus.BAD_REQUEST, "Fecha no valida.")
            return

        start_date = publication_date
        end_date = publication_date

        if view == "relevant":
            start_date = publication_date - timedelta(
                days=RELEVANT_VIEW_WINDOW_DAYS - 1
            )
            rows = self.server.repository.list_by_publication_date_range(
                start_date=start_date,
                end_date=end_date,
                limit=None,
            )
        else:
            rows = self.server.repository.list_by_publication_date(
                fecha_publicacion=fecha_publicacion,
                limit=limit,
            )

        metric_rows = rows

        if view == "relevant":
            metric_rows = self.server.repository.list_by_publication_date(
                fecha_publicacion=fecha_publicacion,
                limit=None,
            )

        total_count = len(rows)
        relevant_rows = [
            row
            for row in rows
            if match_description(
                row["descripcion"],
                self.server.keyword_terms,
            ).is_relevant
        ]
        filtered_rows = rows

        if view == "relevant":
            filtered_rows = _limit_rows(relevant_rows, limit)

        metric_relevant_rows = [
            row
            for row in metric_rows
            if match_description(
                row["descripcion"],
                self.server.keyword_terms,
            ).is_relevant
        ]

        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "fecha_publicacion": fecha_publicacion,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": (end_date - start_date).days + 1,
            },
            "view": view,
            "refresh_seconds": self.server.config.dashboard_refresh_seconds,
            "source_status": self.server.repository.get_monitor_status(),
            "count": len(filtered_rows),
            "total_count": total_count,
            "relevant_count": len(relevant_rows),
            "metric_total_count": len(metric_rows),
            "metric_relevant_count": len(metric_relevant_rows),
            "items": [_row_to_dict(row) for row in filtered_rows],
        }
        self._send_json(payload)

    def _send_dashboard_state(self, view: str | None = None) -> None:
        current_view = view or self.server.dashboard_state.get_view()
        self._send_json(
            {
                "view": current_view,
                "available_views": list(AVAILABLE_VIEWS),
                "cursor_idle_seconds": self.server.config.dashboard_cursor_idle_seconds,
            }
        )

    def _send_recent_publication_stats(self) -> None:
        today = datetime.now().date()
        start_date = today - timedelta(days=6)
        counts = self.server.repository.count_by_publication_date(
            start_date=start_date,
            end_date=today,
        )
        days = []

        for offset in range(7):
            current_date = start_date + timedelta(days=offset)
            date_key = current_date.isoformat()
            days.append(
                {
                    "date": date_key,
                    "label": _weekday_initial(current_date.weekday()),
                    "count": counts.get(date_key, 0),
                    "is_today": current_date == today,
                }
            )

        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "days": days,
        }
        self._send_json(payload)

    def _send_weather(self) -> None:
        try:
            snapshot = get_configured_weather(self.server.config)
            payload = snapshot.to_dict()
        except Exception:
            payload = weather_disabled_snapshot(
                self.server.config.weather_location_name
            ).to_dict()
            payload["condition"] = "Clima no disponible"

        payload["refresh_seconds"] = self.server.config.weather_refresh_seconds
        self._send_json(payload)


def _parse_limit(value: str) -> int:
    try:
        limit = int(value)
    except ValueError:
        return 100

    return max(1, min(limit, 200))


def _parse_publication_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _limit_rows(rows: list, limit: int | None) -> list:
    if limit is None:
        return rows

    return rows[:limit]


def _content_type_for(path: str) -> str:
    if path.endswith(".css"):
        return "text/css; charset=utf-8"

    if path.endswith(".js"):
        return "application/javascript; charset=utf-8"

    if path.endswith(".svg"):
        return "image/svg+xml"

    return "application/octet-stream"


def _weekday_initial(weekday: int) -> str:
    return ["L", "M", "X", "J", "V", "S", "D"][weekday]


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
