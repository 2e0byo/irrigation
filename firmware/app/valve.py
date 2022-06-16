import logging

from . import upython

if upython:  # pragma: no cover
    import uasyncio as asyncio  # pragma: no cover
else:
    import asyncio

from .settings import settings


class ValveError(Exception):
    """Unable to set valve."""


class Valve:
    """A latching valve with no feedback."""

    CLOSED = 0
    CLOSING = 1
    OPENING = 2
    OPEN = 10

    ATTEMPTS = 10

    def __init__(self, name, en, in1, in2):
        """Initialise a new valve() object."""
        self.en = en
        self.in1 = in1
        self.in2 = in2
        self.en.off()
        self._state = self.CLOSED
        self.name = name
        self._logger = logging.getLogger(self.name)

    @property
    def pulse_duration(self):
        """Get the valve pulse duration."""
        return settings.get("{}--pulse_duration".format(self.name), 1)

    def _open(self):
        self.en.off()
        self.in1.on()
        self.in2.off()
        self.en.on()

    def _close(self):
        self.en.off()
        self.in1.off()
        self.in2.on()
        self.en.on()

    async def achieved_state(self, end_state):
        """Determine if we have achieved the desired state."""
        return True

    async def _pulse(self, end_state):
        on = end_state == self.OPEN
        for _ in range(self.ATTEMPTS):
            self._open() if on else self._close()
            await asyncio.sleep(self.pulse_duration)
            self.en.off()
            if await self.achieved_state(end_state):
                self._state = end_state
                self._logger.info(f"{'Opened' if on else 'Closed'} valve.")
                return
        raise ValveError(f"Failed to set valve in {self.ATTEMPTS} attempts!")

    @property
    def current_state(self):
        """Get the current valve state."""
        return self._state

    async def state(self, val: bool = None):
        """
        Get or set current valve state.

        Args:
            val[bool]: Set state (True is open).

        Raises:
            Exception if unable to achieve state.

        """
        if val:
            self._state = self.OPENING
            await self._pulse(self.OPEN)
        elif val is False:
            self._state = self.CLOSING
            await self._pulse(self.CLOSED)
        return self._state


class RateAwareValve(Valve):
    """A latching valve with feedback from a flowrate sensor."""

    def __init__(self, *args, rate_callback, **kwargs):
        """Initialise the RateAwareValve object."""
        super().__init__(*args, **kwargs)
        self.rate_callback = rate_callback
        self.transition_seconds = 15

    async def achieved_state(self, end_state):
        """Determine from the flow rate if we have achieved the desired state."""
        await asyncio.sleep(self.transition_seconds)
        if end_state == self.CLOSED:
            return self.rate_callback() == 0
        else:
            return self.rate_callback() > 0
