"""
Script historico de ingenieria inversa.

Este archivo queda como referencia del descubrimiento inicial del endpoint.
El codigo de aplicacion ya no debe depender de este script; debe usar cfe_api.
"""

import requests
from bs4 import BeautifulSoup


URL = "https://msc.cfe.mx/Aplicaciones/NCFE/Concursos/"
POST_URL = "https://msc.cfe.mx/Aplicaciones/NCFE/Concursos/Procedure/getProcBusqueda"

session = requests.Session()

response = session.get(URL)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
token = soup.find("input", {"name": "__RequestVerificationToken"})

print("Status:", response.status_code)

if token:
    print("Token encontrado:")
    print(token["value"])
else:
    raise RuntimeError("No se encontro el token CSRF.")

payload = {
    "__RequestVerificationToken": token["value"],
    "TipoProcedimientoClave": "",
    "TipoContratacionClave": "",
    "IdEntidadFederativa": "0",
    "Numero": "",
    "Descripcion": "",
    "EstadoProcedimientoContratacionClave": "0",
    "FechaPublicacion": "2026-06-29",
    "FechaPublicacionIni": "",
    "FechaPublicacionFin": "",
    "TestigoSocial": "2",
    "idCaracterProcedimiento": "0",
    "Modalidad": "0",
}

headers = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": URL,
}

result = session.post(POST_URL, data=payload, headers=headers)
result.raise_for_status()

datos = result.json()

print(f"Se encontraron {len(datos)} concursos")

for concurso in datos:
    print(concurso["Numero"])
