"""Diagnostics support for UConnect (T-Mobile) integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.diagnostics.util import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_PIN, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(DOMAIN)

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME, CONF_PIN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a UConnect config entry."""

    coordinator = hass.data[DOMAIN][config_entry.unique_id]

    vehicles: dict[str, Any] = {}
    try:
        for vin, vehicle in coordinator.client.get_vehicles().items():
            # Redact VIN to last four characters to protect privacy.
            redacted_vin = f"**{vin[-4:]}"
            vehicles[redacted_vin] = {
                "make": vehicle.make,
                "model": vehicle.model,
                "nickname": vehicle.nickname,
            }
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Unable to retrieve vehicle list for diagnostics: %s", err)
        vehicles = {"error": "Unable to retrieve vehicle list"}

    return {
        "config_entry": async_redact_data(dict(config_entry.data), TO_REDACT),
        "options": dict(config_entry.options),
        "vehicles": vehicles,
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
        },
    }
