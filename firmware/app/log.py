import logging
from packing.text import RotatingLog
from . import settings

rotating_log = RotatingLog(
    "log",
    "/app/static/",
    log_lines=settings.get("syslog_lines", 200),
    keep_logs=2,
    timestamp=False,
)


class RotatingLogHandler(logging.Handler):
    def __init__(self, log):
        super().__init__()
        self.log = log

    def emit(self, record):
        if record.levelno >= self.level:
            self.log.append(self.formatter.format(record))


rotating_handler = RotatingLogHandler(rotating_log)
rotating_handler.setLevel(logging.INFO)
rotating_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s")
)
