"""Sensor entities for Smart KWL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
        SmartKwlCheckLogSensor(controller, entry),
    ]

    for cfg in TEMP_CONFIGS:
        source_entity = entry.options.get(cfg.key, entry.data.get(cfg.key))
        if source_entity:
            entities.append(SmartKwlTemperatureSensor(controller, entry, cfg.name, cfg.unique_suffix, source_entity))

    async_add_entities(entities)


class SmartKwlBaseEntity(RestoreEntity):
    """Base entity for Smart KWL info entities."""

    _attr_has_entity_name = True

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry, name: str, unique_suffix: str) -> None:
        self._controller = controller
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_name = name
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

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry, name: str, unique_suffix: str, status_key: str) -> None:
        super().__init__(controller, entry, name, unique_suffix)
        self._status_key = status_key

    @property
    def native_value(self) -> Any:
        return self._controller.status.get(self._status_key)


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
            "last_check_lines": self._controller.status.get("last_check_lines", []),
            "check_history": self._controller.status.get("check_history", []),
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
