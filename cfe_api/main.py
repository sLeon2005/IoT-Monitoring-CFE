from core.session import CFESession
from services.concursos import ConcursosService

session = CFESession()
session.initialize()

concursos = ConcursosService(session)

datos = concursos.buscar_por_fecha("2026-06-29")

print(f"Se encontraron {len(datos)} concursos")

for concurso in datos:
    print(concurso.numero, end=" - ")
    print(concurso.descripcion)