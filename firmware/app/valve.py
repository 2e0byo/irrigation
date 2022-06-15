import logging

from . import upython

if upython:  # pragma: no cover
    import uasyncio as asyncio  # pragma: no cover
else:
    import asyncio

from .settings import settings


class Valve:
    """A latching valve with no feedback."""

    CLOSED = 0
    CLOSING = 1
    OPENING = 2
    OPEN = 10

    def __init__(self, name, en, in1, in2):
        """Initialise a new valve() object."""
        self.en = en
        self.in1 = in1
        self.in2 = in2
        self.en.off()
        self._state = False
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

    async def _pulse(self, end_state):
        on = end_state == self.OPEN
        self._open() if on else self._close()
        await asyncio.sleep(self.pulse_duration)
        self.en.off()
        self._state = end_state
        self._logger.info(f"{'Opened' if on else 'Closed'} valve.")

    def state(self, val=None):
        """Get or set the current valve state."""
        if val:
            asyncio.create_task(self._pulse(self.OPEN))
            self._state = self.OPENING
        elif val is False:
            asyncio.create_task(self._pulse(self.CLOSED))
            self._state = self.CLOSING
        return self._state
