from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from monitor.filter_catalog import (
    FilterSection,
    load_filter_sections,
    save_filter_sections,
    sections_from_payload,
)


class FilterCatalogTests(unittest.TestCase):
    def test_load_filter_sections_preserves_comment_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "include.txt"
            path.write_text(
                "\n".join(
                    [
                        "# Linea viva",
                        "",
                        "pertiga",
                        "loadbuster",
                        "",
                        "# Transformadores",
                        "transformador",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                load_filter_sections(path),
                (
                    FilterSection(
                        name="Linea viva",
                        terms=("pertiga", "loadbuster"),
                    ),
                    FilterSection(
                        name="Transformadores",
                        terms=("transformador",),
                    ),
                ),
            )

    def test_save_filter_sections_writes_include_txt_format(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "include.txt"

            save_filter_sections(
                [
                    FilterSection(
                        name="Linea viva",
                        terms=("pertiga", "loadbuster"),
                    ),
                    FilterSection(
                        name="Transformadores",
                        terms=("transformador",),
                    ),
                ],
                path=path,
            )

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "\n".join(
                    [
                        "# Linea viva",
                        "",
                        "pertiga",
                        "loadbuster",
                        "",
                        "# Transformadores",
                        "",
                        "transformador",
                        "",
                    ]
                ),
            )

    def test_sections_from_payload_removes_duplicate_terms(self) -> None:
        sections = sections_from_payload(
            {
                "sections": [
                    {
                        "name": "Herramienta",
                        "terms": ["Pértiga", "pertiga", "# no debe guardarse"],
                    },
                    {
                        "name": "Linea viva",
                        "terms": ["LoadBuster!!"],
                    },
                ],
            }
        )

        self.assertEqual(
            sections,
            (
                FilterSection(name="Herramienta", terms=("pertiga",)),
                FilterSection(name="Linea viva", terms=("loadbuster",)),
            ),
        )


if __name__ == "__main__":
    unittest.main()
