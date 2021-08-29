import logging
import re
from sys import print_exception
import gc

import picoweb
import ujson as json
import utemplate.recompile

import uasyncio as asyncio

from . import hal, irrigation, clock, settings, graph

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
    yield from app.render_template(resp, "index.html", (status(),))


@app.route("/api/status")
@cors
def format_status(req, resp, headers=None):
    print("in format_status")
    try:
        state = status()
    except Exception as e:
        print_exception(e)
        state = {"exception": e}
    encoded = json.dumps(state)
    yield from picoweb.start_response(
        resp, content_type="application/json", headers=headers
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
        await picoweb.start_response(
            resp, content_type="application/json", headers=headers
        )
        await req.awrite("{Exception:")
        await req.awrite(e)
        await req.awrite("}")


@app.route(re.compile("/api/mode/(manual|auto|)"))
@cors
def mode(req, resp, headers=None):
    if req.method == "PUT":
        if req.url_match.group(1) == "manual":
            irrigation.auto_mode = False
        elif req.url_match.group(1) == "auto":
            irrigation.auto_mode = True
    encoded = json.dumps({"mode": "auto" if irrigation.auto_mode else "manual"})
    yield from picoweb.start_response(
        resp, content_type="application/json", headers=headers
    )
    yield from resp.awrite(encoded)


@app.route(re.compile("/api/watering/(on|off)"))
@cors
def watering(req, resp, headers=None):
    if req.method == "PUT":
        irrigation.watering = True if req.url_match.group(1) == "on" else False
    encoded = json.dumps({"watering": irrigation.watering})
    yield from picoweb.start_response(
        resp, content_type="application/json", headers=headers
    )
    yield from resp.awrite(encoded)


@app.route(re.compile("/api/valve/(on|off)"))
@cors
def control_valve(req, resp, headers=None):
    if req.method == "PUT":
        state = True if req.url_match.group(1) == "on" else False
        hal.valve.state = state
    encoded = json.dumps({"valve": hal.valve.state})
    yield from picoweb.start_response(
        resp, content_type="application/json", headers=headers
    )
    yield from resp.awrite(encoded)


@app.route(re.compile("/api/settings/(.*)/(.*)|"))
@cors
def setting(req, resp, headers=None):
    k = req.url_match.group(1)
    if req.method == "PUT":
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
    else:
        encoded = json.dumps({k: settings.get(k)})
    yield from picoweb.start_response(
        resp, content_type="application/json", headers=headers
    )
    yield from resp.awrite(encoded)


@app.route("/api/log")
@cors
def log(req, resp, headers=None):
    req.parse_qs()
    n = int(req.form["n"]) if "n" in req.form else 20
    skip = int(req.form["skip"] if "skip" in req.form else 0)

    yield from picoweb.start_response(resp, content_type="application/json")
    yield from resp.awrite("[")
    started = False
    for floats, bools in graph.packer.read(n=n, skip=skip):
        if started:
            yield from resp.awrite(",")
        enc = {
            "soil_temperature": floats[0],
            "soil_humidity": floats[1],
            "valve": bools[0],
        }
        yield from resp.awrite("{}".format(json.dumps(enc)))
        started = True
    yield from resp.awrite("]")
    gc.collect()


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


def status():
    report = hal.status()
    report["runtime"] = clock.timestr(clock.runtime())
    report.update(settings.settings)
    return report


async def run_app():
    app.run(debug=True, host="0.0.0.0", port="80", log=logging.getLogger("picoweb"))


def init(loop):
    loop.create_task(run_app())
