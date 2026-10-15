# -*- coding: utf-8 -*-
"""Per-OS application data directory of prefs.

The module-level attributes (APP_DIR, CACHE_DIR, BUILD_DIR, TINYTEX_DIR,
PREFS_FILE) stay in place; only their base changes per platform. These tests
exercise the pure path helper (no filesystem writes, no GUI).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import prefs  # noqa: E402


def test_app_dir_for_windows_uses_localappdata():
    result = prefs._app_dir_for(
        "win32", {"LOCALAPPDATA": r"C:\Users\Ana\AppData\Local"}, r"C:\Users\Ana"
    )
    assert result == os.path.join(r"C:\Users\Ana\AppData\Local", "CVLaTeX")
    # Without LOCALAPPDATA it falls back to the user home (legacy behavior).
    result = prefs._app_dir_for("win32", {}, r"C:\Users\Ana")
    assert result == os.path.join(r"C:\Users\Ana", "CVLaTeX")


def test_app_dir_for_macos_uses_application_support():
    result = prefs._app_dir_for("darwin", {}, "/Users/ana")
    assert result == os.path.join(
        "/Users/ana", "Library", "Application Support", "CVLaTeX"
    )


def test_app_dir_for_linux_uses_xdg_data_home():
    assert prefs._app_dir_for("linux", {}, "/home/ana") == os.path.join(
        "/home/ana", ".local", "share", "CVLaTeX"
    )
    assert prefs._app_dir_for(
        "linux", {"XDG_DATA_HOME": "/home/ana/.data"}, "/home/ana"
    ) == os.path.join("/home/ana/.data", "CVLaTeX")


def test_module_attributes_keep_the_expected_layout():
    for name in ("APP_DIR", "CACHE_DIR", "BUILD_DIR", "TINYTEX_DIR", "PREFS_FILE"):
        value = getattr(prefs, name)
        assert isinstance(value, str) and value
    assert prefs.CACHE_DIR == os.path.join(prefs.APP_DIR, "cache")
    assert prefs.BUILD_DIR == os.path.join(prefs.CACHE_DIR, "build")
    assert prefs.TINYTEX_DIR == os.path.join(prefs.APP_DIR, "tinytex")
    assert prefs.PREFS_FILE == os.path.join(prefs.APP_DIR, "prefs.json")
    # The live APP_DIR follows the running platform.
    assert prefs.APP_DIR == prefs._app_dir_for(sys.platform)
