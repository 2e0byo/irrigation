from machine import Pin
import uasyncio as asyncio

en = Pin(23, Pin.OUT)
in1 = Pin(22, Pin.OUT)
in2 = Pin(21, Pin.OUT)


class Valve:
    def __init__(self, en, in1, in2):
        self.en = en
        self.in1 = in1
        self.in2 = in2
        self.en.off()
        self._state = False

    async def _open(self):
        self.en.off()
        self.in1.on()
        self.in2.off()
        self.en.on()
        await asyncio.sleep(1)
        self.en.off()

    async def _close(self):
        self.en.off()
        self.in1.off()
        self.in2.on()
        self.en.on()
        await asyncio.sleep(1)
        self.en.off()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, val):
        if val:
            asyncio.create_task(self._open())
            self._state = True
        else:
            asyncio.create_task(self._close())
            self._state = False
        return self._state


valve = Valve(en, in1, in2)


def status():
    state = {"valve": valve.state}
    return state
