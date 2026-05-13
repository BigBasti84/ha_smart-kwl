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

    async def async_load(self, initial_install_date: str | None = None) -> None:
        self._data = await self._store.async_load() or {}
        if not self._data.get("install_date"):
            # Prefer setup-provided date; otherwise use best-known fallback.
            self._data["install_date"] = initial_install_date or self._data.get("last_cleaned") or datetime.now().isoformat()
            await self._store.async_save(self._data)

    @property
    def last_cleaned(self) -> str | None:
        return self._data.get("last_cleaned")

    @property
    def install_date(self) -> str | None:
        return self._data.get("install_date")

    async def async_set_install_date(self, install_date: str) -> None:
        self._data["install_date"] = install_date
        await self._store.async_save(self._data)

    async def async_mark_cleaned(self) -> None:
        self._data["last_cleaned"] = datetime.now().isoformat()
        await self._store.async_save(self._data)
