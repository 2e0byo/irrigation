import uasyncio as asyncio
from time import localtime
from . import settings
from . import hal
import logging
from sys import print_exception

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
        elapsed = 0
        while auto_mode:
            try:
                if not hal.valve.state:
                    if watering and hal.soil_humidity < settings.get(
                        "lower_humidity_threshold", 65
                    ):
                        logger.info("Started watering")
                        hal.valve.state = True
                        elapsed += 0.5 / 60

                    await asyncio.sleep_ms(500)
                    continue

                else:
                    if hal.soil_humidity > settings.get(
                        "upper_humidity_threshold", 70
                    ) or elapsed > settings.get("watering_minutes", 30):
                        logger.info("Stopped watering")
                        hal.valve.state = False
                        watering = False
                        elapsed = 0
                    elapsed += WATER_LOOP_DELAY / 60

            except Exception as e:
                print_exception(e)

            await asyncio.sleep(WATER_LOOP_DELAY)

        while not auto_mode:
            await asyncio.sleep_ms(100)


def init(loop):
    loop.create_task(auto_water_loop())
    loop.create_task(schedule_loop())
