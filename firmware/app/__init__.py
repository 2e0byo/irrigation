import uos

if "fallback" in uos.listdir("/"):
    uos.remove("/fallback")
    raise Exception("Falling back to repl this once")


def start(logger):
    print("Starting up")

    import gc
    from time import sleep

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

    print("Loading setting.")
    from . import settings

    settings.init()

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
    import irrigation

    print("Initialising...")
    loop = asyncio.get_event_loop()
    api.init(loop)
    clock.init(loop)
    hal.init(loop)
    irrigation.init(loop)
    gc.collect()
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())

    logger.info("Everything started.")

    try:
        loop.run_forever()
    finally:
        print("Loop ended")
        sleep(60)
        machine.reset()
