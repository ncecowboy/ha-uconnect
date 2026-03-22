"""Base Entity for UConnect (T-Mobile) integration."""

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from py_uconnect.client import Vehicle

from .const import DOMAIN
from .coordinator import UconnectDataUpdateCoordinator


class UconnectEntity(CoordinatorEntity):
    """Base entity class for UConnect integration."""

    def __init__(self, coordinator: UconnectDataUpdateCoordinator, vehicle: Vehicle):
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._vin = vehicle.vin

    @property
    def vehicle(self) -> Vehicle:
        """Return the current vehicle object from the coordinator."""
        vehicles = self.coordinator.client.get_vehicles()
        vehicle = vehicles.get(self._vin)
        if vehicle is None:
            raise KeyError(
                f"Vehicle {self._vin} not found in coordinator data. "
                "The vehicle may have been removed from the account."
            )
        return vehicle

    @property
    def device_info(self):
        """Return device information for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.vehicle.vin)},
            manufacturer=self.vehicle.make,
            model=self.vehicle.model,
            name=f"{self.vehicle.make} {self.vehicle.nickname or self.vehicle.model}",
        )
