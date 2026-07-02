"""
Obtencion asistida de sesion CFE mediante navegador.

Este modulo produce los mismos datos que acepta CFESession: cookies y token CSRF.
No conoce endpoints de negocio; solo prepara una sesion valida del portal.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cfe_api.core.errors import CFEAPIError
from cfe_api.core.session import CFESession


@dataclass(frozen=True, slots=True)
class BrowserSessionData:
    cookie_header: str
    request_verification_token: str
    created_at: str


def load_cached_browser_session(path: str | Path) -> BrowserSessionData | None:
    cache_path = Path(path)

    if not cache_path.exists():
        return None

    try:
        raw_data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CFEAPIError(
            f"No fue posible leer la sesion CFE cacheada en {cache_path}."
        ) from exc

    cookie_header = raw_data.get("cookie_header")
    token = raw_data.get("request_verification_token")
    created_at = raw_data.get("created_at")

    if not cookie_header or not token or not created_at:
        return None

    return BrowserSessionData(
        cookie_header=cookie_header,
        request_verification_token=token,
        created_at=created_at,
    )


def save_browser_session(data: BrowserSessionData, path: str | Path) -> None:
    cache_path = Path(path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(asdict(data), indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def clear_cached_browser_session(path: str | Path) -> None:
    cache_path = Path(path)

    if cache_path.exists():
        cache_path.unlink()


def bootstrap_browser_session(
    *,
    profile_dir: str | Path,
    cache_path: str | Path | None = None,
    headless: bool = False,
    timeout_ms: int = 60_000,
) -> BrowserSessionData:
    """
    Abre Chromium con Playwright, carga el portal y extrae cookies + token CSRF.

    Si CFE muestra una validacion visual, debe resolverse manualmente en la ventana
    del navegador. El codigo solo espera a que el portal entregue el input oculto.
    """

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise CFEAPIError(
            "Playwright no esta instalado. Instala con: "
            "pip install playwright && python -m playwright install chromium"
        ) from exc

    profile_path = Path(profile_dir)
    profile_path.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_path),
            headless=headless,
            viewport={"width": 1366, "height": 768},
        )

        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(
                CFESession.HOME_URL,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )

            try:
                page.wait_for_load_state("networkidle", timeout=15_000)
            except PlaywrightTimeoutError:
                pass

            selector = 'input[name="__RequestVerificationToken"]'
            page.wait_for_selector(
                selector,
                state="attached",
                timeout=timeout_ms,
            )
            token = page.locator(selector).first.get_attribute("value")

            if not token:
                raise CFEAPIError("El navegador no encontro el token CSRF de CFE.")

            cookies = context.cookies(CFESession.BASE_URL)
            cookie_header = _build_cookie_header(cookies)

            if not cookie_header:
                raise CFEAPIError("El navegador no entrego cookies de CFE.")

            data = BrowserSessionData(
                cookie_header=cookie_header,
                request_verification_token=token,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

            if cache_path is not None:
                save_browser_session(data, cache_path)

            return data
        finally:
            context.close()


def _build_cookie_header(cookies: list[dict[str, Any]]) -> str:
    cfe_cookies = [
        cookie
        for cookie in cookies
        if "cfe.mx" in cookie.get("domain", "")
        and cookie.get("name")
        and cookie.get("value") is not None
    ]

    return "; ".join(
        f"{cookie['name']}={cookie['value']}"
        for cookie in sorted(cfe_cookies, key=lambda item: item["name"])
    )
