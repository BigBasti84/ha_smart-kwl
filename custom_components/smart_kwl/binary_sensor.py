"""Binary sensor entities for Smart KWL."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
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
    async_add_entities([SmartKwlVentilationState(controller, entry)])


class SmartKwlVentilationState(BinarySensorEntity):
    """Binary sensor showing if ventilation is currently on."""

    _attr_has_entity_name = True
    _attr_name = "Ventilation On"

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry) -> None:
        self._controller = controller
        self._attr_unique_id = f"{entry.entry_id}_ventilation_on"
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
        return state.state == STATE_ON

    @callback
    def _handle_controller_update(self) -> None:
        self.async_write_ha_state()
