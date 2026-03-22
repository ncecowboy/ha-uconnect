"""Coordinator for UConnect (T-Mobile) integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from py_uconnect import Client
from py_uconnect.command import Command
from py_uconnect.api import CHARGING_LEVELS_BY_NAME
from py_uconnect.brands import BRANDS as BRANDS_BY_NAME

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    # BRANDS is retained solely for backward compatibility: config entries created
    # before auto-detection stored the brand as an integer key into this dict.
    BRANDS,
    CONF_BRAND_REGION,
    CONF_DISABLE_TLS_VERIFICATION,
    CONF_LOG_LEVEL,
    DEFAULT_LOG_LEVEL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(DOMAIN)


class UconnectDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the UConnect cloud API."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.platforms: set[str] = set()
        self.extrapolated_soc_sensors: dict = {}

        # Remember which log level was active at initialization so that
        # update_options can detect a change and trigger a reload.
        self._applied_log_level: str = config_entry.options.get(
            CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL
        )

        # Prefer PIN from options; fall back to initial config data
        pin_options = config_entry.options.get(CONF_PIN)
        if pin_options is not None and pin_options != "":
            pin = pin_options
        else:
            pin = config_entry.data.get(CONF_PIN)

        # Resolve brand: new entries store the brand name string directly;
        # legacy entries (created before auto-detection) stored an integer key.
        brand_value = config_entry.data.get(CONF_BRAND_REGION)
        if isinstance(brand_value, int):
            brand_value = BRANDS.get(brand_value)
            if brand_value is None:
                raise ValueError(
                    f"Legacy config entry has an unrecognised brand key: "
                    f"{config_entry.data.get(CONF_BRAND_REGION)}. "
                    "Please reconfigure the integration."
                )
        brand = BRANDS_BY_NAME.get(brand_value)
        if brand is None:
            raise ValueError(
                f"Unknown brand '{brand_value}'. Please reconfigure the integration."
            )

        self.client = Client(
            email=config_entry.data.get(CONF_USERNAME),
            password=config_entry.data.get(CONF_PASSWORD),
            pin=pin,
            brand=brand,
            brand=BRANDS_BY_NAME[config_entry.data.get(CONF_BRAND_REGION)],
            disable_tls_verification=config_entry.data.get(
                CONF_DISABLE_TLS_VERIFICATION
            ),
        )

        self.refresh_interval: int = (
            config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL) * 60
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=self.refresh_interval),
            always_update=True,
        )

    async def _async_update_data(self):
        """Fetch data from the UConnect cloud API."""

        try:
            await self.hass.async_add_executor_job(self.client.refresh)
        except Exception as err:
            # On first run (no cached data), re-raise to signal setup failure
            if self.data is None:
                _LOGGER.error("Initial data fetch failed: %s", err)
                raise
            # On subsequent runs, log and fall back to cached data
            _LOGGER.warning("Update failed, falling back to cached data: %s", err)

        return True

    async def async_command(self, vin: str, cmd: Command) -> None:
        """Execute a remote command on the vehicle."""

        r = await self.hass.async_add_executor_job(self.client.command_verify, vin, cmd)
        await self.async_refresh()

        if not r:
            raise HomeAssistantError("Command execution failed")

    async def async_set_charging_level(self, vin: str, level: str) -> None:
        """Set the preferred charging level for an EV/PHEV."""

        if level not in CHARGING_LEVELS_BY_NAME:
            raise ValueError(f"Invalid charging level: {level}")
        level = CHARGING_LEVELS_BY_NAME[level]

        r = await self.hass.async_add_executor_job(
            self.client.set_charging_level_verify, vin, level
        )
        await self.async_refresh()

        if not r:
            raise HomeAssistantError("Set charging level failed")

    async def update_options(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Handle options updates (e.g. scan interval or log level changes)."""
        new_log_level = config_entry.options.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL)
        if new_log_level != self._applied_log_level:
            # Log level changed — reload the entire entry so the new level is
            # applied cleanly at startup and all components pick it up.
            _LOGGER.debug(
                "Log level changed (%s → %s); reloading integration",
                self._applied_log_level,
                new_log_level,
            )
            await hass.config_entries.async_reload(config_entry.entry_id)
            return

        self.update_interval = timedelta(
            seconds=config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            * 60
        )
