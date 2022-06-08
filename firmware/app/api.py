import gc
import logging
import re
from sys import print_exception

import picoweb
import uasyncio as asyncio
import ujson as json
import utemplate.recompile

from . import clock, graph, hal, irrigation, log
from .settings import settings
from .util import convert_vals

app = picoweb.WebApp(__name__)
app.template_loader = utemplate.recompile.Loader(app.pkg, "templates")
logger = logging.getLogger(__name__)


def _preflight_headers(req):
    headers = {"Access-Control-Allow-Origin": req.headers[b"Origin"].decode()}
    for header in ("Access-Control-Request-Method", "Access-Control-Request-Headers"):
        if header.encode() in req.headers:
            headers[
                header.replace("Request", "Allow").replace("hod", "hods")
            ] = req.headers[header.encode()].decode()
    return headers


def _preflight(req, resp):
    headers = _preflight_headers(req)
    yield from picoweb.start_response(resp, headers=headers)


def cors(f):
    """Provide CORS headers for this endpoint."""

    def _cors(req, resp):
        if req.method == "OPTIONS":
            # logger.debug("preflighting")
            yield from _preflight(req, resp)
        elif b"Origin" in req.headers:
            # logger.debug("setting headers")
            headers = _preflight_headers(req)
            yield from f(req, resp, headers)
        else:
            # logger.debug("no CORS, calling {}".format(f.__name__))
            yield from f(req, resp)

    return _cors


@app.route("/")
async def index(req, resp):
    await picoweb.start_response(resp, content_type="text/html")
    await app.render_template(resp, "index.html", (_report_status(),))


async def json_response(resp, data: dict, headers=None, status=200):
    """Return a JSON response."""
    await picoweb.start_response(
        resp, content_type="application/json", headers=headers, status=status
    )
    await resp.awrite(json.dumps(data))


@app.route(re.compile("/api/status/(.*|)"))
@cors
async def format_status(req, resp, headers=None):
    """Return general status."""
    status = "200"
    try:
        state = _report_status()
        if req.url_match.group(1):
            state = state[req.url_match.group(1)]
    except Exception as e:
        print_exception(e)
        state = {"error": e}
        status = "500"

    await json_response(resp, state, headers, status)


@app.route("/api/self-test/")
async def selftest(req, resp, headers=None):
    """Run self-test routine."""
    try:
        from . import self_test

        await self_test.run_tests()
        await app.sendfile(resp, "/app/static/test.log")
    except Exception as e:
        print_exception(e)
        state = {"exception": e}
        await picoweb.start_response(
            resp, content_type="application/json", headers=headers
        )
        await resp.awrite(json.dumps(state))


async def settable(f, req, resp, headers=None):
    """Set a settable property."""
    status = "200"
    data = None
    if req.method == "PUT":
        if not req.url_match.group(1):
            data = {"error": "No state supplied.  Please use GET to get status."}
            status = "403"
        else:
            f(True if req.url_match.group(1).lower() == "true" else False)

    if not data:
        data = {"value": f()}
    await json_response(resp, data, headers, status)


def property_wrapper(obj, prop):
    """Treat a property like a function."""

    def f(val=None):
        if val:
            setattr(obj, prop, val)
        else:
            return getattr(obj, prop)

    return f


@app.route(re.compile("/api/auto-mode/([Tt]rue|[Ff]alse|)"))
@cors
async def auto_mode(req, resp, headers=None):
    """Turn auto mode on or off."""
    await settable(
        property_wrapper(irrigation.auto_waterer, "auto_mode"), req, resp, headers
    )


@app.route(re.compile("/api/watering/([Tt]rue|[Ff]alse|)"))
@cors
async def watering(req, resp, headers=None):
    """Turn watering mode on or off."""
    await settable(irrigation.auto_waterer.watering, req, resp, headers)


@app.route(re.compile("/api/valve/([Tt]rue|[Ff]alse|)"))
@cors
async def control_valve(req, resp, headers=None):
    """Turn valve on or off."""
    await settable(hal.valve.state, req, resp, headers)


@app.route("/api/settings/")
@cors
async def allsettings(req, resp, headers=None):
    """Get all settings."""
    await json_response(resp, settings.settings, headers)


@app.route(re.compile("^/api/settings/(.+)/(.*)"))
@cors
async def setting(req, resp, headers=None):
    """Get or set a particular setting."""
    status = "200"
    k = req.url_match.group(1)
    if k not in settings.settings:
        status = "400"
        data = {"error": "Supplied setting {} not found".format(k)}

    if status == "200" and req.method == "PUT":
        v = req.url_match.group(2)
        v = convert_vals(v)

        try:
            settings.set(k, v)
            data = {"value": v}
        except Exception as e:
            data = {"Error", e}
            status = "400"

    elif status == "200":
        data = {"value": settings.get(k)}

    await json_response(resp, data, headers, status)


@app.route("/api/log/")
@cors
async def graph_log(req, resp, headers=None):
    """Get log of values for graph."""
    req.parse_qs()
    n = int(req.form["n"]) if "n" in req.form else 20
    skip = int(req.form["skip"] if "skip" in req.form else 0)

    await picoweb.start_response(resp, content_type="application/json", headers=headers)
    await resp.awrite("[")
    started = False
    for reading in graph.packer.read(n=n, skip=skip):
        if started:
            await resp.awrite(",")
        enc = {
            "soil_temperature": reading.floats[0],
            "soil_humidity": reading.floats[1],
            "valve": reading.bools[0],
            "watering": reading.bools[1],
            "auto_mode": reading.bools[2],
            "timestamp": reading.timestamp,
            "id": reading.id,
        }
        await resp.awrite("{}".format(json.dumps(enc)))
        started = True
    await resp.awrite("]")
    gc.collect()


@app.route("/api/syslog/")
@cors
async def syslog(req, resp, headers=None):
    """Get syslog."""
    req.parse_qs()
    n = int(req.form["n"]) if "n" in req.form else 20
    skip = int(req.form["skip"] if "skip" in req.form else 0)

    await picoweb.start_response(resp, content_type="application/json", headers=headers)
    await resp.awrite("[")
    started = False
    for i, timestamp, line in log.rotating_log.read(n=n, skip=skip):
        if started:
            await resp.awrite(",")
        await resp.awrite(json.dumps({"line": line, "timestamp": timestamp, "id": i}))
        started = True

    await resp.awrite("]")


@app.route("/api/repl/")
@cors
async def fallback(req, resp, headers=None):
    """Fall back to repl."""
    with open("/.fallback", "w") as f:
        f.write("")
    _countdown()
    encoded = json.dumps({"status": "Falling back in 10s"})
    await picoweb.start_response(resp, content_type="application/json", headers=headers)
    await resp.awrite(encoded)


async def _fallback():
    print("Falling back in 10")
    await asyncio.sleep(10)
    from machine import reset

    reset()


def _countdown():
    asyncio.get_event_loop().create_task(_fallback())


@app.route("/api/runtime/")
@cors
async def runtime(req, resp, headers=None):
    """Get runtime."""
    data = {"value": clock.timestr(clock.runtime())}
    await json_response(resp, data, headers)


@app.route("/api/frequency/")
@cors
async def freq(req, resp, headers=None):
    """Get frequency of flow sensor."""
    await json_response(resp, {"value": hal.flow_sensor.frequency}, headers)


@app.route("/api/flowrate/")
@cors
async def flowrate(req, resp, headers=None):
    """Get flow rate of flow sensor."""
    await json_response(resp, {"value": hal.flow_sensor.rate}, headers)


def _report_status():
    report = hal.status()
    report["runtime"] = clock.timestr(clock.runtime())
    report.update(settings.settings)
    return report


async def run_app():
    """Start up the api."""
    app.run(debug=-1, host="0.0.0.0", port="9874", log=logging.getLogger("picoweb"))


def init(loop):
    """Initialise this module."""
    loop.create_task(run_app())
