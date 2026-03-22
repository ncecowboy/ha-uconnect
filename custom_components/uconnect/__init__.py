"""UConnect (T-Mobile) Home Assistant integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .const import BRANDS, CONF_BRAND_REGION, CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL, DOMAIN
from .coordinator import UconnectDataUpdateCoordinator
from .services import async_setup_services, async_unload_services

PLATFORMS: list[str] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.LOCK,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.SELECT,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(DOMAIN)


def _apply_log_level(config_entry: ConfigEntry) -> None:
    """Apply the log level from options to the integration loggers."""
    log_level_str = config_entry.options.get(CONF_LOG_LEVEL, DEFAULT_LOG_LEVEL)
    level = getattr(logging, log_level_str.upper(), logging.WARNING)
    for logger_name in (DOMAIN, f"custom_components.{DOMAIN}", "py_uconnect"):
        logging.getLogger(logger_name).setLevel(level)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entries to newer versions."""

    if config_entry.version == 1:
        # v1 stored brand_region as an integer key; v2 stores the brand name string.
        new_data = {**config_entry.data}
        old_val = new_data.get(CONF_BRAND_REGION)
        if isinstance(old_val, int) and old_val in BRANDS:
            new_data[CONF_BRAND_REGION] = BRANDS[old_val]
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, version=2
        )
        _LOGGER.info(
            "Migrated UConnect config entry from version 1 to 2 (brand_region: %s → %s)",
            old_val,
            new_data.get(CONF_BRAND_REGION),
        )

    return True


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the UConnect integration (YAML config not supported)."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up UConnect from a config entry."""

    _apply_log_level(config_entry)

    coordinator = UconnectDataUpdateCoordinator(hass, config_entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        raise ConfigEntryNotReady(f"Unable to connect to UConnect API: {e}") from e

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.unique_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    async_setup_services(hass, config_entry)

    # Register a listener to handle options updates at runtime
    config_entry.async_on_unload(
        config_entry.add_update_listener(coordinator.update_options)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        del hass.data[DOMAIN][config_entry.unique_id]

    if not hass.data[DOMAIN]:
        async_unload_services(hass)

    return unload_ok
