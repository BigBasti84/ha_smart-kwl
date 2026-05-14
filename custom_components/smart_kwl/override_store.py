"""Persistent storage for manual override state."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

OVERRIDE_STORAGE_KEY = "smart_kwl_override"
OVERRIDE_STORAGE_VERSION = 1


class OverrideStore:
    """Load and persist manual override activation state."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, OVERRIDE_STORAGE_VERSION, f"{OVERRIDE_STORAGE_KEY}_{entry_id}")
        self._data: dict = {}

    async def async_load(self) -> None:
        self._data = await self._store.async_load() or {}

    @property
    def override_level(self) -> int | None:
        v = self._data.get("override_level")
        return int(v) if v is not None else None

    @property
    def override_until(self) -> str | None:
        return self._data.get("override_until")

    async def async_save_override(self, level: int, until_iso: str) -> None:
        self._data["override_level"] = level
        self._data["override_until"] = until_iso
        await self._store.async_save(self._data)

    async def async_clear_override(self) -> None:
        self._data.pop("override_level", None)
        self._data.pop("override_until", None)
        await self._store.async_save(self._data)
