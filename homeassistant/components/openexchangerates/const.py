"""Adds constants for Open Exchange Rates integration."""
from homeassistant.const import Platform

DOMAIN = "openexchangerates"
PLATFORMS = [Platform.SENSOR]

DEFAULT_BASE = "USD"
DEFAULT_NAME = "Exchange Rate Sensor"
