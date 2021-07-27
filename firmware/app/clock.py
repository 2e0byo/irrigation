import logging
from time import localtime, mktime
from sys import print_exception

import network
import ntptime
import uasyncio as asyncio
from machine import RTC

rtc = RTC()
rtc.datetime()
wlan = network.WLAN(network.STA_IF)

logger = logging.getLogger(__name__)
boot_time = None


def runtime():
    if not boot_time:
        return None
    else:
        return mktime(localtime()) - mktime(boot_time)


def clockstr(time=None):
    if not time:
        time = rtc.datetime()
    timestamp = "{}-{}-{}".format(*time[:3])
    timestamp += " {}:{}:{}".format(*time[4:7])
    return timestamp


async def sync_clock():
    global boot_time
    while True:
        await asyncio.sleep(60)
        try:
            ntptime.settime()
            rtc.datetime()
            if not boot_time:
                boot_time = localtime()
        except OSError as e:  # errors occasionally
            print_exception(e)
        await asyncio.sleep(300)


def init(loop):
    loop.create_task(sync_clock())
