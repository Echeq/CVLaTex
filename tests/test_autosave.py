# -*- coding: utf-8 -*-
"""The restore point on disk: atomic write, .bak fallback and clearing.

`Api.autosave()` writes `autosave.cvjson` through a fsynced `.tmp` +
`os.replace` and keeps the previous good file as `autosave.cvjson.bak`.
`autosave_read()` falls back to that `.bak` when the primary is missing or
corrupt, and `autosave_clear()` removes both. No GUI, no LaTeX: prefs and
cache are isolated with a tmp fixture.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_gen  # noqa: E402
import main  # noqa: E402
import prefs  # noqa: E402


@pytest.fixture()
def prefs_tmp(tmp_path, monkeypatch):
    """Isolate prefs (dirs and cache) from the user's machine."""
    app = tmp_path / "app"
    monkeypatch.setattr(prefs, "APP_DIR", str(app))
    monkeypatch.setattr(prefs, "CACHE_DIR", str(app / "cache"))
    monkeypatch.setattr(prefs, "BUILD_DIR", str(app / "cache" / "build"))
    monkeypatch.setattr(prefs, "PREFS_FILE", str(app / "prefs.json"))
    monkeypatch.setattr(prefs, "_CACHE", None)
    return tmp_path


def _data(name):
    data = latex_gen.empty_data()
    data["name"] = name
    return data


def _paths():
    app = prefs.APP_DIR
    return (
        os.path.join(app, main.AUTOSAVE_FILE),
        os.path.join(app, main.AUTOSAVE_BAK_FILE),
        os.path.join(app, main.AUTOSAVE_TMP_FILE),
    )


def _envelope_name(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["data"]["name"]


def test_autosave_file_names_are_pinned():
    assert main.AUTOSAVE_FILE == "autosave.cvjson"
    assert main.AUTOSAVE_BAK_FILE == "autosave.cvjson.bak"
    assert main.AUTOSAVE_TMP_FILE == "autosave.cvjson.tmp"


def test_autosave_writes_atomically_and_keeps_the_previous_copy(prefs_tmp):
    api = main.Api(None)
    primary, backup, tmp = _paths()

    assert api.autosave(_data("Primero")) == {"ok": True}
    assert os.path.isfile(primary)
    assert not os.path.exists(tmp)
    assert not os.path.exists(backup)

    assert api.autosave(_data("Segundo")) == {"ok": True}
    # The new data is in place, the previous good file became the fallback and
    # no temporary file survives a successful write.
    assert _envelope_name(primary) == "Segundo"
    assert _envelope_name(backup) == "Primero"
    assert not os.path.exists(tmp)


def test_autosave_read_falls_back_to_the_bak_when_primary_is_corrupt(prefs_tmp):
    api = main.Api(None)
    primary, backup, _ = _paths()
    api.autosave(_data("Primero"))
    api.autosave(_data("Segundo"))
    assert os.path.isfile(backup)

    with open(primary, "w", encoding="utf-8") as f:
        f.write("{not valid json")
    data = api.autosave_read()
    assert isinstance(data, dict) and data["name"] == "Primero"

    # A missing primary falls back to the same .bak.
    os.remove(primary)
    data = api.autosave_read()
    assert isinstance(data, dict) and data["name"] == "Primero"


def test_autosave_read_returns_none_when_both_copies_are_unusable(prefs_tmp):
    primary, backup, _ = _paths()
    os.makedirs(prefs.APP_DIR, exist_ok=True)
    for path in (primary, backup):
        with open(path, "w", encoding="utf-8") as f:
            f.write("[]")
    assert main.Api(None).autosave_read() is None


def test_autosave_clear_removes_primary_bak_and_stale_tmp(prefs_tmp):
    api = main.Api(None)
    api.autosave(_data("Primero"))
    api.autosave(_data("Segundo"))
    primary, backup, tmp = _paths()
    assert os.path.isfile(primary) and os.path.isfile(backup)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("stale")

    assert api.autosave_clear() == {"ok": True}
    for path in (primary, backup, tmp):
        assert not os.path.exists(path), path
    assert api.autosave_read() is None


def test_failed_autosave_keeps_the_previous_good_file(prefs_tmp, monkeypatch):
    api = main.Api(None)
    primary, _, tmp = _paths()
    api.autosave(_data("Primero"))

    def boom(fd):
        raise OSError("disk full")

    monkeypatch.setattr(main.os, "fsync", boom)
    result = api.autosave(_data("Segundo"))

    assert result["ok"] is False
    assert result["errores"]
    # The old restore point survives and no half-written tmp file is left.
    assert _envelope_name(primary) == "Primero"
    assert not os.path.exists(tmp)
