# general imports
from time import sleep

# micropython specific imports
try:
    from micropython import const

    upython = True
except ImportError:
    upython = False

    def const(x):
        """Wrapper fn for micropython's const."""
        return x


if upython:
    from sys import print_exception

    import uasyncio as asyncio
    import uos

    try:
        uos.remove("/.fallback")
        raise Exception("Falling back to repl this once.")
    except OSError:
        pass
else:
    import asyncio


async def wait_safe():
    """Wait and then flag an upgraded system as safe."""
    await asyncio.sleep(60 * 10)
    try:
        uos.remove("/.runsafe")
    except OSError:
        pass


def start(logger):
    """Start the app."""
    print("Starting up")

    import gc

    import machine
    import uasyncio as asyncio

    reset_causes = (
        "Power on",
        "Hard reset",
        "WDT reset",
        "Deepsleep reset",
        "Soft reset",
    )

    gc.enable()
    reset_cause = reset_causes[machine.reset_cause() - 1]
    logger.info("Booting up, reason is {}".format(reset_cause))

    print("Loading Hal")
    from . import hal

    gc.collect()
    print("Loading clock")
    from . import clock

    gc.collect()
    print("Loading api")
    from . import api

    gc.collect()
    print("Loading irrigation")
    from . import irrigation

    print("Initialising...")
    loop = asyncio.get_event_loop()
    api.init(loop)
    clock.init(loop)
    gc.collect()
    print("Syncing clock...")
    i = 0
    while i < 10 and not clock.clock_synced():
        try:
            clock.ntptime.settime()
        except (OverflowError, OSError) as e:
            print("Failed to sync")
            print(clock.rtc.datetime())
            print_exception(e)
            sleep(1)
            i += 1
    if i == 100:
        logger.warning("Failed to sync clock.")
    if clock.clock_synced():
        clock.boot_time = clock.localtime()

    hal.init(loop)
    irrigation.init(loop)
    gc.collect()
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())

    logger.info("Everything started.")
    loop.create_task(wait_safe())

    try:
        loop.run_forever()
    finally:
        print("Loop ended")
        sleep(60)
        machine.reset()
