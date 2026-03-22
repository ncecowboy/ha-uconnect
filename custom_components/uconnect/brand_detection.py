"""Brand auto-detection helper for the UConnect integration.

This module is shared by config_flow (for initial setup) and by __init__
(for runtime recovery when the stored brand yields no vehicles).  Keeping it
here avoids a circular import between those two modules and makes the helper
accessible without reaching into a UI-layer private symbol.
"""

from __future__ import annotations

import logging

from py_uconnect.api import API
from py_uconnect.brands import BRANDS as BRANDS_BY_NAME

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def detect_brand(
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
