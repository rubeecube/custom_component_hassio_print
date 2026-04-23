"""Config flow and options flow for the Auto Print integration.

Setup is CUPS-only — one step asking for the printer URL and queue name.
IMAP is handled by HA's built-in IMAP integration (configured separately).
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ALLOWED_SENDERS,
    CONF_AUTO_DELETE,
    CONF_BOOKLET_PATTERNS,
    CONF_CUPS_URL,
    CONF_DUPLEX_MODE,
    CONF_PRINTER_NAME,
    CONF_QUEUE_FOLDER,
    DEFAULT_AUTO_DELETE,
    DEFAULT_CUPS_URL,
    DEFAULT_DUPLEX_MODE,
    DEFAULT_QUEUE_FOLDER,
    DOMAIN,
    DUPLEX_MODES,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config flow — single step: printer settings
# ---------------------------------------------------------------------------

class AutoPrintConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup UI for Auto Print."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Single step: CUPS base URL + printer queue name."""
        errors: dict[str, str] = {}

        if user_input is not None:
            cups_url = user_input[CONF_CUPS_URL].rstrip("/")
            printer_name = user_input[CONF_PRINTER_NAME].strip()

            try:
                session = async_get_clientsession(self.hass)
                async with session.head(
                    cups_url, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status >= 500:
                        errors["base"] = "cannot_connect_cups"
            except (aiohttp.ClientError, OSError):
                errors["base"] = "cannot_connect_cups"
            except Exception:
                errors["base"] = "unknown"

            if not errors:
                unique_id = f"{cups_url}/{printer_name}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Auto Print — {printer_name}",
                    data={
                        CONF_CUPS_URL: cups_url,
                        CONF_PRINTER_NAME: printer_name,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_CUPS_URL, default=DEFAULT_CUPS_URL): str,
                vol.Required(CONF_PRINTER_NAME): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return AutoPrintOptionsFlow(config_entry)


# ---------------------------------------------------------------------------
# Options flow — editable after setup
# ---------------------------------------------------------------------------

class AutoPrintOptionsFlow(OptionsFlow):
    """Allow the user to adjust runtime options without re-running setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Single-step options form."""
        options = self._config_entry.options
        errors: dict[str, str] = {}

        if user_input is not None:
            patterns = [
                p.strip()
                for p in user_input[CONF_BOOKLET_PATTERNS].splitlines()
                if p.strip()
            ]
            senders = [
                s.strip().lower()
                for s in user_input[CONF_ALLOWED_SENDERS].splitlines()
                if s.strip()
            ]
            return self.async_create_entry(
                title="",
                data={
                    **user_input,
                    CONF_BOOKLET_PATTERNS: patterns,
                    CONF_ALLOWED_SENDERS: senders,
                },
            )

        current_patterns = options.get(CONF_BOOKLET_PATTERNS, [])
        current_senders = options.get(CONF_ALLOWED_SENDERS, [])

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ALLOWED_SENDERS,
                    default="\n".join(current_senders),
                ): str,
                vol.Required(
                    CONF_DUPLEX_MODE,
                    default=options.get(CONF_DUPLEX_MODE, DEFAULT_DUPLEX_MODE),
                ): vol.In(DUPLEX_MODES),
                vol.Required(
                    CONF_BOOKLET_PATTERNS,
                    default="\n".join(current_patterns),
                ): str,
                vol.Required(
                    CONF_AUTO_DELETE,
                    default=options.get(CONF_AUTO_DELETE, DEFAULT_AUTO_DELETE),
                ): bool,
                vol.Required(
                    CONF_QUEUE_FOLDER,
                    default=options.get(CONF_QUEUE_FOLDER, DEFAULT_QUEUE_FOLDER),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
