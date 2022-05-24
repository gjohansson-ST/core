"""Adds config flow for Open Exchange Rates integration."""
from __future__ import annotations

from typing import Any

import requests
from requests.exceptions import HTTPError, JSONDecodeError
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.const import CONF_API_KEY, CONF_BASE, CONF_NAME, CONF_QUOTE
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import DEFAULT_BASE, DEFAULT_NAME, DOMAIN


def get_fx_list() -> dict[str, str]:
    """Get list of available currencies."""
    try:
        result = requests.get(
            "https://openexchangerates.org/api/currencies.json", timeout=10
        )
        return result.json()
    except (HTTPError, JSONDecodeError):
        return {}


def validate_key(data: dict[str, Any]) -> None:
    """Validate api key."""
    params = params = {"base": "USD", "app_id": data[CONF_API_KEY]}
    try:
        result = requests.get(
            "ttps://openexchangerates.org/api/latest.json", params=params, timeout=10
        )
        assert result.json()["rates"]
    except (HTTPError, JSONDecodeError) as error:
        if result.status_code == 401:
            raise InvalidAuth from error
        raise CannotConnect from error


DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(),
        vol.Required(CONF_BASE, default=DEFAULT_BASE): TextSelector(),
        vol.Required(CONF_QUOTE): SelectSelector(
            SelectSelectorConfig(
                options=get_fx_list(), multiple=True, mode=SelectSelectorMode.DROPDOWN
            )
        ),
    }
)
DATA_SCHEMA_REAUTH = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(),
    }
)


class FxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SQL integration."""

    VERSION = 1
    entry: ConfigEntry | None

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-authentication with Open Exchange Rates."""

        self.entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm re-authentication with Open Exchange Rates."""
        errors: dict[str, str] = {}

        if user_input:
            api_key = user_input[CONF_API_KEY]

            assert self.entry is not None
            try:
                await validate_key(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors[CONF_API_KEY] = "invalid_auth"
            else:
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    data={
                        **self.entry.data,
                        CONF_API_KEY: api_key,
                    },
                )
                await self.hass.config_entries.async_reload(self.entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=DATA_SCHEMA_REAUTH,
            errors=errors,
        )

    async def async_step_import(self, config: dict[str, Any] | None) -> FlowResult:
        """Import a configuration from config.yaml."""

        new_config = config.pop(CONF_NAME)
        self._async_abort_entries_match(new_config)
        return await self.async_step_user(user_input=new_config)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step."""
        errors = {}

        if user_input is not None:

            try:
                validate_key(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors[CONF_API_KEY] = "invalid_auth"

            if not errors:
                return self.async_create_entry(
                    title=f"{DEFAULT_NAME} {user_input[CONF_BASE]}",
                    data={
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_BASE: user_input[CONF_BASE],
                        CONF_QUOTE: user_input[CONF_QUOTE],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Could not connect."""


class InvalidAuth(HomeAssistantError):
    """Authentication failure."""
