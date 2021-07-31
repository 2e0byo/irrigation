import uasyncio as asyncio
from time import localtime
from . import settings
from .hal import valve, soil_humidity
import logging

logger = logging.getLogger("irrigation")

auto_mode = True


async def auto_water_loop():
    while True:
        while auto_mode:
            try:
                elapsed = 0
                if not valve.state:
                    h, m = localtime()[3:5]
                    if (
                        h in settings.get("watering_hours", [6, 21])
                        and not m
                        and soil_humidity < settings.get("lower_humidity_threshold", 65)
                    ):
                        valve.state = True
                        elapsed = 1
                else:
                    if soil_humidity > settings.get(
                        "upper_humidity_threshold", 70
                    ) or elapsed > settings.get("watering_minutes", 30):
                        valve.state = False
                        elapsed = 0
                    elapsed += 1
            except Exception as e:
                logger.exc(e)

            await asyncio.sleep(60)

        while not auto_mode:
            await asyncio.sleep_ms(100)


def init(loop):
    loop.create_task(auto_water_loop())
