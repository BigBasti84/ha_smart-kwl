"""Binary sensor entities for Smart KWL."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .controller import SmartKwlController


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart KWL binary sensors."""
    controller: SmartKwlController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SmartKwlVentilationState(controller, entry),
            SmartKwlModeState(controller, entry, "Summer Mode Active", "summer_mode_active", "summer_mode_active"),
            SmartKwlModeState(controller, entry, "Night Mode Active", "night_mode_active", "night_mode_active"),
            SmartKwlModeState(controller, entry, "Manual Override Active", "manual_override_active", "manual_override_active"),
        ]
    )


class SmartKwlVentilationState(BinarySensorEntity):
    """Binary sensor showing if ventilation is currently on."""

    _attr_has_entity_name = False
    _attr_name = "Ventilation On"

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry) -> None:
        self._controller = controller
        self._attr_unique_id = f"{entry.entry_id}_ventilation_on"
        self._attr_object_id = f"{DOMAIN}_ventilation_on"
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

    @property
    def is_on(self) -> bool | None:
        state = self._controller.fan_state()
        if state is None:
            return None
        return state.state not in (STATE_OFF, "unavailable", "unknown")

    @callback
    def _handle_controller_update(self) -> None:
        self.async_write_ha_state()


class SmartKwlModeState(BinarySensorEntity):
    """Binary sensor exposing controller mode state flags."""

    _attr_has_entity_name = False

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry, name: str, unique_suffix: str, status_key: str) -> None:
        self._controller = controller
        self._status_key = status_key
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

    @property
    def is_on(self) -> bool:
        return bool(self._controller.status.get(self._status_key, False))

    @callback
    def _handle_controller_update(self) -> None:
        self.async_write_ha_state()
