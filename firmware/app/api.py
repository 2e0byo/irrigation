import logging
import re
from sys import print_exception

import picoweb
import ujson as json
import uos as os
import utemplate

import uasyncio as asyncio

from . import hal, irrigation, clock

app = picoweb.WebApp(__name__)
app.template_loader = utemplate.recompile.Loader

@app.route("/api/status", methods=["GET"])
def format_status(req, resp):
    try:
        state = status()
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


@app.route(re.compile("/api/valve/(on|off)"), methods=["GET", "PUT"])
def control_valve(req, resp):
    state = True if req.url_match.group(1) == "on" else False
    hal.valve.state = state
    if req.method == "PUT":
        yield from status(req, resp)
    else:
        headers = {"Location": "/api/static/index.html"}
        yield from picoweb.start_response(resp, status="303", headers=headers)


@app.route("/api/repl")
async def fallback(req, resp):  # we should authenticate later
    with open("/fallback", "w") as f:
        f.write("")
    countdown()
    encoded = json.dumps({"status": "Falling back in 10s"})
    await picoweb.start_response(resp, content_type="application/json")
    await resp.awrite(encoded)


@app.route(re.compile("^/static/(.+)"))
def static(req, resp):
    print("Called static")
    print(req.url_match)
    fn = "static/{}".format(req.url_match.group(1))
    try:
        os.stat(fn)
    except OSError:
        yield from picoweb.start_response(resp, content_type="application/json")
        encoded = json.dumps({"Error": "File not found"})
        yield from resp.awrite(encoded)

    content_types = {
        "json": "application/json",
        "html": "text/html",
    }
    try:
        ext = fn.split(".")[:-1]
        if ext in content_types:
            ctype = content_types[ext]
        else:
            ctype = "text/plain"
    except Exception:
        ctype = "text/plain"
        yield from picoweb.start_response(resp, content_type=ctype)
    with open(fn) as f:
        yield from resp.awrite(f.read())


async def _fallback():
    print("Falling back in 10")
    await asyncio.sleep(10)
    from machine import reset

    reset()


def countdown():
    asyncio.get_event_loop().create_task(_fallback())


def status():
    report = hal.status()
    report["runtime"] = clock.clockstr(clock.runtime())
    return report


async def run_app():
    app.run(debug=True, host="0.0.0.0", port="80", log=logging.getLogger("picoweb"))


def init(loop):
    loop.create_task(run_app())
