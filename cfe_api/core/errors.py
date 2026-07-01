from __future__ import annotations


class CFEAPIError(RuntimeError):
    """Error esperado al comunicarse con el portal de CFE."""


class CFEBlockedError(CFEAPIError):
    """El portal rechazo la sesion HTTP, probablemente por proteccion anti-bot."""

