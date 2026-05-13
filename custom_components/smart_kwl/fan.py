"""Fan entity for Smart KWL manual level control."""

from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .controller import SmartKwlController


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart KWL fan entities."""
    controller: SmartKwlController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmartKwlManualFan(controller, entry)])


class SmartKwlManualFan(FanEntity):
    """Expose a dedicated fan entity that controls Smart KWL target levels."""

    _attr_has_entity_name = True
    _attr_name = "Manual Fan Level"
    _attr_supported_features = FanEntityFeature.PRESET_MODE

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry) -> None:
        self._controller = controller
        self._attr_unique_id = f"{entry.entry_id}_manual_fan"
        min_level, max_level = self._controller.level_bounds()
        self._attr_preset_modes = [str(level) for level in range(min_level, max_level + 1)]
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
        return self._controller.current_level() is not None

    @property
    def preset_mode(self) -> str | None:
        level = self._controller.current_level()
        return str(level) if level is not None else None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._controller.async_set_manual_level(int(preset_mode))

    @callback
    def _handle_controller_update(self) -> None:
        self.async_write_ha_state()
