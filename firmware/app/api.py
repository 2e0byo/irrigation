import logging
import re
from sys import print_exception

import picoweb
import ujson as json
import utemplate.recompile

import uasyncio as asyncio

from . import hal, irrigation, clock, settings, graph

app = picoweb.WebApp(__name__)
app.template_loader = utemplate.recompile.Loader(app.pkg, "templates")


@app.route("/")
def index(req, resp):
    yield from app.render_template(resp, "index.html", (status(),))


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
        await app.sendfile(resp, "/app/static/test.log")
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
        headers = {"Location": "/"}
        yield from picoweb.start_response(resp, status="303", headers=headers)


@app.route(re.compile("/api/settings/(.*)/(.*)"), methods=["PUT"])
def setting(req, resp):
    k = req.url_match.group(1)
    v = req.url_match.group(2)
    try:
        v = float(v)
    except ValueError:
        pass
    try:
        v = int(v)
    except ValueError:
        pass

    try:
        settings.set(k, v)
    except Exception as e:
        print_exception(e)
    yield from status(req, resp)


@app.route("/api/log")
def log(req, resp):
    yield from picoweb.start_response(resp, content_type="application/json")
    for floats, bools in graph.packer.read():
        enc = {
            "soil_temperature": floats[0],
            "soil_humidity": floats[1],
            "valve": bools[0],
        }
        yield from resp.awrite(enc)


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


def status():
    report = hal.status()
    report["runtime"] = clock.timestr(clock.runtime())
    report.update(settings.settings)
    return report


async def run_app():
    app.run(debug=True, host="0.0.0.0", port="80", log=logging.getLogger("picoweb"))


def init(loop):
    loop.create_task(run_app())
