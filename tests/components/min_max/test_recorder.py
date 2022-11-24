"""The tests for min_max recorder."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.components.min_max.sensor import (
    ATTR_ENTITIES,
    ATTR_LAST_ENTITY_ID,
    ATTR_MAX_ENTITY_ID,
    ATTR_MIN_ENTITY_ID,
)
from homeassistant.components.recorder.db_schema import StateAttributes, States
from homeassistant.components.recorder.util import session_scope
from homeassistant.const import ATTR_FRIENDLY_NAME
from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from tests.common import AsyncMock, async_fire_time_changed
from tests.components.recorder.common import async_wait_recording_done

VALUES = [17, 20, 15.3]


async def test_exclude_attributes(
    recorder_mock: AsyncMock, hass: HomeAssistant
) -> None:
    """Test min_max attributes to be excluded."""
    config = {
        "sensor": {
            "platform": "min_max",
            "type": "min",
            "entity_ids": ["sensor.test_1", "sensor.test_2", "sensor.test_3"],
        }
    }

    assert await async_setup_component(hass, "sensor", config)
    await hass.async_block_till_done()

    entity_ids = config["sensor"]["entity_ids"]

    for entity_id, value in dict(zip(entity_ids, VALUES)).items():
        hass.states.async_set(entity_id, value)
        await hass.async_block_till_done()

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=5))
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)

    def _fetch_min_max_states() -> list[State]:
        with session_scope(hass=hass) as session:
            native_states = []
            for db_state, db_state_attributes in session.query(States, StateAttributes):
                state: State = db_state.to_native()
                state.attributes = db_state_attributes.to_native()
                native_states.append(state)
            return native_states

    states: list[State] = await hass.async_add_executor_job(_fetch_min_max_states)
    assert len(states) > 1
    for state in states:
        assert ATTR_ENTITIES not in state.attributes
        assert ATTR_MIN_ENTITY_ID not in state.attributes
        assert ATTR_MAX_ENTITY_ID not in state.attributes
        assert ATTR_LAST_ENTITY_ID not in state.attributes
        assert ATTR_FRIENDLY_NAME in state.attributes
