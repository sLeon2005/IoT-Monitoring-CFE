from __future__ import annotations

import argparse
import html
import os

import requests

from cfe_api.models.concurso import Concurso
from monitor.config import load_env_file


class TelegramNotificationError(RuntimeError):
    """Error esperado al enviar mensajes por Telegram."""


class TelegramNotifier:
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

        if not self.bot_token:
            raise ValueError("Falta TELEGRAM_BOT_TOKEN.")

        if not self.chat_id:
            raise ValueError("Falta TELEGRAM_CHAT_ID.")

    def send(self, message: str, parse_mode: str | None = None) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "disable_web_page_preview": True,
        }

        if parse_mode is not None:
            payload["parse_mode"] = parse_mode

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TelegramNotificationError(_format_telegram_error(exc)) from exc

    def send_new_concurso(self, concurso: Concurso) -> None:
        self.send(format_new_concurso_message(concurso), parse_mode="HTML")

    def send_status(self, message: str) -> None:
        self.send(
            f"<b>Estado monitor CFE</b>\n{html.escape(message)}",
            parse_mode="HTML",
        )

    def send_error(self, message: str) -> None:
        self.send(
            f"<b>Error monitor CFE</b>\n{html.escape(message)}",
            parse_mode="HTML",
        )


def format_new_concurso_message(concurso: Concurso) -> str:
    return "\n".join(
        [
            "<b>Nuevo concurso CFE detectado</b>",
            f"<b>Número:</b> {html.escape(concurso.numero)}",
            f"<b>Entidad:</b> {html.escape(concurso.entidad_federativa)}",
            f"<b>Tipo:</b> {html.escape(concurso.tipo_procedimiento)}",
            "",
            "<b>Descripción:</b>",
            html.escape(concurso.descripcion),
        ]
    )


def _format_telegram_error(exc: requests.RequestException) -> str:
    response = exc.response

    if response is None:
        return "No fue posible enviar mensaje Telegram."

    snippet = " ".join(response.text[:300].split())

    return (
        "No fue posible enviar mensaje Telegram. "
        f"HTTP {response.status_code}. Respuesta: {snippet}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Notificador Telegram del monitor CFE.")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Envia un mensaje de prueba usando TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.",
    )
    parser.add_argument(
        "--message",
        default="Prueba de notificaciones del monitor CFE.",
        help="Texto del mensaje de prueba.",
    )

    return parser.parse_args()


def main() -> None:
    load_env_file()
    args = parse_args()

    if not args.test:
        raise SystemExit("Usa --test para enviar un mensaje de prueba.")

    notifier = TelegramNotifier()
    notifier.send_status(args.message)
    print("Mensaje de prueba enviado por Telegram.")


if __name__ == "__main__":
    main()
