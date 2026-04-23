"""Config flow tests for the Auto Print integration.

Golden rules applied:
  - Happy path: single "user" step → entry created.
  - CUPS unreachable → error shown → user can recover and complete.
  - Duplicate unique-id → aborted.
  - Options flow: persists all fields; allowed_senders stored as list.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.auto_print.const import DOMAIN

from .conftest import MOCK_CONFIG_DATA, MOCK_OPTIONS, _make_cups_session

_STEP1_INPUT = {
    "cups_url": "http://10.0.0.1:631",
    "printer_name": "TestPrinter",
}


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

async def test_full_flow_creates_entry(
    hass: HomeAssistant,
    mock_cups_ok,
    mock_setup_entry,
) -> None:
    """A complete valid flow must create a config entry in one step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _STEP1_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["cups_url"] == "http://10.0.0.1:631"
    assert result["data"]["printer_name"] == "TestPrinter"
    mock_setup_entry.assert_called_once()


async def test_entry_title_contains_printer_name(
    hass: HomeAssistant,
    mock_cups_ok,
    mock_setup_entry,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _STEP1_INPUT
    )
    assert "TestPrinter" in result["title"]


# ---------------------------------------------------------------------------
# CUPS error branch — error shown, user can recover
# ---------------------------------------------------------------------------

async def test_cups_unreachable_shows_error_then_recovers(
    hass: HomeAssistant,
    mock_setup_entry,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    # First attempt — CUPS is down.
    with patch(
        "custom_components.auto_print.config_flow.async_get_clientsession",
        side_effect=__import__("aiohttp").ClientError("refused"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _STEP1_INPUT
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "cannot_connect_cups"

    # Recovery — CUPS comes back.
    with patch(
        "custom_components.auto_print.config_flow.async_get_clientsession",
        return_value=_make_cups_session(200),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _STEP1_INPUT
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY


# ---------------------------------------------------------------------------
# Duplicate entry is rejected
# ---------------------------------------------------------------------------

async def test_duplicate_entry_aborted(
    hass: HomeAssistant,
    mock_cups_ok,
    mock_setup_entry,
) -> None:
    # First setup.
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _STEP1_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    # Second attempt with same CUPS URL + printer name.
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _STEP1_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------

async def test_options_flow_persists_all_fields(
    hass: HomeAssistant,
    mock_coordinator_update,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_DATA, options=MOCK_OPTIONS
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    new_input = {
        "allowed_senders": "a@example.com\nb@example.com",
        "duplex_mode": "one-sided",
        "booklet_patterns": "Au Puits\nBulletin",
        "auto_delete": False,
        "queue_folder": "/tmp/q2",
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], new_input
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    # Senders and patterns must be stored as lists, not raw strings.
    assert entry.options["allowed_senders"] == ["a@example.com", "b@example.com"]
    assert entry.options["booklet_patterns"] == ["Au Puits", "Bulletin"]
    assert entry.options["duplex_mode"] == "one-sided"
    assert entry.options["auto_delete"] is False


async def test_options_flow_empty_senders_means_accept_all(
    hass: HomeAssistant,
    mock_coordinator_update,
) -> None:
    """An empty allowed_senders field is valid — it means accept all senders."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_DATA, options=MOCK_OPTIONS
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    new_input = {
        "allowed_senders": "   ",   # whitespace only → empty list
        "duplex_mode": "two-sided-long-edge",
        "booklet_patterns": "",
        "auto_delete": True,
        "queue_folder": "/tmp/q",
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], new_input
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["allowed_senders"] == []
