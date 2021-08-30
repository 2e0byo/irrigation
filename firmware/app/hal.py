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

    def state(self, val=None):
        if val:
            asyncio.create_task(self._open())
            self._state = True
        elif val is False:
            asyncio.create_task(self._close())
            self._state = False
        return self._state


class TempSensor:
    def __init__(self, name, sensor, power, logf=None):
        self.name = name
        self.sensor = sensor
        self.power = power
        self.temperature = None
        self.humidity = None
        self.logf = logf

    @property
    def power_down(self):
        return settings.get("{}/power_down_sensor".format(self.name), True)

    async def read_sensor(self):
        self.power.on()
        await asyncio.sleep_ms(200)
        # these are pretty instantaneous
        self.temperature = self.sensor.read_temperature()
        self.humidity = self.sensor.read_humidity()
        if self.power_down:
            power.off()

    async def read_sensor_loop(self):
        silent_count = 0  # don't keep stale readings indefinitely
        while True:
            try:
                await read_sensor()
                silent_count = 0
            except Exception as e:
                logger.exc(e, "Read sensor failed: {}")
                silent_count += 1
                if silent_count > 10:
                    self.soil_temperature = None
                    self.soil_humidity = None
                continue
            if self.logf:
                self.logf(self)
            await asyncio.sleep(60)

    def init(self, loop):
        loop.create_task(self.read_sensor_loop())


def log_temps(sensor):
    graph.packer.append(floats=(sensor.temperature, sensor.humidity), bools=bools())


def bools():
    from . import irrigation

    return (
        valve.state(),
        irrigation.auto_waterer.watering,
        irrigation.auto_waterer.auto_mode,
    )


def status():
    from . import irrigation

    state = {
        "valve": valve.state(),
        "mode": "auto" if irrigation.auto_waterer.auto_mode else "manual",
        "soil_temperature": temp_sensor.soil_temperature,
        "soil_humidity": temp_sensor.soil_humidity,
        "watering": irrigation.auto_waterer.watering,
    }
    return state


valve = Valve(en, in1, in2)
clk = Pin(18)
data = Pin(17)
power = Pin(19, Pin.OUT)
sensor = SHT1x(data, clk)
temp_sensor = TempSensor("sens1", sensor, power, logf=log_temps)


def init(loop):
    temp_sensor.init(loop)
    valve.state(False)
