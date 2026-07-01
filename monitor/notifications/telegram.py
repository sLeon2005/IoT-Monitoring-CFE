from __future__ import annotations

import os

import requests

from cfe_api.models.concurso import Concurso


class TelegramNotifier:
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

        if not self.bot_token:
            raise ValueError("Falta TELEGRAM_BOT_TOKEN.")

        if not self.chat_id:
            raise ValueError("Falta TELEGRAM_CHAT_ID.")

    def send(self, message: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        response = requests.post(
            url,
            json={
                "chat_id": self.chat_id,
                "text": message,
            },
            timeout=30,
        )
        response.raise_for_status()

    def send_new_concurso(self, concurso: Concurso) -> None:
        message = "\n".join(
            [
                "Nuevo concurso CFE detectado",
                f"Numero: {concurso.numero}",
                f"Entidad: {concurso.entidad_federativa}",
                f"Estado: {concurso.estado}",
                f"Tipo: {concurso.tipo_procedimiento}",
                f"Monto: {concurso.monto}",
                f"Descripcion: {concurso.descripcion}",
            ]
        )

        self.send(message)
