"""Support for openexchangerates.org exchange rates service."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_BASE, CONF_NAME, CONF_QUOTE
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType, StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_BASE, DEFAULT_NAME, DOMAIN
from .coordinator import FxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by openexchangerates.org"

MIN_TIME_BETWEEN_UPDATES = timedelta(hours=2)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_QUOTE): cv.string,
        vol.Optional(CONF_BASE, default=DEFAULT_BASE): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


@dataclass
class FxRequiredKeysMixin:
    """Mixin for required keys."""

    value_fn: Callable[[dict[str, Any]], StateType | datetime]


@dataclass
class FxSensorEntityDescription(SensorEntityDescription, FxRequiredKeysMixin):
    """Describes Open Exchange Rates sensor entity."""


SENSOR_TYPES: tuple[FxSensorEntityDescription, ...] = (
    FxSensorEntityDescription(
        key="timestamp",
        name="Last Update",
        icon="mdi:clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data["timestamp"],
    ),
    FxSensorEntityDescription(
        key="status",
        name="Status",
        icon="mdi:state-machine",
        value_fn=lambda data: data["status"],
    ),
    FxSensorEntityDescription(
        key="count",
        name="API Count",
        icon="mdi:history",
        value_fn=lambda data: data["count"],
    ),
    FxSensorEntityDescription(
        key="remain",
        name="API calls remain",
        icon="mdi:restore",
        value_fn=lambda data: data["remain"],
    ),
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Open Exchange Rates sensor."""
    _LOGGER.warning(
        # Config flow added in Home Assistant Core 2022.6, remove import flow in 2022.8
        "Loading Open Exchanges Rates via platform setup is deprecated; Please remove it from your configuration"
    )

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config,
        )
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Open Exchange Rates sensor entry."""

    coordinator: FxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[OpenexchangeratesSensor] = []
    currency: str
    for currency in entry.data[CONF_QUOTE]:
        entities.extend(
            OpenexchangeratesSensor(
                coordinator,
                entry.title,
                entry.entry_id,
                FxSensorEntityDescription(
                    key=f"rate_{currency.lower()}",
                    name=f"to {currency}",
                    icon="mdi:currency-usd",
                    value_fn=lambda data, currency: data[currency],
                ),
                currency,
            )
        )
    entities.extend(
        OpenexchangeratesSensor(
            coordinator,
            entry.title,
            entry.entry_id,
            description,
            None,
        )
        for description in SENSOR_TYPES
    )

    async_add_entities(entities)


class OpenexchangeratesSensor(CoordinatorEntity[FxDataUpdateCoordinator], SensorEntity):
    """Representation of an Open Exchange Rates sensor."""

    entity_description: FxSensorEntityDescription
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: FxDataUpdateCoordinator,
        name,
        entry_id: str,
        entity_description: FxSensorEntityDescription,
        currency: str | None,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{name} {entity_description.name}"
        self._attr_unique_id = f"{entry_id}-{entity_description.key}"
        self.entity_description = entity_description
        self.currency = currency
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry_id)},
            manufacturer="Open Exchange Rates",
            name=name,
            configuration_url="https://openexchangerates.org/account",
        )
        self._update_attr()

    def _update_attr(self) -> None:
        """Update _attr."""
        if self.currency:
            self._attr_native_value = self.entity_description.value_fn(
                self.coordinator.data, self.currency
            )
            return
        self._attr_native_value = self.entity_description.value_fn(
            self.coordinator.data
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_attr()
        return super()._handle_coordinator_update()
