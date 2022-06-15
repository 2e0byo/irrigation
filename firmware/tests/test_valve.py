import asyncio

import pytest
from app.valve import Valve


@pytest.fixture
def valve(mocker):
    v = Valve("Valve", mocker.Mock(), mocker.Mock(), mocker.Mock())
    settings = {"Valve--pulse_duration": 0.1}
    mocker.patch("app.valve.settings", settings)
    return v


async def test_open_close(valve):
    assert valve.state() == valve.CLOSED
    valve.state(True)
    assert valve.state() == valve.OPENING
    await asyncio.sleep(0.3)
    assert valve.state() == valve.OPEN
    valve.state(False)
    assert valve.state() == valve.CLOSING
    await asyncio.sleep(0.3)
    assert valve.state() == valve.CLOSED


async def test_pulse_duration(valve):
    assert valve.pulse_duration == 0.1
