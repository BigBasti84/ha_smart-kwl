"""Sensor entities for Smart KWL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_EXHAUST_TEMPERATURE_ENTITY,
    CONF_INCOMING_TEMPERATURE_ENTITY,
    CONF_OUTGOING_TEMPERATURE_ENTITY,
    CONF_OUTSIDE_TEMPERATURE_ENTITY,
    DOMAIN,
)
from .controller import SmartKwlController


@dataclass(slots=True)
class TemperatureEntityConfig:
    key: str
    name: str
    unique_suffix: str


TEMP_CONFIGS: tuple[TemperatureEntityConfig, ...] = (
    TemperatureEntityConfig(CONF_INCOMING_TEMPERATURE_ENTITY, "Incoming Temperature", "incoming_temperature"),
    TemperatureEntityConfig(CONF_OUTGOING_TEMPERATURE_ENTITY, "Outgoing Temperature", "outgoing_temperature"),
    TemperatureEntityConfig(CONF_OUTSIDE_TEMPERATURE_ENTITY, "Outside Temperature", "outside_temperature"),
    TemperatureEntityConfig(CONF_EXHAUST_TEMPERATURE_ENTITY, "Exhaust Temperature", "exhaust_temperature"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart KWL sensors from config entry."""
    controller: SmartKwlController = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        SmartKwlDiagnosticSensor(controller, entry, "Target Fan Level", "target_fan_level", "target_level"),
        SmartKwlDiagnosticSensor(controller, entry, "Target Fan Percentage", "target_fan_percentage", "target_percentage"),
        SmartKwlDiagnosticSensor(controller, entry, "Humidity Combined", "humidity_combined", "humidity_combined", "%"),
        SmartKwlDiagnosticSensor(controller, entry, "Humidity Low", "humidity_low", "humidity_low", "%"),
        SmartKwlDiagnosticSensor(controller, entry, "Humidity High", "humidity_high", "humidity_high", "%"),
        SmartKwlDiagnosticSensor(controller, entry, "CO2 Combined", "co2_combined", "co2_combined", "ppm"),
        SmartKwlDiagnosticSensor(controller, entry, "CO2 Low", "co2_low", "co2_low", "ppm"),
        SmartKwlDiagnosticSensor(controller, entry, "CO2 High", "co2_high", "co2_high", "ppm"),
        SmartKwlDiagnosticSensor(controller, entry, "Manual Override Level", "manual_override_level_status", "manual_override_level"),
        SmartKwlDiagnosticSensor(controller, entry, "Manual Override Until", "manual_override_until", "manual_override_until"),
        SmartKwlDiagnosticSensor(controller, entry, "External Manual Hold", "external_manual_hold", "external_manual_hold"),
        SmartKwlCheckLogSensor(controller, entry),
        SmartKwlFilterSensor(controller, entry, "Filter Days Since Cleaning", "filter_days_since_cleaning", "filter_days_since_cleaning", "d"),
        SmartKwlFilterSensor(controller, entry, "Filter Days Remaining", "filter_days_remaining", "filter_days_remaining_life", "d"),
        SmartKwlFilterSensor(controller, entry, "Filter Months Remaining", "filter_months_remaining", "filter_months_remaining"),
        SmartKwlFilterSensor(controller, entry, "Filter Cleaning Status", "filter_cleaning_status", "filter_cleaning_status"),
        SmartKwlFilterSensor(controller, entry, "Filter Last Cleaned", "filter_last_cleaned", "filter_last_cleaned"),
        SmartKwlFilterSensor(controller, entry, "Filter Lifetime Source", "filter_lifetime_source", "filter_lifetime_entity"),
    ]

    for cfg in TEMP_CONFIGS:
        source_entity = entry.options.get(cfg.key, entry.data.get(cfg.key))
        if source_entity:
            entities.append(SmartKwlTemperatureSensor(controller, entry, cfg.name, cfg.unique_suffix, source_entity))

    async_add_entities(entities)


class SmartKwlBaseEntity(RestoreEntity):
    """Base entity for Smart KWL info entities."""

    _attr_has_entity_name = False

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry, name: str, unique_suffix: str) -> None:
        self._controller = controller
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_object_id = f"{DOMAIN}_{unique_suffix}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Smart KWL",
        )
        self._remove_listener = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._remove_listener = self._controller.add_listener(self._handle_controller_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener:
            self._remove_listener()
            self._remove_listener = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_controller_update(self) -> None:
        self.async_write_ha_state()


class SmartKwlDiagnosticSensor(SmartKwlBaseEntity, SensorEntity):
    """Expose controller diagnostics as sensors."""

    def __init__(
        self,
        controller: SmartKwlController,
        entry: ConfigEntry,
        name: str,
        unique_suffix: str,
        status_key: str,
        unit: str | None = None,
    ) -> None:
        super().__init__(controller, entry, name, unique_suffix)
        self._status_key = status_key
        self._last_value: Any = None
        if unit is not None:
            self._attr_native_unit_of_measurement = unit

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state not in {"unknown", "unavailable", "none"}:
            self._last_value = state.state

    @property
    def native_value(self) -> Any:
        value = self._controller.status.get(self._status_key)
        if value is None:
            return self._last_value
        self._last_value = value
        return value


class SmartKwlCheckLogSensor(SmartKwlBaseEntity, SensorEntity):
    """Expose the last 10 regular check results as text attributes."""

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry) -> None:
        super().__init__(controller, entry, "Check Log", "check_log")

    @property
    def native_value(self) -> str:
        return str(self._controller.status.get("last_action_line") or "no_checks_yet")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "target_level": self._controller.status.get("target_level"),
            "default_level": self._controller.status.get("default_level"),
            "base_level": self._controller.status.get("base_level"),
            "summer_heat_active": self._controller.status.get("summer_heat_active"),
            "last_reason": self._controller.status.get("last_reason"),
            "last_check_lines": self._controller.status.get("last_check_lines", []),
            "check_history": self._controller.status.get("check_history", []),
            "change_history": self._controller.status.get("change_history", []),
        }


class SmartKwlTemperatureSensor(SmartKwlBaseEntity, SensorEntity):
    """Mirror configured source temperature sensors."""

    def __init__(
        self,
        controller: SmartKwlController,
        entry: ConfigEntry,
        name: str,
        unique_suffix: str,
        source_entity: str,
    ) -> None:
        super().__init__(controller, entry, name, unique_suffix)
        self._source_entity = source_entity

    @property
    def native_value(self) -> float | None:
        state = self.hass.states.get(self._source_entity)
        if state is None:
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        state = self.hass.states.get(self._source_entity)
        if state is None:
            return None
        unit = state.attributes.get("unit_of_measurement")
        return str(unit) if unit is not None else None


class SmartKwlFilterSensor(SmartKwlBaseEntity, SensorEntity):
    """Expose filter maintenance data as sensors."""

    def __init__(
        self,
        controller: SmartKwlController,
        entry: ConfigEntry,
        name: str,
        unique_suffix: str,
        status_key: str,
        unit: str | None = None,
    ) -> None:
        super().__init__(controller, entry, name, unique_suffix)
        self._status_key = status_key
        self._last_value: Any = None
        if unit is not None:
            self._attr_native_unit_of_measurement = unit

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state not in {"unknown", "unavailable", "none"}:
            self._last_value = state.state

    @property
    def native_value(self) -> Any:
        value = self._controller.status.get(self._status_key)
        if value is None:
            return self._last_value
        self._last_value = value
        return value
