from packing.packed import PackedRotatingLog
from . import settings

packer = PackedRotatingLog(
    "readings",
    "/app/static/",
    log_lines=settings.get("log_size", 1440),
    floats=2,
    ints=0,
    bools=1,
    keep_logs=settings.get("keep_logs", 3),
    timestamp=True,
)
