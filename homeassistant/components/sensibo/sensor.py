"""Sensor platform for Sensibo integration."""
from __future__ import annotations


from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.components.climate.const import ATTR_FAN_MODE, ATTR_SWING_MODE

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_MODE, ATTR_STATE, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SensiboDataUpdateCoordinator

SERVICE_SET_TIMER = "set_timer"
SERVICE_DEL_TIMER = "del_timer"

SENSOR_TYPES = (
    SensorEntityDescription(
        key="timer",
        name="Timer",
        icon="mdi:timer",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
        device_class=SensorDeviceClass.TIMESTAMP,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Sensibo sensor platform."""

    coordinator: SensiboDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        SensiboSensor(coordinator, device_id, description)
        for device_id, device_data in coordinator.data.items()
        for description in SENSOR_TYPES
        if device_data["hvac_modes"] and device_data["temp"]
    )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_TIMER,
        {
            vol.Required(ATTR_STATE): vol.In(["on", "off"]),
            vol.Optional(ATTR_MODE): "kalle",  # NEED TO FIX
            vol.Optional(ATTR_FAN_MODE): "kalle",
            vol.Optional(ATTR_TEMPERATURE): "kalle",
            vol.Optional(ATTR_SWING_MODE): "kalle",
        },
        "async_set_timer",
    )
    platform.async_register_entity_service(
        SERVICE_DEL_TIMER,
        {},
        "async_del_timer",
    )


class SensiboSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensibo numbers."""

    coordinator: SensiboDataUpdateCoordinator
    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: SensiboDataUpdateCoordinator,
        device_id: str,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initiate Sensibo Sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._device_id = device_id
        self._client = coordinator.client
        self._attr_unique_id = f"{device_id}-{entity_description.key}"
        self._attr_name = (
            f"{coordinator.data[device_id]['name']} {entity_description.name}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.data[device_id]["id"])},
            name=coordinator.data[device_id]["name"],
            connections={(CONNECTION_NETWORK_MAC, coordinator.data[device_id]["mac"])},
            manufacturer="Sensibo",
            configuration_url="https://home.sensibo.com/",
            model=coordinator.data[device_id]["model"],
            sw_version=coordinator.data[device_id]["fw_ver"],
            hw_version=coordinator.data[device_id]["fw_type"],
            suggested_area=coordinator.data[device_id]["name"],
        )

    @property
    def native_value(self) -> datetime | None:
        """Return Timer target."""
        if self.coordinator.data[self._device_id]["timer"]["enabled"]:
            return self.coordinator.data[self._device_id]["timer"]["timer_target_tz"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional attributes."""
        return {
            "timer_created": self.coordinator.data[self._device_id]["timer"][
                "timer_created_tz"
            ],
            "on": self.coordinator.data[self._device_id]["timer"]
            .get("acstate", {})
            .get("on", None),
            "mode": self.coordinator.data[self._device_id]["timer"]
            .get("acstate", {})
            .get("mode", None),
            "fanLevel": self.coordinator.data[self._device_id]["timer"]
            .get("acstate", {})
            .get("fanLevel", None),
            "targetTemperature": self.coordinator.data[self._device_id]["timer"]
            .get("acstate", {})
            .get("targetTemperature", None),
            "swing": self.coordinator.data[self._device_id]["timer"]
            .get("acstate", {})
            .get("swing", None),
        }

    async def async_set_timer(self) -> None:
        """Custom Service to set timer."""
        # NEED TO FIX

    async def async_del_timer(self) -> None:
        """Custom Service to delete timer."""
        # NEED TO FIX
