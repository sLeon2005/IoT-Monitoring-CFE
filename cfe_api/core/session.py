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


class CFESession:
    """Administra una sesion HTTP con el portal de CFE."""

    BASE_URL = "https://msc.cfe.mx"
    HOME_URL = f"{BASE_URL}/Aplicaciones/NCFE/Concursos/"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
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

        response.raise_for_status()

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
