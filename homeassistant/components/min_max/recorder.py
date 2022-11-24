"""Integration platform for recorder."""
from __future__ import annotations

from homeassistant.core import HomeAssistant, callback

from .sensor import (
    ATTR_ENTITIES,
    ATTR_LAST_ENTITY_ID,
    ATTR_MAX_ENTITY_ID,
    ATTR_MIN_ENTITY_ID,
)


@callback
def exclude_attributes(hass: HomeAssistant) -> set[str]:
    """Exclude min_max attributes from being recorded in the database."""
    return {
        ATTR_ENTITIES,
        ATTR_MIN_ENTITY_ID,
        ATTR_MAX_ENTITY_ID,
        ATTR_LAST_ENTITY_ID,
    }
