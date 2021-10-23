from json import load, dump


class Settings:
    def __init__(self, fn):
        self.fn = fn
        self.settings = {}
        try:
            self.load_settings()
        except Exception:
            self.set("created", True)

    def load_settings(self):
        with open(self.fn, "r") as f:
            self.settings = load(f)

    def set(self, k, v):
        self.settings[k] = v
        with open(self.fn, "w") as f:
            dump(self.settings, f)

    def get(self, k, fallback=None):
        try:
            return self.settings[k]
        except KeyError:
            if fallback:
                self.set(k, fallback)
                return fallback
            else:
                raise KeyError("No such setting: {}".format(k))


settings = Settings("settings.json")
