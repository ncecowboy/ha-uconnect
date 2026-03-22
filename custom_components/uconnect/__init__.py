"""UConnect (T-Mobile) Home Assistant integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_PIN, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .brand_detection import detect_brand
from .const import (
    BRANDS,
    CONF_BRAND_REGION,
    CONF_DISABLE_TLS_VERIFICATION,
    CONF_LOG_LEVEL,
    DEFAULT_LOG_LEVEL,
    DEFAULT_PIN,
    DOMAIN,
)
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

    # If the initial refresh succeeded but returned no vehicles, the stored brand
    # may be stale or wrong.  Try every known brand to find one that returns
    # vehicles and, if a better brand is found, update the config entry so all
    # subsequent refreshes use it automatically.
    if not coordinator.client.get_vehicles():
        current_brand = config_entry.data.get(CONF_BRAND_REGION)
        _LOGGER.warning(
            "No vehicles found for brand %r. "
            "Attempting brand auto-detection across all known brands…",
            current_brand,
        )

        # Resolve the effective PIN using the same options-first logic as the
        # coordinator so that a PIN updated in options is honoured here too.
        pin_options = config_entry.options.get(CONF_PIN)
        effective_pin = (
            pin_options
            if pin_options is not None and pin_options != ""
            else config_entry.data.get(CONF_PIN, DEFAULT_PIN)
        )

        new_brand, any_login = await detect_brand(
            hass,
            email=config_entry.data.get(CONF_USERNAME, ""),
            password=config_entry.data.get(CONF_PASSWORD, ""),
            pin=effective_pin,
            disable_tls_verification=config_entry.data.get(
                CONF_DISABLE_TLS_VERIFICATION, False
            ),
        )

        if new_brand and new_brand != current_brand:
            _LOGGER.info(
                "Brand auto-detection found vehicles under %r "
                "(was %r). Updating config entry.",
                new_brand,
                current_brand,
            )
            hass.config_entries.async_update_entry(
                config_entry,
                data={**config_entry.data, CONF_BRAND_REGION: new_brand},
            )
            # Re-initialize the coordinator with the corrected brand.
            # The previous coordinator was never stored in hass.data yet,
            # so replacing the local reference here is safe.
            coordinator = UconnectDataUpdateCoordinator(hass, config_entry)
            try:
                await coordinator.async_config_entry_first_refresh()
            except Exception as e:
                raise ConfigEntryNotReady(
                    f"Unable to connect to UConnect API after brand update: {e}"
                ) from e
        elif not any_login:
            raise ConfigEntryAuthFailed(
                "Login failed for all known brands. "
                "Please check your UConnect credentials and reconfigure the integration."
            )
        else:
            _LOGGER.warning(
                "No vehicles were found for any known brand. "
                "Your vehicle may not be registered with the UConnect service, "
                "or your subscription may have expired. "
                "Please verify your vehicle is registered in the UConnect (or Mopar) "
                "app and try again."
            )

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
