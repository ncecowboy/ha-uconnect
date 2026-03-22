"""Legacy brand definitions for older UConnect Access vehicles (2013–2018 era).

Background
----------
Stellantis vehicles from roughly 2013–2018 shipped with **UConnect Access**
connected-services modems that operated over the now-defunct Sprint 3G network.
When Sprint's 3G network was retired in 2022, these vehicles lost cellular
connectivity until owners installed the T-Mobile 4G OBD Adapter.

The older UConnect Access portal (connect.ramtrucks.com, connect.dodge.com,
connect.chrysler.com, connect.jeep.com) used *different Gigya authentication
API keys* from the current Stellantis GSDP portal (login-us.ramtrucks.com,
login-us.dodge.com, etc.).  Vehicles originally registered under the older
portal's Gigya tenant may not appear when py-uconnect authenticates via the
newer tenant — even though both ultimately route to the same GSDP back-end.

This module defines ``Brand`` objects that use the older Gigya API keys so the
brand-detection code can try them as a fallback when no vehicles are found with
the current keys.  The API (backend) configuration is identical to the current
brands — only the Gigya authentication key and login URL differ.

References
----------
* The legacy Gigya keys were obtained by reverse-engineering the FiatChamp
  Home Assistant add-on (https://github.com/wubbl0rz/FiatChamp) which
  predates the current py-uconnect library and uses the older key set.
* Confirmed to differ from the py-uconnect 0.3.x DODGE_US key.
"""

from py_uconnect.brands import (
    API_US,
    AUTH_US,
    TOKEN_URL_US,
    LOCALE_US,
    REGION_US,
    Brand,
)

# ---------------------------------------------------------------------------
# Legacy Gigya key discovered in FiatChamp (older UConnect Access era).
# FiatChamp used this single key for both Dodge and Fiat US before the brands
# were migrated to individual, per-brand keys in the current GSDP system.
# ---------------------------------------------------------------------------
_LEGACY_UCONNECT_ACCESS_KEY = "3_etlYkCXNEhz4_KJVYDqnK1CqxQjvJStJMawBohJU2ch3kp30b0QCJtLCzxJ93N-M"

DODGE_US_LEGACY = Brand(
    name="DODGE_US_LEGACY",
    region=REGION_US,
    login_api_key=_LEGACY_UCONNECT_ACCESS_KEY,
    login_url="https://login-us.dodge.com",
    token_url=TOKEN_URL_US,
    api=API_US,
    auth=AUTH_US,
    locale=LOCALE_US,
)
"""Legacy Dodge US brand using the older UConnect Access Gigya API key.

Used as a fallback when the current DODGE_US key returns no vehicles.  This
may succeed for 2013–2018 Dodge vehicles (Charger, Challenger, Durango) that
were originally enrolled through the older ``connect.dodge.com`` portal and
have since been connected via the T-Mobile 4G OBD Adapter.
"""

CHRYSLER_US_LEGACY = Brand(
    name="CHRYSLER_US_LEGACY",
    region=REGION_US,
    login_api_key=_LEGACY_UCONNECT_ACCESS_KEY,
    login_url="https://login-us.chrysler.com",
    token_url=TOKEN_URL_US,
    api=API_US,
    auth=AUTH_US,
    locale=LOCALE_US,
)
"""Legacy Chrysler US brand using the older UConnect Access Gigya API key.

Used as a fallback for 2015–2018 Chrysler vehicles (300, Pacifica) that may
have been originally enrolled under the older ``connect.chrysler.com`` portal.
"""

LEGACY_BRANDS: dict[str, Brand] = {
    DODGE_US_LEGACY.name: DODGE_US_LEGACY,
    CHRYSLER_US_LEGACY.name: CHRYSLER_US_LEGACY,
}
"""All legacy brand definitions keyed by brand name.

These are tried as a fallback by :mod:`brand_detection` after all current
py-uconnect brands have been attempted without finding any vehicles.
"""
