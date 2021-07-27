from json import load, dump

settings_file = "settings.json"
settings = {}


def load_settings():
    global settings
    with open(settings_file, "r") as f:
        settings = load(f)


def set(k, v):
    settings[k] = v
    with open(settings_file, "w") as f:
        dump(settings, f)


def get(k, fallback=None):
    try:
        return settings[k]
    except KeyError:
        set(k, fallback)
        return fallback


def init():
    try:
        load_settings()
    except Exception:
        set("created", True)
        load_settings()
