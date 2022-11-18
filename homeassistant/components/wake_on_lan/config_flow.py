"""Adds config flow for Wake on LAN integration."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.const import (
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
)
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
    SchemaOptionsFlowHandler,
)
from homeassistant.helpers.selector import (
    ActionSelector,
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import CONF_OFF_ACTION, CONF_SWITCH, DEFAULT_NAME, DOMAIN

BASE_SETUP = {vol.Required(CONF_SWITCH, default=True): BooleanSelector()}
SWITCH_SETUP = {
    vol.Required(CONF_MAC): TextSelector(),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): TextSelector(),
}
SWITCH_SETUP_OPT = {
    vol.Optional(CONF_BROADCAST_ADDRESS): TextSelector(),
    vol.Optional(CONF_BROADCAST_PORT): NumberSelector(
        NumberSelectorConfig(min=0, max=65535, step=1, mode=NumberSelectorMode.BOX)
    ),
    vol.Optional(CONF_HOST): TextSelector(),
    vol.Optional(CONF_OFF_ACTION): ActionSelector(),
}


DATA_SCHEMA_BASE = vol.Schema(BASE_SETUP)
DATA_SCHEMA_SWITCH = vol.Schema({**SWITCH_SETUP, **SWITCH_SETUP_OPT})
DATA_SCHEMA_SWITCH_OPT = vol.Schema(SWITCH_SETUP_OPT)
DATA_SCHEMA_IMPORT = vol.Schema({**BASE_SETUP, **SWITCH_SETUP, **SWITCH_SETUP_OPT})


CONFIG_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
    "user": SchemaFlowFormStep(
        schema=DATA_SCHEMA_BASE,
        next_step=lambda _: "switch",
    ),
    "switch": SchemaFlowFormStep(schema=DATA_SCHEMA_SWITCH),
    "import": SchemaFlowFormStep(schema=DATA_SCHEMA_IMPORT),
}
OPTIONS_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
    "init": SchemaFlowFormStep(schema=DATA_SCHEMA_SWITCH_OPT)
}


class WOLConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Wake on LAN."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return options.get(CONF_NAME, "Send Magic Packet")

    def async_config_flow_finished(self, options: Mapping[str, Any]) -> None:
        """Check for duplicate records."""
        data: dict[str, Any] = dict(options)
        self._async_abort_entries_match(data)


class WOLOptionFlowHandler(SchemaOptionsFlowHandler):
    """Handle an option flow for Wake on LAN."""
