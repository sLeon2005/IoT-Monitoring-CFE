from __future__ import annotations

import logging

from cfe_api.core.browser_session import (
    BrowserSessionData,
    bootstrap_browser_session,
    clear_cached_browser_session,
    load_cached_browser_session,
)
from monitor.config import MonitorConfig


logger = logging.getLogger(__name__)


def resolve_cfe_session_data(config: MonitorConfig) -> BrowserSessionData | None:
    if config.cfe_cookie_header and config.cfe_request_verification_token:
        logger.info("Usando sesion CFE configurada manualmente en .env.")
        return BrowserSessionData(
            cookie_header=config.cfe_cookie_header,
            request_verification_token=config.cfe_request_verification_token,
            created_at="env",
        )

    cached_session = load_cached_browser_session(config.cfe_session_cache_path)

    if cached_session is not None:
        logger.info(
            "Usando sesion CFE cacheada desde %s.",
            config.cfe_session_cache_path,
        )
        return cached_session

    if not config.cfe_browser_bootstrap_enabled:
        logger.info("Bootstrap de sesion CFE por navegador deshabilitado.")
        return None

    logger.info("Obteniendo sesion CFE con Chromium/Playwright.")
    return bootstrap_browser_session(
        profile_dir=config.cfe_browser_profile_dir,
        cache_path=config.cfe_session_cache_path,
        headless=config.cfe_browser_headless,
        timeout_ms=config.cfe_browser_timeout_ms,
    )


def invalidate_cached_cfe_session(config: MonitorConfig) -> None:
    if config.cfe_cookie_header and config.cfe_request_verification_token:
        return

    clear_cached_browser_session(config.cfe_session_cache_path)
