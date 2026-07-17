from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from monitor.filtering import DEFAULT_INCLUDE_KEYWORDS_PATH
from monitor.filtering import normalize_text


DEFAULT_SECTION_NAME = "Sin seccion"


@dataclass(frozen=True, slots=True)
class FilterSection:
    name: str
    terms: tuple[str, ...]


def load_filter_sections(
    path: str | Path = DEFAULT_INCLUDE_KEYWORDS_PATH,
) -> tuple[FilterSection, ...]:
    filter_path = Path(path)

    if not filter_path.exists():
        return ()

    sections: list[FilterSection] = []
    current_name: str | None = None
    current_terms: list[str] = []

    def flush_current() -> None:
        nonlocal current_name, current_terms

        if current_name is None:
            return

        sections.append(
            FilterSection(
                name=current_name,
                terms=tuple(current_terms),
            )
        )
        current_name = None
        current_terms = []

    for line in filter_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()

        if not raw:
            continue

        if raw.startswith("#"):
            flush_current()
            current_name = _clean_section_name(raw.removeprefix("#"))
            continue

        if current_name is None:
            current_name = DEFAULT_SECTION_NAME

        current_terms.append(raw)

    flush_current()

    return tuple(sections)


def save_filter_sections(
    sections: tuple[FilterSection, ...] | list[FilterSection],
    path: str | Path = DEFAULT_INCLUDE_KEYWORDS_PATH,
) -> None:
    filter_path = Path(path)
    normalized_sections = normalize_filter_sections(sections)
    content = serialize_filter_sections(normalized_sections)

    filter_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = filter_path.with_name(f"{filter_path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(filter_path)


def normalize_filter_sections(
    sections: tuple[FilterSection, ...] | list[FilterSection],
) -> tuple[FilterSection, ...]:
    normalized: list[FilterSection] = []
    seen_terms: set[str] = set()

    for section in sections:
        name = _clean_section_name(section.name)
        terms: list[str] = []

        for raw_term in section.terms:
            term = _clean_term(raw_term)

            if not term:
                continue

            normalized_term = normalize_text(term)

            if not normalized_term or normalized_term in seen_terms:
                continue

            terms.append(term)
            seen_terms.add(normalized_term)

        normalized.append(FilterSection(name=name, terms=tuple(terms)))

    return tuple(normalized)


def serialize_filter_sections(sections: tuple[FilterSection, ...]) -> str:
    blocks: list[str] = []

    for section in sections:
        block_lines = [f"# {section.name}", ""]
        block_lines.extend(section.terms)
        blocks.append("\n".join(block_lines).rstrip())

    if not blocks:
        return ""

    return "\n\n".join(blocks).rstrip() + "\n"


def sections_to_payload(sections: tuple[FilterSection, ...]) -> dict:
    return {
        "sections": [
            {
                "name": section.name,
                "terms": list(section.terms),
                "term_count": len(section.terms),
            }
            for section in sections
        ],
        "section_count": len(sections),
        "term_count": sum(len(section.terms) for section in sections),
    }


def sections_from_payload(payload: dict) -> tuple[FilterSection, ...]:
    raw_sections = payload.get("sections")

    if not isinstance(raw_sections, list):
        raise ValueError("El payload debe incluir una lista de secciones.")

    sections: list[FilterSection] = []

    for index, raw_section in enumerate(raw_sections, start=1):
        if not isinstance(raw_section, dict):
            raise ValueError(f"La seccion {index} no es valida.")

        raw_name = raw_section.get("name")
        raw_terms = raw_section.get("terms", [])

        if not isinstance(raw_name, str):
            raise ValueError(f"La seccion {index} debe tener nombre.")

        if not isinstance(raw_terms, list):
            raise ValueError(f"La seccion {index} debe tener lista de terminos.")

        terms: list[str] = []

        for term_index, raw_term in enumerate(raw_terms, start=1):
            if not isinstance(raw_term, str):
                raise ValueError(
                    f"El termino {term_index} de la seccion {index} no es valido."
                )

            terms.append(raw_term)

        sections.append(FilterSection(name=raw_name, terms=tuple(terms)))

    return normalize_filter_sections(sections)


def _clean_section_name(value: str) -> str:
    clean_value = " ".join(value.strip().lstrip("#").split())
    return clean_value or DEFAULT_SECTION_NAME


def _clean_term(value: str) -> str:
    clean_value = " ".join(value.strip().split())

    if clean_value.startswith("#"):
        return ""

    return normalize_text(clean_value)
