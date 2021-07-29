from packing import PackedReadings
from . import settings

packer = PackedReadings(
    "readings",
    "/app/static/",
    settings.get("log_size", 1440),
    2,
    1,
    keep_logs=settings.get("keep_logs", 3),
)
