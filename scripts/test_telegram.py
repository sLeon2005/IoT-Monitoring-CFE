from datetime import datetime
from pathlib import Path
import sys


if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from monitor.config import load_env_file
from monitor.notifications.telegram import TelegramNotifier


def main() -> None:
    load_env_file()

    hora = datetime.now().strftime("%H:%M:%S")
    mensaje = f"Hora actual: {hora}"

    notifier = TelegramNotifier()
    notifier.send(mensaje)

    print("Mensaje enviado.")


if __name__ == "__main__":
    main()
