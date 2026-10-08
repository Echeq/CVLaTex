import json
import os


LOCALAPPDATA = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
APP_DIR = os.path.join(LOCALAPPDATA, "CVLaTeX")
CACHE_DIR = os.path.join(APP_DIR, "cache")
BUILD_DIR = os.path.join(CACHE_DIR, "build")
TINYTEX_DIR = os.path.join(APP_DIR, "tinytex")
PREFS_FILE = os.path.join(APP_DIR, "prefs.json")

DEFAULTS = {
    "papel": "a4",
    "margenes": {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0},
    "fuente": 11,
    "autocompilar": True,
    "breakpoint": 960,
    "latex_path": None,
    "setup_dismissed": False,
    "tema": "sistema",
}

_CACHE = None


def _ensure_dirs():
    for d in (APP_DIR, CACHE_DIR, BUILD_DIR):
        os.makedirs(d, exist_ok=True)


def load():
    global _CACHE
    if _CACHE is not None:
        return dict(_CACHE)
    data = json.loads(json.dumps(DEFAULTS))
    _ensure_dirs()
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                for k, v in saved.items():
                    if k == "margenes" and isinstance(v, dict):
                        data["margenes"].update(v)
                    else:
                        data[k] = v
        except (json.JSONDecodeError, OSError):
            pass
    _CACHE = data
    return dict(_CACHE)


def save(data):
    global _CACHE
    _ensure_dirs()
    _CACHE = dict(data)
    tmp = PREFS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PREFS_FILE)


def set(k, v):
    data = load()
    data[k] = v
    save(data)


def get(k, default=None):
    data = load()
    return data.get(k, default if default is not None else DEFAULTS.get(k))