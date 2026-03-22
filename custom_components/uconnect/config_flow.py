"""Config flow for UConnect (T-Mobile) integration."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from py_uconnect.api import API
from py_uconnect.brands import BRANDS as BRANDS_BY_NAME

from .const import (
    CONF_BRAND_REGION,
    CONF_DISABLE_TLS_VERIFICATION,
    CONF_ADD_COMMAND_ENTITIES,
    CONF_LOG_LEVEL,
    DEFAULT_LOG_LEVEL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_PIN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_PIN, default=DEFAULT_PIN): str,
        vol.Required(CONF_DISABLE_TLS_VERIFICATION, default=False): bool,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_SCAN_INTERVAL,
            default=DEFAULT_SCAN_INTERVAL,
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=999)),
        vol.Optional(CONF_PIN, default=DEFAULT_PIN): str,
        vol.Required(CONF_ADD_COMMAND_ENTITIES, default=False): bool,
        vol.Optional(CONF_LOG_LEVEL, default=DEFAULT_LOG_LEVEL): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="debug", label="Debug"),
                    selector.SelectOptionDict(value="info", label="Info"),
                    selector.SelectOptionDict(value="warning", label="Warning"),
                    selector.SelectOptionDict(value="error", label="Error"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


async def _detect_brand(
    hass: HomeAssistant,
    email: str,
    password: str,
    pin: str,
    disable_tls_verification: bool,
) -> tuple[str | None, bool]:
    """Try every known brand to find one where credentials work and vehicles exist.

    Returns a tuple of:
      - brand_name (str): the detected brand name, or None if not found
      - any_login_succeeded (bool): True if at least one brand accepted the credentials
    """
    any_login_succeeded = False

    for brand in BRANDS_BY_NAME.values():
        try:
            api = API(
                email=email,
                password=password,
                pin=pin,
                brand=brand,
                disable_tls_verification=disable_tls_verification,
            )
            await hass.async_add_executor_job(api.login)
            any_login_succeeded = True
            vehicles = await hass.async_add_executor_job(api.list_vehicles)
            if vehicles:
                _LOGGER.debug("Auto-detected brand: %s", brand.name)
                return brand.name, True
        except Exception as err:
            _LOGGER.debug(
                "Brand %s: login or vehicle fetch failed, trying next: %s",
                brand.name,
                err,
            )

    return None, any_login_succeeded


async def validate_input(hass: HomeAssistant, user_input: dict[str, Any]) -> str:
    """Validate credentials, auto-detect the brand, and return the brand name."""

    brand_name, any_login_succeeded = await _detect_brand(
        hass,
        email=user_input[CONF_USERNAME],
        password=user_input[CONF_PASSWORD],
        pin=user_input.get(CONF_PIN, DEFAULT_PIN),
        disable_tls_verification=user_input.get(CONF_DISABLE_TLS_VERIFICATION, False),
    )

    if brand_name is None:
        if any_login_succeeded:
            raise NoVehicles
        raise InvalidAuth

    return brand_name


class UconnectOptionFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for UConnect."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options init setup."""

        if user_input is not None:
            return self.async_create_entry(
                title=self._config_entry.title, data=user_input
            )

        return self.async_show_form(
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self._config_entry.options
            ),
        )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UConnect (T-Mobile)."""

    VERSION = 2
    reauth_entry: ConfigEntry | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Return the options flow handler."""
        return UconnectOptionFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""

        if user_input is None:
            return self.async_show_form(
                data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            brand_name = await validate_input(self.hass, user_input)
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except NoVehicles:
            errors["base"] = "no_vehicles"
        except Exception:
            _LOGGER.exception("Unexpected exception during setup")
            errors["base"] = "unknown"
        else:
            # Persist the auto-detected brand so the coordinator can use it
            user_input = {**user_input, CONF_BRAND_REGION: brand_name}

            if self.reauth_entry is None:
                title = f"{brand_name} {user_input[CONF_USERNAME]}"
                await self.async_set_unique_id(
                    hashlib.sha256(user_input[CONF_USERNAME].encode("utf-8")).hexdigest()
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=title, data=user_input)
            else:
                self.hass.config_entries.async_update_entry(
                    self.reauth_entry, data=user_input
                )
                await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an API authentication error."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({}),
            )
        return await self.async_step_user()


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class NoVehicles(HomeAssistantError):
    """Error to indicate credentials are valid but no vehicles were found."""
