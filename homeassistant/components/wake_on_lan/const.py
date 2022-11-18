"""Constants for the Wake-On-LAN component."""
from homeassistant.const import Platform

CONF_OFF_ACTION = "turn_off"
CONF_SWITCH = "switch"
DEFAULT_NAME = "Wake on LAN"
DOMAIN = "wake_on_lan"
PLATFORMS = [Platform.SWITCH]
