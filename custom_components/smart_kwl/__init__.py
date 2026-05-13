"""Smart KWL integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .controller import SmartKwlController

PLATFORMS = ["sensor", "binary_sensor", "fan", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smart KWL from a config entry."""
    controller = SmartKwlController(hass, entry)
    await controller.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = controller
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Smart KWL config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    controller: SmartKwlController | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if controller is not None:
        await controller.async_stop()
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
