import json
from datetime import datetime
from pathlib import Path


def load(fn: Path):
    with fn.open() as f:
        data = json.load(f)
    for record in data:
        record["timestamp"] = datetime(*record["timestamp"][:-1])
    return data
