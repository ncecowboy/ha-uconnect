"""Button platform for UConnect (T-Mobile) integration.

Provides one-shot action buttons:
- Refresh Location   – request an updated GPS fix
- Deep Refresh       – force a battery-level update from the vehicle
- Charge Now         – initiate EV charging
- Lights             – blink lights
- Lights & Horn      – blink lights and sound horn
- Update Data        – refresh all vehicle data from the cloud
- Reset Battery Learning – reset the extrapolated-SOC learned parameters

Command buttons are only added when "Add command entities" is enabled.
The Reset Battery Learning button is always available for EVs/PHEVs.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Final

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntityDescription,
    ButtonEntity,
)

from py_uconnect.client import Vehicle
from py_uconnect.command import (
    COMMAND_REFRESH_LOCATION,
    COMMAND_DEEP_REFRESH,
    COMMAND_CHARGE,
    COMMAND_LIGHTS,
    COMMAND_LIGHTS_HORN,
    Command,
)

from .const import DOMAIN, CONF_ADD_COMMAND_ENTITIES
from .coordinator import UconnectDataUpdateCoordinator
from .entity import UconnectEntity


@dataclass
class UconnectButtonEntityDescription(ButtonEntityDescription):
    """A class that describes custom button entities."""

    command: Command | None = None


BUTTON_DESCRIPTIONS: Final[tuple[UconnectButtonEntityDescription, ...]] = (
    UconnectButtonEntityDescription(
        key="button_location",
        name="Refresh Location",
        icon="mdi:crosshairs-gps",
        command=COMMAND_REFRESH_LOCATION,
        device_class=ButtonDeviceClass.UPDATE,
    ),
    UconnectButtonEntityDescription(
        key="button_deep_refresh",
        name="Deep Refresh",
        icon="mdi:refresh",
        command=COMMAND_DEEP_REFRESH,
        device_class=ButtonDeviceClass.UPDATE,
    ),
    UconnectButtonEntityDescription(
        key="button_charge",
        name="Charge Now",
        icon="mdi:ev-station",
        command=COMMAND_CHARGE,
        device_class=ButtonDeviceClass.UPDATE,
    ),
    UconnectButtonEntityDescription(
        key="button_lights",
        name="Lights",
        icon="mdi:car-light-dimmed",
        command=COMMAND_LIGHTS,
        device_class=ButtonDeviceClass.UPDATE,
    ),
    UconnectButtonEntityDescription(
        key="button_lights_horn",
        name="Lights & Horn",
        icon="mdi:bugle",
        command=COMMAND_LIGHTS_HORN,
        device_class=ButtonDeviceClass.UPDATE,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button platform."""
    coordinator: UconnectDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.unique_id
    ]
    entities = []

    # EV-only button: always available regardless of command-entities setting
    for vehicle in coordinator.client.vehicles.values():
        if vehicle.vin in coordinator.extrapolated_soc_sensors:
            entities.append(UconnectResetLearningButton(coordinator, vehicle))

    # Command buttons – only when the option is enabled
    if config_entry.options.get(CONF_ADD_COMMAND_ENTITIES):
        for vehicle in coordinator.client.vehicles.values():
            entities.append(UconnectButtonUpdate(coordinator, vehicle))
            for description in BUTTON_DESCRIPTIONS:
                if description.command.name in vehicle.supported_commands:
                    entities.append(UconnectButton(coordinator, description, vehicle))

    async_add_entities(entities)
    return True


class UconnectButton(ButtonEntity, UconnectEntity):
    """A button that sends a single command to the vehicle."""

    def __init__(
        self,
        coordinator: UconnectDataUpdateCoordinator,
        description: UconnectButtonEntityDescription,
        vehicle: Vehicle,
    ):
        """Initialize the button entity."""
        UconnectEntity.__init__(self, coordinator, vehicle)
        self.entity_description: UconnectButtonEntityDescription = description
        self._attr_name = (
            f"{vehicle.make} "
            f"{vehicle.nickname or vehicle.model} "
            f"{description.name}"
        )
        self._attr_unique_id = f"{DOMAIN}_{vehicle.vin}_{description.key}"

    @property
    def icon(self):
        """Return the button icon."""
        return self.entity_description.icon

    async def async_press(self, **kwargs):
        """Send the command to the vehicle."""
        await self.coordinator.async_command(
            self.vehicle.vin, self.entity_description.command
        )


class UconnectButtonUpdate(ButtonEntity, UconnectEntity):
    """Button that triggers a data refresh from the UConnect cloud."""

    def __init__(
        self,
        coordinator: UconnectDataUpdateCoordinator,
        vehicle: Vehicle,
    ):
        """Initialize the update button."""
        UconnectEntity.__init__(self, coordinator, vehicle)
        self._attr_name = (
            f"{vehicle.make} "
            f"{vehicle.nickname or vehicle.model} Update Data"
        )
        self._attr_unique_id = f"{DOMAIN}_{vehicle.vin}_update"

    @property
    def icon(self):
        """Return the update icon."""
        return "mdi:update"

    async def async_press(self, **kwargs):
        """Trigger a coordinator data refresh."""
        await self.coordinator.async_refresh()


class UconnectResetLearningButton(ButtonEntity, UconnectEntity):
    """Button to reset learned battery charging and drain parameters."""

    def __init__(
        self,
        coordinator: UconnectDataUpdateCoordinator,
        vehicle: Vehicle,
    ):
        """Initialize the reset button."""
        UconnectEntity.__init__(self, coordinator, vehicle)
        self._attr_name = (
            f"{vehicle.make} {vehicle.nickname or vehicle.model} "
            "Reset Battery Learning"
        )
        self._attr_unique_id = f"{DOMAIN}_{vehicle.vin}_reset_battery_learning"
        self._attr_icon = "mdi:head-sync-outline"

    async def async_press(self, **kwargs):
        """Reset learned SOC parameters."""
        sensor = self.coordinator.extrapolated_soc_sensors.get(self._vin)
        if sensor is not None:
            sensor.reset_learning()
