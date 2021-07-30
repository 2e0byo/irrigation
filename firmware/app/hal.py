from machine import Pin
import uasyncio as asyncio
from sht1x import SHT1x
import logging
from . import settings, graph

logger = logging.getLogger("Hal")

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

clk = Pin(18)
data = Pin(17)
power = Pin(19, Pin.OUT)
sensor = SHT1x(data, clk)
soil_temperature, soil_humidity = None, None


async def read_sensor():
    power.on()
    await asyncio.sleep_ms(200)
    temp = sensor.read_temperature()
    humid = sensor.read_humidity()
    if settings.get("power_down_sensor", True):
        power.off()
    return temp, humid


async def read_sensor_loop():
    global soil_temperature, soil_humidity
    silent_count = 0  # don't keep stale readings indefinitely
    while True:
        try:
            soil_temperature, soil_humidity = await read_sensor()
            silent_count = 0
        except Exception as e:
            logger.exc("Read sensor failed: {}".format(e))
            silent_count += 1
            if silent_count > 10:
                soil_temperature, soil_humidity = None, None
            continue
        graph.packer.append([soil_temperature, soil_humidity], [valve.state])
        await asyncio.sleep(60)


def status():
    from . import irrigation

    state = {
        "valve": valve.state,
        "mode": "auto" if irrigation.auto_mode else "manual",
        "soil_temperature": soil_temperature,
        "soil_humidity": soil_humidity,
    }
    # power.off()
    return state


def init(loop):
    loop.create_task(read_sensor_loop())
