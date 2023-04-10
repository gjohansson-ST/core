"""Support for custom shell commands to turn a switch on/off."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    SwitchEntity,
)
from homeassistant.const import (
    CONF_COMMAND_OFF,
    CONF_COMMAND_ON,
    CONF_COMMAND_STATE,
    CONF_FRIENDLY_NAME,
    CONF_ICON_TEMPLATE,
    CONF_SWITCHES,
    CONF_UNIQUE_ID,
    CONF_VALUE_TEMPLATE,
    CONF_ICON,
    CONF_NAME,
    CONF_STATE,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.template import Template
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.components.template.trigger_entity import TriggerBaseEntity

from .const import CONF_COMMAND_TIMEOUT, DEFAULT_TIMEOUT, DOMAIN, PLATFORMS
from .utils import call_shell_with_timeout, check_output_or_log

_LOGGER = logging.getLogger(__name__)
DEFAULT_VALUE_TEMPLATE = r"{{value}}"

SWITCH_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_COMMAND_OFF, default="true"): cv.string,
        vol.Optional(CONF_COMMAND_ON, default="true"): cv.string,
        vol.Optional(CONF_COMMAND_STATE): cv.string,
        vol.Optional(CONF_FRIENDLY_NAME): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE, default=DEFAULT_VALUE_TEMPLATE): cv.string,
        vol.Optional(CONF_ICON_TEMPLATE): cv.template,
        vol.Optional(CONF_COMMAND_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_SWITCHES): cv.schema_with_slug_keys(SWITCH_SCHEMA)}
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Find and return switches controlled by shell commands."""

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)

    devices: dict[str, Any] = config.get(CONF_SWITCHES, {})
    switches = []
    config = {}

    for object_id, device_config in devices.items():
        value_template = Template(device_config.get(CONF_VALUE_TEMPLATE))
        config[CONF_VALUE_TEMPLATE] = value_template

        icon_template: Template | None = device_config.get(CONF_ICON_TEMPLATE)
        if icon_template is not None:
            config = {CONF_ICON: icon_template}

        config[CONF_NAME] = Template(
            device_config.get(CONF_FRIENDLY_NAME, object_id), hass
        )
        config[CONF_UNIQUE_ID] = device_config.get(CONF_UNIQUE_ID)

        switches.append(
            CommandSwitch(
                object_id,
                device_config.get(CONF_FRIENDLY_NAME, object_id),
                device_config[CONF_COMMAND_ON],
                device_config[CONF_COMMAND_OFF],
                device_config.get(CONF_COMMAND_STATE),
                icon_template,
                value_template,
                device_config[CONF_COMMAND_TIMEOUT],
                device_config.get(CONF_UNIQUE_ID),
                config,
            )
        )

    if not switches:
        _LOGGER.error("No switches added")
        return

    async_add_entities(switches)


class CommandSwitch(TriggerBaseEntity, SwitchEntity):
    """Representation a switch that can be toggled using shell commands."""

    domain = "switch"
    extra_template_keys = (CONF_VALUE_TEMPLATE,)

    def __init__(
        self,
        object_id: str,
        friendly_name: str,
        command_on: str,
        command_off: str,
        command_state: str | None,
        icon_template: Template | None,
        value_template: Template | None,
        timeout: int,
        unique_id: str | None,
        config: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        super().__init__(self.hass, config)
        self.entity_id = ENTITY_ID_FORMAT.format(object_id)
        self._attr_is_on = False
        self._command_on = command_on
        self._command_off = command_off
        self._command_state = command_state
        self._value_template = value_template
        self._timeout = timeout
        self._attr_should_poll = bool(command_state)

    async def _switch(self, command: str) -> bool:
        """Execute the actual commands."""
        _LOGGER.info("Running command: %s", command)

        success = (
            await self.hass.async_add_executor_job(
                call_shell_with_timeout, command, self._timeout
            )
            == 0
        )

        if not success:
            _LOGGER.error("Command failed: %s", command)

        return success

    def _query_state_value(self, command: str) -> str | None:
        """Execute state command for return value."""
        _LOGGER.info("Running state value command: %s", command)
        return check_output_or_log(command, self._timeout)

    def _query_state_code(self, command: str) -> bool:
        """Execute state command for return code."""
        _LOGGER.info("Running state code command: %s", command)
        return (
            call_shell_with_timeout(command, self._timeout, log_return_code=False) == 0
        )

    @property
    def assumed_state(self) -> bool:
        """Return true if we do optimistic updates."""
        return self._command_state is None

    def _query_state(self) -> str | int | None:
        """Query for state."""
        if self._command_state:
            if self._value_template:
                return self._query_state_value(self._command_state)
            return self._query_state_code(self._command_state)
        if TYPE_CHECKING:
            return None

    async def async_update(self) -> None:
        """Update device state."""
        if self._command_state:
            payload = str(await self.hass.async_add_executor_job(self._query_state))
            self._variables = payload  # load variables with result from query
            if self._value_template:
                payload = self._value_template.async_render_with_possible_json_value(
                    payload, None
                )
            print(payload)
            self._attr_is_on = None
            if payload:
                self._attr_is_on = payload.lower() == "true"
            self._process_data()  # Process template data
            print(self._rendered)

    @property
    def is_on(self) -> bool | None:
        """Return is on."""
        if self._command_state:
            if state := self._rendered.get(CONF_VALUE_TEMPLATE):
                return state.lower() == "true"
        return self._attr_is_on

        return self._rendered.get(CONF_VALUE_TEMPLATE).lower() == "true"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        if await self._switch(self._command_on) and not self._command_state:
            self._attr_is_on = True
            self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        if await self._switch(self._command_off) and not self._command_state:
            self._attr_is_on = False
            self.async_schedule_update_ha_state()
