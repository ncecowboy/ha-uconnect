"""Brand auto-detection helper for the UConnect integration.

This module is shared by config_flow (for initial setup) and by __init__
(for runtime recovery when the stored brand yields no vehicles).  Keeping it
here avoids a circular import between those two modules and makes the helper
accessible without reaching into a UI-layer private symbol.

Detection strategy
------------------
1. Try all current py-uconnect brands (modern Stellantis GSDP system).
2. If no vehicles are found with any current brand, fall back to the legacy
   UConnect Access brand variants defined in :mod:`legacy_brands`.  These use
   the older Gigya API keys that were in use before Stellantis consolidated
   authentication onto the current ``login-us.*`` endpoints.  Some 2013–2018
   era vehicles (Dodge, Chrysler) may have account registrations tied to these
   older keys.
"""

from __future__ import annotations

import logging

from py_uconnect.api import API
from py_uconnect.brands import BRANDS as BRANDS_BY_NAME

from homeassistant.core import HomeAssistant

from .legacy_brands import LEGACY_BRANDS

_LOGGER = logging.getLogger(__name__)


async def detect_brand(
    hass: HomeAssistant,
    email: str,
    password: str,
    pin: str,
    disable_tls_verification: bool,
) -> tuple[str | None, bool]:
    """Try every known brand to find one where credentials work and vehicles exist.

    First tries all current py-uconnect brands; if none return vehicles, falls
    back to the legacy UConnect Access brands for older vehicles.

    Returns a tuple of:
      - brand_name (str): the detected brand name, or None if not found
      - any_login_succeeded (bool): True if at least one brand accepted the credentials
    """
    any_login_succeeded = False

    # Phase 1 — current Stellantis GSDP brands
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

    # Phase 2 — legacy UConnect Access brands (older Gigya API keys)
    # These are always attempted after Phase 1.  They use the authentication
    # keys that were active on the older UConnect Access portals
    # (connect.dodge.com, connect.chrysler.com) for 2013–2018 era vehicles.
    # A vehicle enrolled under the legacy Gigya tenant may not appear even
    # when Phase 1 login succeeds because the two tenants hold separate
    # vehicle registrations.
    _LOGGER.debug(
        "Trying legacy UConnect Access brands for older 2013–2018 era vehicles"
    )

    for brand in LEGACY_BRANDS.values():
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
                _LOGGER.debug(
                    "Auto-detected legacy brand: %s (older UConnect Access key)",
                    brand.name,
                )
                return brand.name, True
        except Exception as err:
            _LOGGER.debug(
                "Legacy brand %s: login or vehicle fetch failed, trying next: %s",
                brand.name,
                err,
            )

    return None, any_login_succeeded
