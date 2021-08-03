import uasyncio as asyncio
from time import localtime
from . import settings
from .hal import valve, soil_humidity
import logging

logger = logging.getLogger("irrigation")

auto_mode = True
watering = False
WATER_LOOP_DELAY = 60


async def schedule_loop():
    global watering
    while True:
        h, m = localtime()[3:5]
        if h == settings.get("watering hours", [6, 21]) and not m:
            logger.info("Schedule watering")
            watering = True
        await asyncio.sleep(60)


async def auto_water_loop():
    global watering
    while True:
        while auto_mode:
            try:
                elapsed = 0
                if not valve.state:
                    if watering and soil_humidity < settings.get(
                        "lower_humidity_threshold", 65
                    ):
                        logger.info("Started watering")
                        valve.state = True
                        elapsed = 1
                        await asyncio.sleep_ms(500)
                else:
                    if soil_humidity > settings.get(
                        "upper_humidity_threshold", 70
                    ) or elapsed > settings.get("watering_minutes", 30):
                        logger.info("Stopped watering")
                        valve.state = False
                        watering = False
                        elapsed = 0
                    elapsed += 1
                    await asyncio.sleep(WATER_LOOP_DELAY)
            except Exception as e:
                logger.exc(e)

        while not auto_mode:
            await asyncio.sleep_ms(100)


def init(loop):
    loop.create_task(auto_water_loop())
    loop.create_task(schedule_loop())
