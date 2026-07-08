from __future__ import annotations

import json
import unittest

from cfe_api.core.errors import CFEAPIError, CFEBlockedError
from cfe_api.core.utils import parse_aspnet_date
from cfe_api.models.concurso import Concurso
from cfe_api.services.concursos import _parse_concursos_response


class FakeResponse:
    def __init__(
        self,
        body: str,
        *,
        content_type: str = "application/json",
    ):
        self.text = body
        self.headers = {"Content-Type": content_type}

    def json(self):
        return json.loads(self.text)


def make_response(body: str, *, content_type: str = "application/json") -> FakeResponse:
    return FakeResponse(body, content_type=content_type)


def sample_concurso_payload(**overrides):
    payload = {
        "Id": 123,
        "Numero": "CFE-001",
        "Descripcion": "Herramienta electrica",
        "EstadoProcedimiento": "Vigente",
        "EntidadFederativa": "Tamaulipas",
        "TipoProcedimientoClave": "LP",
        "TipoContratacionClave": "BIENES",
        "FechaPublicacion": "/Date(1782753588817)/",
        "NombProveedorAdjudicado": None,
        "MONTO": "1,234.50",
        "FechaLimiteOfertas": None,
        "FechaFallo": "",
    }
    payload.update(overrides)
    return payload


class ConcursoModelTests(unittest.TestCase):
    def test_from_dict_converts_valid_payload(self) -> None:
        concurso = Concurso.from_dict(sample_concurso_payload())

        self.assertEqual(concurso.id, 123)
        self.assertEqual(concurso.numero, "CFE-001")
        self.assertEqual(concurso.proveedor_adjudicado, "")
        self.assertEqual(concurso.monto, 1234.50)
        self.assertIsNotNone(concurso.fecha_publicacion)
        self.assertIsNone(concurso.fecha_limite_ofertas)

    def test_from_dict_rejects_missing_required_field(self) -> None:
        payload = sample_concurso_payload(Numero="")

        with self.assertRaisesRegex(ValueError, "Numero"):
            Concurso.from_dict(payload)

    def test_from_dict_accepts_decimal_comma_amount(self) -> None:
        concurso = Concurso.from_dict(sample_concurso_payload(MONTO="123,45"))

        self.assertEqual(concurso.monto, 123.45)


class CFEResponseParsingTests(unittest.TestCase):
    def test_parse_concursos_response_requires_json_list(self) -> None:
        response = make_response(json.dumps({"data": []}))

        with self.assertRaisesRegex(CFEAPIError, "lista"):
            _parse_concursos_response(response)

    def test_parse_concursos_response_rejects_html(self) -> None:
        response = make_response(
            "<html>No autorizado</html>",
            content_type="text/html",
        )

        with self.assertRaisesRegex(CFEAPIError, "JSON valido"):
            _parse_concursos_response(response)

    def test_parse_concursos_response_detects_waf_block(self) -> None:
        response = make_response(
            "<html><meta name='ROBOTS' content='NOINDEX, NOFOLLOW'>incap_ses</html>",
            content_type="text/html",
        )

        with self.assertRaises(CFEBlockedError):
            _parse_concursos_response(response)

    def test_parse_concursos_response_wraps_invalid_items(self) -> None:
        response = make_response(json.dumps([sample_concurso_payload(Id="abc")]))

        with self.assertRaisesRegex(CFEAPIError, "posicion 0"):
            _parse_concursos_response(response)


class DateParsingTests(unittest.TestCase):
    def test_parse_aspnet_date_accepts_offset_format(self) -> None:
        self.assertIsNotNone(parse_aspnet_date("/Date(1782753588817-0600)/"))

    def test_parse_aspnet_date_rejects_partial_digits(self) -> None:
        self.assertIsNone(parse_aspnet_date("fecha 1782753588817"))


if __name__ == "__main__":
    unittest.main()
