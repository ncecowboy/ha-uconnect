"""Extrapolated State of Charge sensor for UConnect (T-Mobile) integration.

This sensor predicts the battery charge level between API poll intervals
based on:
- The last known state of charge from the vehicle
- Whether the vehicle is currently charging or driving
- A learned charging rate and drain rate (updated via exponential
  moving average as more data points become available)

A companion UconnectChargingRateSensor exposes the current learned
charging rate in %/h for diagnostic purposes.

The sensor persists its learned state across HA restarts using
RestoreEntity so that accuracy is maintained without waiting for
a full re-learning cycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import callback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

from py_uconnect.client import Vehicle
from py_uconnect.command import COMMAND_DEEP_REFRESH

from .const import DOMAIN
from .coordinator import UconnectDataUpdateCoordinator
from .entity import UconnectEntity

_LOGGER = logging.getLogger(__name__)

# How often to recalculate the extrapolated value
EXTRAPOLATION_UPDATE_INTERVAL = timedelta(minutes=1)

# Correction factor bounds (avoids runaway adjustments)
DEFAULT_CORRECTION_FACTOR = 1.0
MIN_CORRECTION_FACTOR = 0.5
MAX_CORRECTION_FACTOR = 1.5
CORRECTION_EMA_ALPHA = 0.3  # Weight for new observations in EMA

# If the vehicle has been idle for this long, trigger a deep refresh
DEEP_REFRESH_IDLE_THRESHOLD = timedelta(hours=1)

# Minimum data points before trusting the learned rate
MIN_LEARNING_SAMPLES = 3


@dataclass
class _SocState:
    """Persisted SOC learning state."""

    # Latest real SOC reading from the API
    base_soc: float | None = None
    base_timestamp: datetime | None = None

    # Charging mode
    is_charging: bool = False
    charge_rate_pct_per_hour: float | None = None  # learned rate
    charge_rate_samples: int = 0
    charge_correction: float = DEFAULT_CORRECTION_FACTOR
    target_soc: float = 100.0

    # Driving / idle drain mode
    drain_rate_pct_per_hour: float | None = None  # learned rate
    drain_rate_samples: int = 0
    drain_correction: float = DEFAULT_CORRECTION_FACTOR

    # Timestamps
    last_deep_refresh: datetime | None = None


class UconnectExtrapolatedSocSensor(SensorEntity, UconnectEntity, RestoreEntity):
    """Sensor that interpolates the HV battery SOC between API updates."""

    def __init__(
        self,
        coordinator: UconnectDataUpdateCoordinator,
        vehicle: Vehicle,
    ) -> None:
        """Initialise the sensor."""
        UconnectEntity.__init__(self, coordinator, vehicle)
        self._attr_unique_id = f"{DOMAIN}_{vehicle.vin}_extrapolated_soc"
        self._attr_name = (
            f"{vehicle.make} "
            f"{vehicle.nickname or vehicle.model} HV Battery Charge (Extrapolated)"
        )
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:battery-sync"

        self._state = _SocState()
        self._unsub_timer = None

    # ------------------------------------------------------------------
    # HA lifecycle
    # ------------------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        """Restore previous state and start the update timer."""
        await super().async_added_to_hass()

        # Attempt to restore persisted learning state
        last_state = await self.async_get_last_state()
        if last_state and last_state.attributes:
            self._restore_from_attributes(last_state.attributes)

        # Subscribe to coordinator updates
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

        # Start the per-minute extrapolation timer
        self._unsub_timer = async_track_time_interval(
            self.hass,
            self._async_update_extrapolated,
            EXTRAPOLATION_UPDATE_INTERVAL,
        )
        self.async_on_remove(self._cancel_timer)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up the timer on removal."""
        self._cancel_timer()

    def _cancel_timer(self) -> None:
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None

    # ------------------------------------------------------------------
    # Coordinator update handler
    # ------------------------------------------------------------------

    @callback
    def _handle_coordinator_update(self) -> None:
        """Process a fresh data update from the coordinator."""
        try:
            vehicle = self.vehicle
        except KeyError:
            return

        current_soc = vehicle.state_of_charge
        if current_soc is None:
            return

        now = datetime.now(timezone.utc)
        s = self._state

        if s.base_soc is not None and s.base_timestamp is not None:
            elapsed_hours = (now - s.base_timestamp).total_seconds() / 3600.0
            if elapsed_hours > 0:
                actual_delta = current_soc - s.base_soc

                if s.is_charging and actual_delta > 0:
                    # Learn charging rate
                    measured_rate = actual_delta / elapsed_hours
                    if s.charge_rate_pct_per_hour is None:
                        s.charge_rate_pct_per_hour = measured_rate
                    else:
                        s.charge_rate_pct_per_hour = (
                            CORRECTION_EMA_ALPHA * measured_rate
                            + (1 - CORRECTION_EMA_ALPHA) * s.charge_rate_pct_per_hour
                        )
                    s.charge_rate_samples += 1

                    # Update correction factor
                    extrapolated = self.native_value
                    if extrapolated is not None and extrapolated != current_soc:
                        correction = current_soc / max(extrapolated, 0.1)
                        s.charge_correction = max(
                            MIN_CORRECTION_FACTOR,
                            min(
                                MAX_CORRECTION_FACTOR,
                                CORRECTION_EMA_ALPHA * correction
                                + (1 - CORRECTION_EMA_ALPHA) * s.charge_correction,
                            ),
                        )

                elif not s.is_charging and actual_delta < 0:
                    # Learn drain rate
                    measured_rate = abs(actual_delta) / elapsed_hours
                    if s.drain_rate_pct_per_hour is None:
                        s.drain_rate_pct_per_hour = measured_rate
                    else:
                        s.drain_rate_pct_per_hour = (
                            CORRECTION_EMA_ALPHA * measured_rate
                            + (1 - CORRECTION_EMA_ALPHA) * s.drain_rate_pct_per_hour
                        )
                    s.drain_rate_samples += 1

        # Update baseline
        s.base_soc = current_soc
        s.base_timestamp = now
        s.is_charging = bool(vehicle.charging)
        if hasattr(vehicle, "state_of_charge_target"):
            s.target_soc = vehicle.state_of_charge_target or 100.0

        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Timer-driven extrapolation
    # ------------------------------------------------------------------

    @callback
    def _async_update_extrapolated(self, _now=None) -> None:
        """Recalculate the extrapolated value and trigger a state write."""
        self.async_write_ha_state()

        # Schedule a deep refresh if the vehicle has been idle long enough
        s = self._state
        if (
            s.base_timestamp is not None
            and not s.is_charging
            and (datetime.now(timezone.utc) - s.base_timestamp)
            >= DEEP_REFRESH_IDLE_THRESHOLD
            and (
                s.last_deep_refresh is None
                or (datetime.now(timezone.utc) - s.last_deep_refresh)
                >= DEEP_REFRESH_IDLE_THRESHOLD
            )
        ):
            s.last_deep_refresh = datetime.now(timezone.utc)
            async_call_later(self.hass, 0, self._async_trigger_deep_refresh)

    async def _async_trigger_deep_refresh(self, _now=None) -> None:
        """Send a deep refresh command to the vehicle."""
        try:
            await self.coordinator.async_command(self._vin, COMMAND_DEEP_REFRESH)
        except Exception as err:
            _LOGGER.debug("Deep refresh failed: %s", err)

    # ------------------------------------------------------------------
    # Value calculation
    # ------------------------------------------------------------------

    @property
    def native_value(self) -> float | None:
        """Return the extrapolated SOC."""
        s = self._state
        if s.base_soc is None or s.base_timestamp is None:
            return None

        now = datetime.now(timezone.utc)
        elapsed_hours = (now - s.base_timestamp).total_seconds() / 3600.0

        if s.is_charging:
            return self._extrapolate_charging(s, elapsed_hours)
        return self._extrapolate_draining(s, elapsed_hours)

    @staticmethod
    def _extrapolate_charging(s: _SocState, elapsed_hours: float) -> float:
        """Estimate SOC while charging."""
        if s.charge_rate_pct_per_hour is None:
            return round(s.base_soc, 1)

        rate = s.charge_rate_pct_per_hour
        correction = (
            s.charge_correction if s.charge_rate_samples >= MIN_LEARNING_SAMPLES
            else DEFAULT_CORRECTION_FACTOR
        )
        extrapolated = s.base_soc + rate * correction * elapsed_hours
        extrapolated = min(extrapolated, s.target_soc)
        return round(extrapolated, 1)

    @staticmethod
    def _extrapolate_draining(s: _SocState, elapsed_hours: float) -> float:
        """Estimate SOC while driving / idle."""
        if s.drain_rate_pct_per_hour is None:
            return round(s.base_soc, 1)

        rate = s.drain_rate_pct_per_hour
        correction = (
            s.drain_correction if s.drain_rate_samples >= MIN_LEARNING_SAMPLES
            else DEFAULT_CORRECTION_FACTOR
        )
        extrapolated = s.base_soc - rate * correction * elapsed_hours
        extrapolated = max(0.0, extrapolated)
        return round(extrapolated, 1)

    # ------------------------------------------------------------------
    # Learning reset
    # ------------------------------------------------------------------

    def reset_learning(self) -> None:
        """Reset all learned charging and drain rate parameters."""
        s = self._state
        s.charge_rate_pct_per_hour = None
        s.charge_rate_samples = 0
        s.charge_correction = DEFAULT_CORRECTION_FACTOR
        s.drain_rate_pct_per_hour = None
        s.drain_rate_samples = 0
        s.drain_correction = DEFAULT_CORRECTION_FACTOR
        _LOGGER.info("Battery learning reset for %s", self._vin)
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # State persistence (extra_state_attributes / restore)
    # ------------------------------------------------------------------

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose learning state for persistence and diagnostics."""
        s = self._state
        return {
            "base_soc": s.base_soc,
            "base_timestamp": s.base_timestamp.isoformat() if s.base_timestamp else None,
            "is_charging": s.is_charging,
            "charge_rate_pct_per_hour": s.charge_rate_pct_per_hour,
            "charge_rate_samples": s.charge_rate_samples,
            "charge_correction": s.charge_correction,
            "target_soc": s.target_soc,
            "drain_rate_pct_per_hour": s.drain_rate_pct_per_hour,
            "drain_rate_samples": s.drain_rate_samples,
            "drain_correction": s.drain_correction,
        }

    def _restore_from_attributes(self, attrs: dict[str, Any]) -> None:
        """Restore learning state from persisted HA attributes."""
        s = self._state
        try:
            s.base_soc = attrs.get("base_soc")
            raw_ts = attrs.get("base_timestamp")
            s.base_timestamp = (
                datetime.fromisoformat(raw_ts) if raw_ts else None
            )
            s.is_charging = bool(attrs.get("is_charging", False))
            s.charge_rate_pct_per_hour = attrs.get("charge_rate_pct_per_hour")
            s.charge_rate_samples = int(attrs.get("charge_rate_samples", 0))
            s.charge_correction = float(
                attrs.get("charge_correction", DEFAULT_CORRECTION_FACTOR)
            )
            s.target_soc = float(attrs.get("target_soc", 100.0))
            s.drain_rate_pct_per_hour = attrs.get("drain_rate_pct_per_hour")
            s.drain_rate_samples = int(attrs.get("drain_rate_samples", 0))
            s.drain_correction = float(
                attrs.get("drain_correction", DEFAULT_CORRECTION_FACTOR)
            )
        except Exception as err:
            _LOGGER.warning("Failed to restore battery learning state: %s", err)


class UconnectChargingRateSensor(SensorEntity, UconnectEntity):
    """Diagnostic sensor exposing the learned EV charging rate in %/h."""

    def __init__(
        self,
        coordinator: UconnectDataUpdateCoordinator,
        vehicle: Vehicle,
    ) -> None:
        """Initialise the sensor."""
        UconnectEntity.__init__(self, coordinator, vehicle)
        self._attr_unique_id = f"{DOMAIN}_{vehicle.vin}_charging_rate"
        self._attr_name = (
            f"{vehicle.make} "
            f"{vehicle.nickname or vehicle.model} Charging Rate"
        )
        self._attr_native_unit_of_measurement = "%/h"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_entity_registry_enabled_default = False  # disabled by default

    @property
    def native_value(self) -> float | None:
        """Return the learned charging rate."""
        soc_sensor = self.coordinator.extrapolated_soc_sensors.get(self._vin)
        if soc_sensor is None:
            return None
        return soc_sensor._state.charge_rate_pct_per_hour
