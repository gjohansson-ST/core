"""DataUpdateCoordinator for the Open Exchange Rates integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_BASE, CONF_QUOTE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_RESOURCE_LATEST = "https://openexchangerates.org/api/latest.json"
_RESOURCE_USAGE = "https://openexchangerates.org/api/usage.json"
TIME_BETWEEN_UPDATES = timedelta(hours=2)


class FxDataUpdateCoordinator(DataUpdateCoordinator):
    """A Open Exchange Rates Data Update Coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=TIME_BETWEEN_UPDATES,
        )

        self._base = entry.data[CONF_BASE]
        self._api_key = entry.data[CONF_API_KEY]
        self._quote = entry.data[CONF_QUOTE]

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Open Exchange Rates API."""
        params = {"base": self._base, "app_id": self._api_key}
        try:
            result = requests.get(_RESOURCE_LATEST, params=params, timeout=10)
            rates: dict[str, float] = result.json()["rates"]
            timestamp: datetime = result.json()["timestamp"]
            usage = requests.get(_RESOURCE_USAGE, params=params, timeout=10)
            status: str = usage.json()["data"]["status"]
            count: int = usage.json()["data"]["usage"]["requests"]
            remain: int = usage.json()["data"]["usage"]["requests_remaining"]
        except requests.exceptions.HTTPError as error:
            if result.status_code == 401:
                raise ConfigEntryAuthFailed from error
            raise UpdateFailed("Error getting data {error}") from error

        states = dict(rates.items())

        states["timestamp"] = timestamp
        states["status"] = status
        states["count"] = count
        states["remain"] = remain

        _LOGGER.debug("States: %s", states)
        return states
