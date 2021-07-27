from machine import Pin
from sys import stdout, print_exception


def fallback_connect():
    import secrets
    import network

    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print("connecting to network...")
        sta_if.active(True)
        sta_if.connect(secrets.wifi_SSID, secrets.wifi_PSK)
        while not sta_if.isconnected():
            pass
    print("network config:", sta_if.ifconfig())


try:
    import logging

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG,
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler(stdout)
    sh.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
    )
    logger.addHandler(sh)
    logger.debug("Logger initialised")

    fallback_connect()

    print("import app")
    import app

    app.start(logger)

except Exception as e:
    print("Falling back....")
    print_exception(e)
    fallback_connect()
    try:
        logger.error(print_exception(e))
        logger.info("Running failsafe repl.")
    except Exception:
        print_exception(e)
        print("Running failsafe repl.")
