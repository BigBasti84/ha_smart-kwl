"""Persistent storage for filter tracking."""

from __future__ import annotations

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

FILTER_STORAGE_KEY = "smart_kwl_filter"
FILTER_STORAGE_VERSION = 1


class FilterStore:
    """Load and persist filter maintenance data."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, FILTER_STORAGE_VERSION, f"{FILTER_STORAGE_KEY}_{entry_id}")
        self._data: dict = {}

    async def async_load(self) -> None:
        self._data = await self._store.async_load() or {}
        if not self._data.get("install_date"):
            self._data["install_date"] = datetime.now().isoformat()
            await self._store.async_save(self._data)

    @property
    def last_cleaned(self) -> str | None:
        return self._data.get("last_cleaned")

    @property
    def install_date(self) -> str | None:
        return self._data.get("install_date")

    async def async_mark_cleaned(self) -> None:
        self._data["last_cleaned"] = datetime.now().isoformat()
        await self._store.async_save(self._data)
