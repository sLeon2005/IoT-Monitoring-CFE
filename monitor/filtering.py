from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from cfe_api.models.concurso import Concurso


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INCLUDE_KEYWORDS_PATH = PROJECT_ROOT / "config" / "filters" / "include.txt"


@dataclass(frozen=True, slots=True)
class KeywordTerm:
    raw: str
    normalized: str


@dataclass(frozen=True, slots=True)
class FilterResult:
    is_relevant: bool
    matches: tuple[str, ...]


def load_keyword_terms(path: str | Path = DEFAULT_INCLUDE_KEYWORDS_PATH) -> tuple[KeywordTerm, ...]:
    """Carga terminos desde un archivo .txt con una palabra o frase por linea."""

    keyword_path = Path(path)

    if not keyword_path.exists():
        return ()

    terms: list[KeywordTerm] = []
    seen_normalized: set[str] = set()

    for line in keyword_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()

        if not raw or raw.startswith("#"):
            continue

        normalized = normalize_text(raw)

        if not normalized or normalized in seen_normalized:
            continue

        terms.append(KeywordTerm(raw=raw, normalized=normalized))
        seen_normalized.add(normalized)

    return tuple(terms)


class KeywordTermStore:
    """Carga terminos y los refresca cuando cambia el archivo."""

    def __init__(self, path: str | Path = DEFAULT_INCLUDE_KEYWORDS_PATH):
        self.path = Path(path)
        self._mtime_ns: int | None = None
        self._terms: tuple[KeywordTerm, ...] = ()

    def get_terms(self) -> tuple[KeywordTerm, ...]:
        current_mtime = self._get_mtime_ns()

        if current_mtime != self._mtime_ns:
            self._terms = load_keyword_terms(self.path)
            self._mtime_ns = current_mtime

        return self._terms

    def refresh(self) -> tuple[KeywordTerm, ...]:
        self._terms = load_keyword_terms(self.path)
        self._mtime_ns = self._get_mtime_ns()
        return self._terms

    def _get_mtime_ns(self) -> int | None:
        try:
            return self.path.stat().st_mtime_ns
        except FileNotFoundError:
            return None


def match_description(
    description: str,
    terms: tuple[KeywordTerm, ...],
) -> FilterResult:
    normalized_description = normalize_text(description)

    if not normalized_description or not terms:
        return FilterResult(is_relevant=False, matches=())

    searchable_description = f" {normalized_description} "
    matches = tuple(
        term.raw
        for term in terms
        if f" {term.normalized} " in searchable_description
    )

    return FilterResult(is_relevant=bool(matches), matches=matches)


def match_concurso(
    concurso: Concurso,
    terms: tuple[KeywordTerm, ...],
) -> FilterResult:
    return match_description(concurso.descripcion, terms)


def is_relevant_concurso(
    concurso: Concurso,
    terms: tuple[KeywordTerm, ...],
) -> bool:
    return match_concurso(concurso, terms).is_relevant


def normalize_text(value: str) -> str:
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(char)
    )
    alphanumeric_words = re.sub(r"[^a-z0-9]+", " ", without_accents)

    return " ".join(alphanumeric_words.split())
