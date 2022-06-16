import logging

import uasyncio as asyncio
from machine import Pin, Timer
from sht1x import SHT1x

from . import graph
from .settings import settings
from .valve import Valve

logger = logging.getLogger("Hal")

en = Pin(23, Pin.OUT)
in1 = Pin(22, Pin.OUT)
in2 = Pin(21, Pin.OUT)


class TempSensor:
    def __init__(self, name, sensor, power, logf=None, period=60):
        self.name = name
        self.sensor = sensor
        self.power = power
        self.temperature = None
        self.humidity = None
        self.logf = logf
        self.period = period

    @property
    def power_down(self):
        return settings.get("{}--power_down_sensor".format(self.name), True)

    async def read_sensor(self):
        self.power.on()
        if self.power_down:
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
                await self.read_sensor()
                silent_count = 0
                if self.logf:
                    self.logf(self)
            except Exception as e:
                logger.exc(e, "Read sensor failed: {}")
                silent_count += 1
                if silent_count > 10:
                    self.soil_temperature = None
                    self.soil_humidity = None
            await asyncio.sleep(self.period)

    def init(self, loop):
        loop.create_task(self.read_sensor_loop())


def log_temps(sensor):
    graph.packer.append(floats=(sensor.temperature, sensor.humidity), bools=bools())


def bools():
    from . import irrigation

    return (
        valve.current_state >= valve.OPENING,
        irrigation.auto_waterer.watering(),
        irrigation.auto_waterer.auto_mode,
    )


def status():
    from . import irrigation

    state = {
        "valve": valve.current_state,
        "soil_temperature": temp_sensor.temperature,
        "soil_humidity": temp_sensor.humidity,
        "watering": irrigation.auto_waterer.watering(),
        "auto_mode": irrigation.auto_waterer.auto_mode,
    }
    return state


valve = Valve("valve1", en, in1, in2)
clk = Pin(18)
data = Pin(17)
power = Pin(5, Pin.OUT)
sensor = SHT1x(data, clk)
temp_sensor = TempSensor("sens1", sensor, power, logf=log_temps)


class FreqCounter:
    """A frequency counter, depending on interrupts."""

    def __init__(self, pin, period_ms):
        """Initialise the counter."""
        self._count = 0
        self._total_count = 0
        self.period_ms = period_ms
        pin.irq(trigger=Pin.IRQ_FALLING, handler=self._incr)
        timer = Timer(-1)
        timer.init(period=period_ms, mode=Timer.PERIODIC, callback=self._total)

    def _incr(self, *_):
        self._count += 1

    def _total(self, *_):
        self._total_count = self._count
        self._count = 0

    @property
    def frequency(self):
        """Calculate the current frequency."""
        return 1_000 * self._total_count / self.period_ms


class FlowSensor(FreqCounter):
    """A flow sensor e.g. for water or air."""

    def __init__(self, *args, rate: float = 7.5):
        """Initialise the sensor.

        params:
            rate (float): volume per hour / frequency. (default=7.5)
        """
        super().__init__(*args)
        self._rate = rate

    @property
    def rate(self):
        """Calculate the current flow rate."""
        return self.frequency * self._rate


flow_sensor = FlowSensor(Pin(19, Pin.IN), 1_000)


def init(loop):
    temp_sensor.init(loop)
    asyncio.create_task(valve.state(False))
