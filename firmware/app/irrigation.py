import uasyncio as asyncio
from time import localtime
from . import hal
from .settings import settings
import logging
from sys import print_exception


class AutoWaterer:
    def __init__(self, name, sensor, valve, loop_delay=60):
        self.name = name
        self.loop_delay = loop_delay
        self._watering = False
        self._auto_mode = True
        self.sensor = sensor
        self.valve = valve
        self.logger = logging.getLogger(self.name)
        # populate settings on init in case needed elsewhere
        # e.g. for api/web status page
        self.lower_humidity
        self.upper_humidity
        self.watering_hours
        self.watering_minutes

    def auto_mode(self, val=None):
        if val:
            self._auto_mode = True
        elif val is False:
            self._auto_mode = False
        return self._auto_mode

    def watering(self, val=None):
        if val:
            self._watering = True
        elif val is False:
            self._watering = False
        return self._watering

    @property
    def lower_temperature(self):
        return settings.get("{}--lower_temperature".format(self.name), 5)

    @property
    def lower_humidity(self):
        return settings.get("{}--lower_humidity_threshold".format(self.name), 65)

    @property
    def upper_humidity(self):
        return settings.get("{}--upper_humidity_threshold".format(self.name), 75)

    @property
    def watering_hours(self):
        return settings.get("{}--watering_hours".format(self.name), [6, 12])

    @property
    def watering_minutes(self):
        return settings.get("{}--watering_minutes".format(self.name), 30)

    async def schedule_loop(self):
        while True:
            h, m = localtime()[3:5]
            if h in self.watering_hours and m == 1:
                self.logger.info("Scheduling watering")
                self.watering(True)
            await asyncio.sleep(60)

    async def auto_water_loop(self):
        while True:
            elapsed = 0
            while self.auto_mode:
                try:
                    if not self.valve.state():
                        if (
                            self.watering()
                            and self.sensor.humidity < self.lower_humidity
                            and self.sensor.temperature > self.lower_temperature
                        ):
                            self.logger.info(
                                "Started watering humidity {} < {}".format(
                                    self.sensor.humidity, self.lower_humidity
                                )
                            )
                            self.valve.state(True)
                            elapsed += 0.5 / 60

                        await asyncio.sleep_ms(500)
                        continue

                    else:
                        if (
                            self.sensor.humidity > self.upper_humidity
                            or elapsed > self.watering_minutes
                        ):
                            self.logger.info("Stopped watering")
                            self.valve.state(False)
                            self.watering(False)
                            elapsed = 0
                        elapsed += self.loop_delay / 60

                except Exception as e:
                    self.logger.exc(e, "Error in watering loop")

                await asyncio.sleep(self.loop_delay)

            while not self.auto_mode:
                await asyncio.sleep_ms(100)

    def init(self, loop):
        loop.create_task(self.auto_water_loop())
        loop.create_task(self.schedule_loop())


auto_waterer = AutoWaterer("waterer1", hal.temp_sensor, hal.valve)


def init(loop):
    auto_waterer.init(loop)
