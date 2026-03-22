"""Device tracker platform for UConnect (T-Mobile) integration.

Tracks vehicle GPS location using data from the UConnect cloud API.
Corresponds to the PSA API lastPosition endpoint which returns
latitude, longitude and a timestamp for the last known location.
"""

from __future__ import annotations

from py_uconnect.client import Vehicle

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import UconnectDataUpdateCoordinator
from .entity import UconnectEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device_tracker platform."""
    coordinator: UconnectDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.unique_id
    ]
    entities = []
    for vehicle in coordinator.client.vehicles.values():
        if vehicle.location is not None:
            entities.append(UconnectTracker(coordinator, vehicle))

    async_add_entities(entities)
    return True


class UconnectTracker(TrackerEntity, UconnectEntity):
    """Tracks the GPS position of a UConnect-enabled vehicle."""

    def __init__(
        self,
        coordinator: UconnectDataUpdateCoordinator,
        vehicle: Vehicle,
    ):
        """Initialize the tracker."""
        UconnectEntity.__init__(self, coordinator, vehicle)
        self._attr_unique_id = f"{DOMAIN}_{vehicle.vin}_location"
        self._attr_name = (
            f"{vehicle.make} "
            f"{vehicle.nickname or vehicle.model} Location"
        )
        self._attr_icon = "mdi:map-marker-outline"

    @property
    def latitude(self):
        """Return the latitude of the vehicle."""
        if self.vehicle.location is None:
            return None
        return self.vehicle.location.latitude

    @property
    def longitude(self):
        """Return the longitude of the vehicle."""
        if self.vehicle.location is None:
            return None
        return self.vehicle.location.longitude

    @property
    def battery_level(self):
        """Return the HV battery level (for EVs) or None."""
        return self.vehicle.state_of_charge

    @property
    def source_type(self):
        """Return GPS as the source type."""
        return SourceType.GPS
