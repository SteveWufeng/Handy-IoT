import copy
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = PROJECT_ROOT / "config.json"

DEFAULTS = {
    "calendar": {
        "ics_url": "",
        "days_ahead": 14,
        "max_events": 40,
        "refresh_minutes": 15,
    },
    "pomodoro": {
        "work_minutes": 25,
        "break_minutes": 5,
        "long_break_minutes": 15,
        "cycles": 4,
        "auto_start": True,
    },
    "music": {
        "volume": 70,
        "search_results": 20,
        "quick_searches": ["lofi hip hop", "jazz cafe", "piano classical"],
    },
    "display": {"fps": 30},
    "audio": {"enabled": True},
    "branding": {"name": "Handy"},
}


def _merge(base, override):
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


class Config:
    def __init__(self, path=None):
        env_path = os.environ.get("HANDY_CONFIG")
        self.path = Path(env_path).expanduser() if env_path else Path(path) if path else DEFAULT_PATH
        self.data = copy.deepcopy(DEFAULTS)
        self.load()

    def load(self):
        self.data = copy.deepcopy(DEFAULTS)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        if isinstance(raw, dict):
            self.data = _merge(self.data, raw)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def get(self, dotted, default=None):
        node = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted, value):
        parts = dotted.split(".")
        node = self.data
        for part in parts[:-1]:
            if not isinstance(node.get(part), dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value

    def reload(self):
        self.load()
