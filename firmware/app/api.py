import logging
import re
from sys import print_exception
import gc

import picoweb
import ujson as json
import utemplate.recompile

import uasyncio as asyncio

from . import hal, irrigation, clock, settings, graph, log

app = picoweb.WebApp(__name__)
app.template_loader = utemplate.recompile.Loader(app.pkg, "templates")
logger = logging.getLogger(__name__)


def preflight_headers(req):
    headers = {"Access-Control-Allow-Origin": req.headers[b"Origin"].decode()}
    for header in ("Access-Control-Request-Method", "Access-Control-Request-Headers"):
        if header.encode() in req.headers:
            headers[
                header.replace("Request", "Allow").replace("hod", "hods")
            ] = req.headers[header.encode()].decode()
    return headers


def preflight(req, resp):
    headers = preflight_headers(req)
    yield from picoweb.start_response(resp, headers=headers)


def cors(f):
    def _cors(req, resp):
        if req.method == "OPTIONS":
            logger.debug("preflighting")
            yield from preflight(req, resp)
        elif b"Origin" in req.headers:
            logger.debug("setting headers")
            headers = preflight_headers(req)
            yield from f(req, resp, headers)
        else:
            logger.debug("no CORS, calling {}".format(f.__name__))
            yield from f(req, resp)

    return _cors


@app.route("/")
def index(req, resp):
    yield from picoweb.start_response(resp, content_type="text/html")
    yield from app.render_template(resp, "index.html", (report_status(),))


@app.route("/api/status")
@cors
def format_status(req, resp, headers=None):
    status = "200"
    try:
        state = report_status()
    except Exception as e:
        print_exception(e)
        state = {"error": e}
        status = "500"
    encoded = json.dumps(state)
    yield from picoweb.start_response(
        resp, content_type="application/json", headers=headers, status=status
    )
    yield from resp.awrite(encoded)


@app.route("/api/self-test")
async def selftest(req, resp, headers=None):
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


def settable(f, req, resp, headers=None):
    status = "200"
    encoded = None
    if req.method == "PUT":
        if not req.url_match.group(1):
            encoded = json.dumps(
                {"error": "No state supplied.  Please use GET to get status."}
            )
            status = "403"
        else:
            f(True if req.url_match.group(1) == "on" else False)

    if not encoded:
        encoded = json.dumps({"value": f()})

    yield from picoweb.start_response(
        resp, content_type="application/json", headers=headers, status=status
    )
    yield from resp.awrite(encoded)


@app.route(re.compile("/api/auto-mode/(on|off|)"))
@cors
def auto_mode(req, resp, headers=None):
    yield from settable(irrigation.auto_waterer.auto_mode, req, resp, headers)


@app.route(re.compile("/api/watering/(on|off|)"))
@cors
def watering(req, resp, headers=None):
    yield from settable(irrigation.auto_waterer.watering, req, resp, headers)


@app.route(re.compile("/api/valve/(on|off|)"))
@cors
def control_valve(req, resp, headers=None):
    yield from settable(hal.valve.state, req, resp, headers)


@app.route(re.compile("^/api/settings/(.*)/(.*|)"))
@cors
def setting(req, resp, headers=None):
    status = "200"
    k = req.url_match.group(1)
    if k not in settings.settings:
        status = "400"
        encoded = {"error": "Supplied setting {} not found".format(k)}

    if status == "200" and req.method == "PUT":
        v = req.url_match.group(2)
        try:
            v = float(v)
        except ValueError:
            pass
        try:
            v = int(v)
        except ValueError:
            pass
        if v == "True":
            v = True
        if v == "False":
            v = False

        try:
            settings.set(k, v)
            encoded = json.dumps({k: v})
        except Exception as e:
            encoded = json.dumps({"Error", e})
            status = "400"
    elif status == "200":
        encoded = json.dumps({k: settings.get(k)})
    yield from picoweb.start_response(
        resp, content_type="application/json", headers=headers, status=status
    )
    yield from resp.awrite(encoded)


@app.route("/api/log")
@cors
def graph_log(req, resp, headers=None):
    req.parse_qs()
    n = int(req.form["n"]) if "n" in req.form else 20
    skip = int(req.form["skip"] if "skip" in req.form else 0)

    yield from picoweb.start_response(
        resp, content_type="application/json", headers=headers
    )
    yield from resp.awrite("[")
    started = False
    for reading in graph.packer.read(n=n, skip=skip):
        if started:
            yield from resp.awrite(",")
        enc = {
            "soil_temperature": reading.floats[0],
            "soil_humidity": reading.floats[1],
            "valve": reading.bools[0],
            "watering": reading.bools[1],
            "auto_mode": reading.bools[2],
            "timestamp": reading.timestamp,
        }
        yield from resp.awrite("{}".format(json.dumps(enc)))
        started = True
    yield from resp.awrite("]")
    gc.collect()


@app.route("/api/syslog")
@cors
def syslog(req, resp, headers=None):
    req.parse_qs()
    n = int(req.form["n"]) if "n" in req.form else 20
    skip = int(req.form["skip"] if "skip" in req.form else 0)

    yield from picoweb.start_response(
        resp, content_type="application/json", headers=headers
    )
    yield from resp.awrite("[")
    started = False
    for line in log.rotating_log.read(n=n, skip=skip):
        if started:
            yield from resp.awrite(",")
        yield from resp.awrite(json.dumps({"line": line}))
        started = True

    yield from resp.awrite("]")


@app.route("/api/repl")
@cors
async def fallback(req, resp, headers=None):
    with open("/fallback", "w") as f:
        f.write("")
    countdown()
    encoded = json.dumps({"status": "Falling back in 10s"})
    await picoweb.start_response(resp, content_type="application/json", headers=headers)
    await resp.awrite(encoded)


async def _fallback():
    print("Falling back in 10")
    await asyncio.sleep(10)
    from machine import reset

    reset()


def countdown():
    asyncio.get_event_loop().create_task(_fallback())


def report_status():
    report = hal.status()
    report["runtime"] = clock.timestr(clock.runtime())
    report.update(settings.settings)
    return report


async def run_app():
    app.run(debug=0, host="0.0.0.0", port="80", log=logging.getLogger("picoweb"))


def init(loop):
    loop.create_task(run_app())
