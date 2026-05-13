"""Button entities for Smart KWL."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .controller import SmartKwlController


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart KWL button entities."""
    controller: SmartKwlController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmartKwlMarkFiltersCleaned(controller, entry)])


class SmartKwlMarkFiltersCleaned(ButtonEntity):
    """Button to record that filters have been cleaned."""

    _attr_has_entity_name = True
    _attr_name = "Filters Cleaned"
    _attr_icon = "mdi:air-filter"

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry) -> None:
        self._controller = controller
        self._attr_unique_id = f"{entry.entry_id}_mark_filters_cleaned"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Smart KWL",
        )

    async def async_press(self) -> None:
        await self._controller.async_mark_filters_cleaned()
