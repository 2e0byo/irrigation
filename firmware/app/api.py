import logging
import re
from sys import print_exception

import picoweb
import ujson as json
import uos as os

import uasyncio as asyncio

app = picoweb.WebApp(__name__)
from . import hal, irrigation


@app.route("/api/status", methods=["GET"])
def status(req, resp):
    try:
        state = hal.status()
    except Exception as e:
        print_exception(e)
        state = {"exception": e}
    encoded = json.dumps(state)
    yield from picoweb.start_response(resp, content_type="application/json")
    yield from resp.awrite(encoded)


@app.route("/api/self-test")
async def selftest(req, resp):
    try:
        from . import self_test

        await self_test.run_tests()
        await picoweb.start_response(resp, content_type="text/plain")
        with open("/static/test.log") as f:
            for line in f.readlines():
                await resp.awrite(line)
    except Exception as e:
        print_exception(e)
        await status(req, resp)


@app.route(re.compile("/api/mode/(manual|auto|)"), methods=["GET", "PUT"])
def mode(req, resp):
    if req.method == "PUT":
        if req.url_match.group(1) == "manual":
            irrigation.auto_mode = False
        elif req.url_match.group(1) == "auto":
            irrigation.auto_mode = True
    encoded = json.dumps({"mode": "auto" if irrigation.auto_mode else "manual"})
    yield from picoweb.start_response(resp, content_type="application/json")
    yield from resp.awrite(encoded)


@app.route(re.compile("/api/hardware/(valve)/(on|off)"), methods=["PUT"])
def control_hardware(req, resp):
    output = req.url_match.group(1)
    state = True if req.url_match.group(2) == "on" else False
    setattr(hal, output, state)
    yield from status()


@app.route("/api/repl")
async def fallback(req, resp):  # we should authenticate later
    with open("/fallback", "w") as f:
        f.write("")
    countdown()
    encoded = json.dumps({"status": "Falling back in 10s"})
    await picoweb.start_response(resp, content_type="application/json")
    await resp.awrite(encoded)


async def _fallback():
    print("Falling back in 10")
    await asyncio.sleep(10)
    from machine import reset

    reset()


def countdown():
    asyncio.get_event_loop().create_task(_fallback())


async def run_app():
    app.run(debug=True, host="0.0.0.0", port="80", log=logging)


def init(loop):
    loop.create_task(run_app())
