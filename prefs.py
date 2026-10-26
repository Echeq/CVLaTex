"""User preferences in the per-OS application data directory.

Windows keeps %LOCALAPPDATA%\\CVLaTeX\\prefs.json; macOS uses
~/Library/Application Support/CVLaTeX and other systems follow the XDG base
directory spec ($XDG_DATA_HOME or ~/.local/share) + /CVLaTeX.

Las claves son inglesas desde la migracion: paper, margins, font_size,
auto_compile, breakpoint, latex_path, setup_dismissed, theme, colors, split,
ui_language y ui_language_chosen. load() migra una sola vez los ficheros
escritos con las claves antiguas en espanol y guarda una copia prefs.json.bak
que nunca se pisa.
"""

import json
import os
import shutil
import sys


def _app_dir_for(platform=None, env=None, home=None):
    """Application data directory (with the CVLaTeX subfolder) for a platform.

    Pure function so the per-OS paths are unit-testable: `platform` defaults
    to `sys.platform`, `env` to `os.environ` and `home` to the user home.
    """
    platform = sys.platform if platform is None else platform
    env = os.environ if env is None else env
    home = os.path.expanduser("~") if home is None else home
    if platform == "win32":
        base = env.get("LOCALAPPDATA") or home
    elif platform == "darwin":
        base = os.path.join(home, "Library", "Application Support")
    else:
        base = env.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(base, "CVLaTeX")


APP_DIR = _app_dir_for()
CACHE_DIR = os.path.join(APP_DIR, "cache")
BUILD_DIR = os.path.join(CACHE_DIR, "build")
TINYTEX_DIR = os.path.join(APP_DIR, "tinytex")
PREFS_FILE = os.path.join(APP_DIR, "prefs.json")

DEFAULTS = {
    "paper": "a4",
    "margins": {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0},
    "font_size": 11,
    "auto_compile": True,
    "breakpoint": 960,
    "latex_path": None,
    "setup_dismissed": False,
    "theme": "system",
    # Document palette: "#RRGGBB" values or "" (empty = the template's own
    # color). "text" tints the whole PDF body.
    "colors": {"primary": "", "secondary": "", "text": "", "gray": ""},
    "split": 50,
    "ui_language": "en",
    "ui_language_chosen": False,
}

# Frozen migration: legacy Spanish prefs key -> new English key.
_RENAMES = {
    "papel": "paper",
    "margenes": "margins",
    "fuente": "font_size",
    "autocompilar": "auto_compile",
    "tema": "theme",
    "colores": "colors",
}

# Renamed values/nested keys inside the migrated keys.
_TEMAS = {"claro": "light", "oscuro": "dark", "sistema": "system"}
_COLORES = {
    "primario": "primary",
    "secundario": "secondary",
    "texto": "text",
    "gris": "gray",
}

# Keys merged key by key: a partially saved dict never loses new subkeys.
_FUSIONABLES = ("margins", "colors")

_CACHE = None


def _ensure_dirs():
    for d in (APP_DIR, CACHE_DIR, BUILD_DIR):
        os.makedirs(d, exist_ok=True)


def _normalizar_legado(guardado):
    """Traduce a las claves nuevas un prefs guardado con las claves antiguas."""
    nuevos = {}
    for clave, valor in guardado.items():
        if clave not in _RENAMES:
            continue
        nueva = _RENAMES[clave]
        if nueva == "colors" and isinstance(valor, dict):
            valor = {_COLORES.get(k, k): v for k, v in valor.items()}
        elif nueva == "theme" and isinstance(valor, str):
            valor = _TEMAS.get(valor, valor)
        nuevos[nueva] = valor
    return nuevos


def _normalizar_nuevo(guardado):
    """Claves del prefs guardado que ya usan los nombres nuevos."""
    return {k: v for k, v in guardado.items() if k not in _RENAMES}


def _fusionar(destino, origen):
    """Vuelca `origen` en `destino`; margins/colors se fusionan clave a clave."""
    for clave, valor in origen.items():
        if clave in _FUSIONABLES and isinstance(valor, dict):
            destino[clave].update(valor)
        else:
            destino[clave] = valor


def _copia_backup():
    """Copia prefs.json a prefs.json.bak sin pisar un .bak existente."""
    ruta = PREFS_FILE + ".bak"
    if os.path.exists(ruta):
        return
    try:
        shutil.copy2(PREFS_FILE, ruta)
    except OSError:
        pass


def _escribir(data):
    tmp = PREFS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PREFS_FILE)


def load():
    global _CACHE
    if _CACHE is not None:
        return dict(_CACHE)
    data = json.loads(json.dumps(DEFAULTS))
    _ensure_dirs()
    migrado = False
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                guardado = json.load(f)
            if isinstance(guardado, dict):
                # Primero las claves antiguas; las nuevas ganan si conviven.
                _fusionar(data, _normalizar_legado(guardado))
                _fusionar(data, _normalizar_nuevo(guardado))
                migrado = any(clave in guardado for clave in _RENAMES)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            pass
    _CACHE = data
    if migrado:
        # Migracion de una sola vez: copia de seguridad del original y
        # persistencia del fichero ya migrado.
        _copia_backup()
        try:
            _escribir(data)
        except OSError:
            pass
    return dict(_CACHE)


def save(data):
    global _CACHE
    _ensure_dirs()
    _CACHE = dict(data)
    _escribir(data)


def set(k, v):
    data = load()
    data[k] = v
    save(data)


def get(k, default=None):
    data = load()
    return data.get(k, default if default is not None else DEFAULTS.get(k))
