import asyncio

import pytest
from app.valve import RateAwareValve, Valve, ValveError


@pytest.fixture
def valve(mocker):
    v = Valve("Valve", mocker.Mock(), mocker.Mock(), mocker.Mock())
    settings = {"Valve--pulse_duration": 0.1}
    mocker.patch("app.valve.settings", settings)
    return v


async def test_open_close(valve):
    assert valve.current_state == valve.CLOSED
    asyncio.create_task(valve.state(True))
    await asyncio.sleep(0)
    assert valve.current_state == valve.OPENING
    await asyncio.sleep(0.3)
    assert valve.current_state == valve.OPEN
    assert await valve.state() == valve.OPEN
    asyncio.create_task(valve.state(False))
    await asyncio.sleep(0)
    assert valve.current_state == valve.CLOSING
    await asyncio.sleep(0.3)
    assert valve.current_state == valve.CLOSED
    assert await valve.state() == valve.CLOSED


async def test_fail_once(valve):
    x = 0

    async def fail_once(*args):
        nonlocal x
        x += 1
        return x > 1

    valve.achieved_state = fail_once
    await valve.state(True)
    assert x == 2
    assert valve.current_state == valve.OPEN


async def test_fail(valve):
    async def state(*args):
        return False

    valve.achieved_state = state
    with pytest.raises(ValveError):
        await valve.state(True)


async def test_pulse_duration(valve):
    assert valve.pulse_duration == 0.1


@pytest.fixture
def rate_valve(mocker):
    v = RateAwareValve(
        "RateValve",
        mocker.Mock(),
        mocker.Mock(),
        mocker.Mock(),
        rate_callback=mocker.Mock(),
    )
    settings = {"RateValve--pulse_duration": 0.1}
    mocker.patch("app.valve.settings", settings)
    v.transition_seconds = 0.5
    return v


async def test_rate_valve_on_off(rate_valve):
    rate_valve.rate_callback.return_value = 10
    await rate_valve.state(True)
    assert rate_valve.current_state == rate_valve.OPEN
    rate_valve.rate_callback.return_value = 0
    await rate_valve.state(False)
    assert rate_valve.current_state == rate_valve.CLOSED


async def test_rate_valve_fail(rate_valve):
    rate_valve.ATTEMPTS = 3
    rate_valve.rate_callback.return_value = 10
    with pytest.raises(ValveError):
        await rate_valve.state(False)
    assert rate_valve.current_state == rate_valve.CLOSING
    rate_valve.rate_callback.return_value = 0
    with pytest.raises(ValveError):
        await rate_valve.state(True)
    assert rate_valve.current_state == rate_valve.OPENING


async def test_rate_valve_slow(rate_valve):
    x = 0
    start = 0
    end = 10

    def rate(*args):
        nonlocal x, end
        x += 1
        return end if x > 1 else start

    rate_valve.rate_callback = rate

    await rate_valve.state(True)
    assert x == 2
    assert rate_valve.en.on.call_count == 2
    start, end = end, start
    x = 0
    await rate_valve.state(False)
    assert rate_valve.en.on.call_count == 4
