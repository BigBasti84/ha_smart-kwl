"""Number entities for Smart KWL manual override controls."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .controller import SmartKwlController


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart KWL number entities."""
    controller: SmartKwlController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SmartKwlManualOverrideLevelNumber(controller, entry),
            SmartKwlManualOverrideDurationNumber(controller, entry),
        ]
    )


class SmartKwlBaseNumber(RestoreEntity, NumberEntity):
    """Base number entity that follows controller updates."""

    _attr_has_entity_name = False

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry, name: str, unique_suffix: str) -> None:
        self._controller = controller
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_object_id = f"{DOMAIN}_{unique_suffix}"
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


class SmartKwlManualOverrideLevelNumber(SmartKwlBaseNumber):
    """Pending manual override level selector."""

    _attr_native_step = 1
    _attr_mode = "box"
    _attr_icon = "mdi:fan"

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry) -> None:
        super().__init__(controller, entry, "Manual Override Level", "manual_override_level")
        min_level, max_level = self._controller.level_bounds()
        self._attr_native_min_value = float(min_level)
        self._attr_native_max_value = float(max_level)

    @property
    def native_value(self) -> float:
        return float(self._controller.pending_manual_override_level())

    async def async_set_native_value(self, value: float) -> None:
        self._controller.set_pending_manual_override_level(int(round(value)))


class SmartKwlManualOverrideDurationNumber(SmartKwlBaseNumber):
    """Pending manual override duration selector in hours."""

    _attr_native_min_value = 1
    _attr_native_max_value = 24
    _attr_native_step = 1
    _attr_mode = "box"
    _attr_native_unit_of_measurement = "h"
    _attr_icon = "mdi:timer"

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry) -> None:
        super().__init__(controller, entry, "Manual Override Duration", "manual_override_duration")

    @property
    def native_value(self) -> float:
        return float(self._controller.pending_manual_override_hours())

    async def async_set_native_value(self, value: float) -> None:
        self._controller.set_pending_manual_override_hours(int(round(value)))
