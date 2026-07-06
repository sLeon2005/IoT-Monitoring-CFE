from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


AVAILABLE_VIEWS = ("all", "relevant")
DEFAULT_VIEW = "all"


@dataclass(slots=True)
class DashboardState:
    _view: str = DEFAULT_VIEW
    _lock: Lock = field(default_factory=Lock)

    def get_view(self) -> str:
        with self._lock:
            return self._view

    def set_view(self, view: str) -> str:
        if view not in AVAILABLE_VIEWS:
            raise ValueError(f"Vista no soportada: {view}")

        with self._lock:
            self._view = view
            return self._view

    def next_view(self) -> str:
        with self._lock:
            current_index = AVAILABLE_VIEWS.index(self._view)
            next_index = (current_index + 1) % len(AVAILABLE_VIEWS)
            self._view = AVAILABLE_VIEWS[next_index]
            return self._view


def is_valid_view(view: str) -> bool:
    return view in AVAILABLE_VIEWS
