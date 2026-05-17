"""Button entities for Smart KWL."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up Smart KWL button entities."""
    controller: SmartKwlController = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SmartKwlMarkFiltersCleaned(controller, entry),
            SmartKwlApplyManualOverride(controller, entry),
            SmartKwlCancelManualOverride(controller, entry),
        ]
    )


class SmartKwlMarkFiltersCleaned(ButtonEntity):
    """Button to record that filters have been cleaned."""

    _attr_has_entity_name = False
    _attr_name = "Filters Cleaned"
    _attr_icon = "mdi:air-filter"

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry) -> None:
        self._controller = controller
        self._attr_unique_id = f"{entry.entry_id}_mark_filters_cleaned"
        self._attr_object_id = f"{DOMAIN}_filters_cleaned"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Smart KWL",
        )

    async def async_press(self) -> None:
        await self._controller.async_mark_filters_cleaned()


class SmartKwlApplyManualOverride(ButtonEntity):
    """Button to apply timed manual override using configured values."""

    _attr_has_entity_name = False
    _attr_name = "Apply Manual Override"
    _attr_icon = "mdi:timer-play"

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry) -> None:
        self._controller = controller
        self._remove_listener = None
        self._attr_unique_id = f"{entry.entry_id}_apply_manual_override"
        self._attr_object_id = f"{DOMAIN}_apply_manual_override"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Smart KWL",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._remove_listener = self._controller.add_listener(self._handle_controller_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_controller_update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        status = self._controller.status
        return not bool(status.get("manual_override_active"))

    async def async_press(self) -> None:
        await self._controller.async_apply_manual_override()


class SmartKwlCancelManualOverride(ButtonEntity):
    """Button to cancel active manual override."""

    _attr_has_entity_name = False
    _attr_name = "Cancel Manual Override"
    _attr_icon = "mdi:timer-off"

    def __init__(self, controller: SmartKwlController, entry: ConfigEntry) -> None:
        self._controller = controller
        self._remove_listener = None
        self._attr_unique_id = f"{entry.entry_id}_cancel_manual_override"
        self._attr_object_id = f"{DOMAIN}_cancel_manual_override"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Smart KWL",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._remove_listener = self._controller.add_listener(self._handle_controller_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_controller_update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return bool(self._controller.status.get("manual_override_active"))

    async def async_press(self) -> None:
        await self._controller.async_cancel_manual_override()
