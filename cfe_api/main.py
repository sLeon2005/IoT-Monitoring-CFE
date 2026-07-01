from datetime import datetime
from pathlib import Path
import sys


if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from cfe_api.core.session import CFESession
from cfe_api.services.concursos import ConcursosService


def main() -> None:
    hoy = datetime.now().strftime("%Y-%m-%d")

    session = CFESession()
    session.initialize()

    concursos = ConcursosService(session)

    datos = concursos.buscar(
        fecha_publicacion=hoy
    )

    print(f"Se encontraron {len(datos)} concursos para {hoy}\n")

    for concurso in datos:
        print(f"{concurso.numero} - {concurso.descripcion}")


if __name__ == "__main__":
    main()
