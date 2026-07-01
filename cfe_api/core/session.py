"""
Modulo encargado de administrar la sesion HTTP con CFE.

Responsabilidades:
- Crear y mantener una requests.Session()
- Obtener automaticamente el __RequestVerificationToken
- Exponer metodos GET y POST reutilizables

Este modulo NO conoce ningun endpoint especifico.
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from cfe_api.core.errors import CFEAPIError, CFEBlockedError


class CFESession:
    """Administra una sesion HTTP con el portal de CFE."""

    BASE_URL = "https://msc.cfe.mx"
    HOME_URL = f"{BASE_URL}/Aplicaciones/NCFE/Concursos/"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
            }
        )
        self.csrf_token: str | None = None

    def initialize(self) -> None:
        """
        Inicializa la sesion y obtiene el token CSRF.

        Debe llamarse una sola vez al iniciar.
        """

        response = self.session.get(
            self.HOME_URL,
            timeout=self.timeout
        )

        self._raise_for_status(response, "inicializar sesion CFE")

        soup = BeautifulSoup(response.text, "html.parser")

        token = soup.find(
            "input",
            {"name": "__RequestVerificationToken"}
        )

        if token is None:
            raise RuntimeError(
                "No fue posible obtener el token CSRF."
            )

        self.csrf_token = token["value"]

    @property
    def token(self) -> str:
        """Devuelve el token CSRF actual."""

        if self.csrf_token is None:
            raise RuntimeError(
                "La sesion aun no ha sido inicializada."
            )

        return self.csrf_token

    def get(self, url: str, **kwargs):
        """Realiza una peticion GET utilizando la sesion."""

        return self.session.get(
            url,
            timeout=self.timeout,
            **kwargs
        )

    def post(self, url: str, **kwargs):
        """Realiza una peticion POST utilizando la sesion."""

        return self.session.post(
            url,
            timeout=self.timeout,
            **kwargs
        )

    @staticmethod
    def _raise_for_status(response: requests.Response, context: str) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            snippet = " ".join(response.text[:300].split())
            message = (
                f"No fue posible {context}. "
                f"HTTP {response.status_code}. Respuesta: {snippet}"
            )

            if response.status_code == 403 or _looks_like_waf_block(response.text):
                raise CFEBlockedError(message) from exc

            raise CFEAPIError(message) from exc


def _looks_like_waf_block(body: str) -> bool:
    markers = (
        "NOINDEX, NOFOLLOW",
        "incap_ses",
        "visid_incap",
        "_Incapsula_Resource",
    )

    return any(marker in body for marker in markers)
