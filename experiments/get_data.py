import json
import operator
from datetime import datetime
from pathlib import Path
from sys import stdout

import requests

HOSTNAME = "irrigation.lan"
logf = Path("data.json")

data = None


def flushprint(*args, **kwargs):
    try:
        end = kwargs.pop("end")
    except KeyError:
        end = "\n"
    stdout.write(" ".join(args) + end, **kwargs)
    stdout.flush()


class DataExhaustedError(Exception):
    pass


class DataValidityError(Exception):
    pass


def load():
    global data
    try:
        with logf.open() as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []


def save():
    with logf.open() as f:
        json.dump(data, f)


def ids():
    return (x["id"] for x in data)


def get(skip=0, n=None):
    url = "http://" + HOSTNAME + f"/api/log/?skip={skip}"
    if n:
        url += f"&n={n}"
    records = requests.get(url).json()
    for record in records:
        record["timestamp"] = datetime(*record["timestamp"][:-1])
    return records


def find_offset(target_id):
    last_id = None
    skip = sum(1 for x in ids() if x > target_id)
    while True:
        id_ = get(skip, 1)[0]["id"]
        if id_ == last_id:
            raise DataExhaustedError(f"Data exhausted when looking for {target_id}.")
        if id_ == target_id:
            break
        skip += id_ - target_id
        last_id = id_
    return skip


def fetch_new():
    global data
    skip = 0
    flushprint("Getting new records", end="")
    while True:
        flushprint(".", end="")
        newest = max(ids())
        records = get(skip)
        new_records = [x for x in records if x["id"] > newest]
        if not new_records:
            break
        data += new_records
        skip += len(records)

    data.sort(key=operator.itemgetter("id"))
    flushprint("")

    try:
        skip = find_offset(min(ids()))
    except DataExhaustedError:
        return

    flushprint("Getting old records", end="")
    while True:
        flushprint(".", end="")
        oldest = min(ids())
        records = get(skip)
        new_records = [x for x in records if x["id"] < oldest]
        if not new_records:
            break
        data += new_records
        skip += len(records)

    flushprint("")

    data.sort(key=operator.itemgetter("id"))


def fetch_one(id_) -> dict:
    skip = find_offset(id_)
    resp = get(skip, 1)[0]
    if resp["id"] != id_:
        raise DataValidityError("Server returned wrong record!")
    return resp


def patch():
    """Workaround possible race condition where offset changes mid-fetch."""
    global data

    all_ids = list(ids())
    next_ids = iter(all_ids)
    next(next_ids)
    missing_ids = [id_ for id_, next_id in zip(all_ids, next_ids) if next_id - id_ > 1]
    flushprint(f"Fetching {len(missing_ids)} missing records.")
    missing = []
    ATTEMPTS = 5
    for id_ in missing_ids:
        for _ in range(ATTEMPTS):
            try:
                missing.append(fetch_one(id_))
                break
            except DataValidityError:
                continue
    data += missing
    data.sort(key=operator.itemgetter("id"))


def setup():
    global data
    if not data:
        data = get()


def main():
    load()
    setup()
    fetch_new()
    patch()
    save()


if __name__ == "__main__":
    main()
