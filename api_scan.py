# Código por Sebastián León para EEPAT de México S.A. de C.V.

import requests
from bs4 import BeautifulSoup

URL = "https://msc.cfe.mx/Aplicaciones/NCFE/Concursos/"

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
    print("No se encontró el token.")

POST_URL = "https://msc.cfe.mx/Aplicaciones/NCFE/Concursos/Procedure/getProcBusqueda"

payload = {
    "__RequestVerificationToken": token["value"],
    "TipoProcedimientoClave": "",
    "TipoContratacionClave": "",
    "IdEntidadFederativa": "0",
    "Numero": "",
    "Descripcion": "",
    "EstadoProcedimientoContratacionClave": "0",
    "FechaPublicacion": "2026-06-29",   # usa la fecha que quieras consultar
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

r = session.post(POST_URL, data=payload, headers=headers)
r.raise_for_status()

datos = r.json()

print(f"Se encontraron {len(datos)} concursos")

for concurso in datos:
    print(concurso["Numero"])