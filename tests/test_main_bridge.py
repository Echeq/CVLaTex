# -*- coding: utf-8 -*-
"""Smoke checks for the frozen main.Api bridge.

Covers the .cvjson v3 envelope with its `<fichero>.v2.bak` pre-migration copy,
the autosave envelope (v3 + legacy plain dict), the startup cache purge, the
messages wiring (es/en/zh/ru), the close guard, TinyTeX cancellation, the autosave
base64 cache and the skip-recompile cache. No GUI, no LaTeX, no pywebview
window: prefs and CACHE_DIR are isolated with a tmp fixture.
"""

import base64
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_engine  # noqa: E402
import latex_gen  # noqa: E402
import main  # noqa: E402
import messages  # noqa: E402
import prefs  # noqa: E402


@pytest.fixture()
def prefs_tmp(tmp_path, monkeypatch):
    """Aisla prefs (dirs y cache) del equipo del usuario."""
    app = tmp_path / "app"
    monkeypatch.setattr(prefs, "APP_DIR", str(app))
    monkeypatch.setattr(prefs, "CACHE_DIR", str(app / "cache"))
    monkeypatch.setattr(prefs, "BUILD_DIR", str(app / "cache" / "build"))
    monkeypatch.setattr(prefs, "PREFS_FILE", str(app / "prefs.json"))
    monkeypatch.setattr(prefs, "_CACHE", None)
    return tmp_path


def _api_opening(monkeypatch, path):
    api = main.Api(None)
    monkeypatch.setattr(api, "choose_file", lambda *a, **k: str(path))
    return api


def _wait_until(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while not predicate() and time.time() < deadline:
        time.sleep(0.01)
    assert predicate()


# ---------------------------------------------------------------------------
# .cvjson v3 envelope, v2/v1 reading and .v2.bak copy
# ---------------------------------------------------------------------------

def test_open_cv_v2_backs_up_once_and_returns_english_data(prefs_tmp, monkeypatch):
    tmp = prefs_tmp
    photo = tmp / "foto-v2.png"
    photo.write_bytes(b"foto-v2")
    cvjson = tmp / "antiguo.cvjson"
    cvjson.write_text(
        json.dumps(
            {
                "version": 2,
                "datos": {
                    "nombre": "Ana",
                    "foto": str(photo),
                    "experiencia": [{"tipo": "Trabajo", "puesto": "Dev"}],
                },
                "medios": {
                    str(photo): {
                        "nombre": "foto-v2.png",
                        "b64": base64.b64encode(b"foto-v2").decode("ascii"),
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    original = cvjson.read_text(encoding="utf-8")

    api = _api_opening(monkeypatch, cvjson)
    result = api.open_cv()
    assert result["ok"] is True
    data = result["datos"]
    # English keys after migration; media materialized in CACHE_DIR.
    assert data["name"] == "Ana"
    assert "nombre" not in data and "foto" not in data
    assert data["work"] == [{"tipo": "Trabajo", "position": "Dev"}]
    assert data["photo"] != str(photo)
    assert os.path.isfile(data["photo"])
    assert os.path.basename(data["photo"]).startswith("cv_")

    backup = tmp / "antiguo.cvjson.v2.bak"
    assert backup.read_text(encoding="utf-8") == original

    # A second legacy open never clobbers the existing backup.
    cvjson.write_text(
        json.dumps({"version": 2, "datos": {"nombre": "Otro"}, "medios": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    second = _api_opening(monkeypatch, cvjson).open_cv()
    assert second["datos"]["name"] == "Otro"
    assert backup.read_text(encoding="utf-8") == original


def test_export_cv_writes_v3_envelope_with_data_and_media(prefs_tmp, monkeypatch):
    tmp = prefs_tmp
    photo = tmp / "foto.png"
    photo.write_bytes(b"foto-v3")
    data = latex_gen.empty_data()
    data["name"] = "Ana"
    data["photo"] = str(photo)

    out = tmp / "mi_cv.cvjson"
    api = _api_opening(monkeypatch, out)
    assert api.export_cv(data) == {"ok": True, "ruta": str(out)}

    content = json.loads(out.read_text(encoding="utf-8"))
    assert content["version"] == 3
    assert "datos" not in content and "medios" not in content
    assert content["data"]["name"] == "Ana"
    assert content["media"][str(photo)]["name"] == "foto.png"
    assert content["media"][str(photo)]["b64"] == base64.b64encode(b"foto-v3").decode("ascii")

    # v3 round trip: media materializes and no legacy backup is created.
    opened = _api_opening(monkeypatch, out).open_cv()
    assert opened["ok"] is True
    assert opened["datos"]["photo"] != str(photo)
    assert os.path.isfile(opened["datos"]["photo"])
    assert not (tmp / "mi_cv.cvjson.v2.bak").exists()


def test_export_cv_with_path_skips_the_dialog_and_writes_v3(prefs_tmp, monkeypatch):
    """export_cv(data, path) writes directly without opening choose_file."""
    tmp = prefs_tmp
    data = latex_gen.empty_data()
    data["name"] = "Ana"
    out = tmp / "directo.cvjson"
    api = main.Api(None)

    def fail_choose_file(*args, **kwargs):
        raise AssertionError("choose_file must not be called when path is given")

    monkeypatch.setattr(api, "choose_file", fail_choose_file)
    assert api.export_cv(data, str(out)) == {"ok": True, "ruta": str(out)}

    content = json.loads(out.read_text(encoding="utf-8"))
    assert content["version"] == 3
    assert "data" in content and "media" in content
    assert content["data"]["name"] == "Ana"
    assert content["media"] == {}


def test_open_cv_migrates_the_legacy_contacts(prefs_tmp, monkeypatch):
    """An old cvjson with fixed contact fields opens without losing data."""
    tmp = prefs_tmp
    cvjson = tmp / "contactos.cvjson"
    cvjson.write_text(
        json.dumps(
            {
                "version": 3,
                "data": {
                    "cv_language": "es",
                    "github": "github.com/ana",
                    "linkedin": "linkedin.com/in/ana",
                    "website": "ana.dev",
                    "birth_date": "12/05/1994",
                    "nationality": "Española",
                },
                "media": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = _api_opening(monkeypatch, cvjson).open_cv()
    assert result["ok"] is True
    data = result["datos"]
    assert data["socials"] == [
        {"network": "github", "label": "", "value": "github.com/ana"},
        {"network": "linkedin", "label": "", "value": "linkedin.com/in/ana"},
        {"network": "website", "label": "", "value": "ana.dev"},
    ]
    assert data["extra_fields"][:2] == [
        {"label": "Nacimiento", "value": "12/05/1994"},
        {"label": "Nacionalidad", "value": "Española"},
    ]
    for key in ("github", "linkedin", "website", "birth_date", "nationality"):
        assert key not in data, key


# ---------------------------------------------------------------------------
# Autosave envelope (v3 + legacy plain dict)
# ---------------------------------------------------------------------------

def test_autosave_round_trip_v3_and_legacy_plain_dict(prefs_tmp):
    tmp = prefs_tmp
    photo = tmp / "foto.png"
    photo.write_bytes(b"foto-autosave")
    data = latex_gen.empty_data()
    data["name"] = "Ana"
    data["photo"] = str(photo)

    api = main.Api(None)
    assert api.autosave(data) == {"ok": True}

    autosave_path = os.path.join(prefs.APP_DIR, "autosave.cvjson")
    with open(autosave_path, "r", encoding="utf-8") as f:
        envelope = json.load(f)
    assert envelope["version"] == 3
    assert envelope["data"]["name"] == "Ana"
    assert str(photo) in envelope["media"]

    read = api.autosave_read()
    assert isinstance(read, dict)
    assert not ({"version", "data", "media", "datos", "medios"} & set(read))
    assert read["name"] == "Ana"
    assert read["photo"] != str(photo) and os.path.isfile(read["photo"])

    # Legacy plain-dict autosave (no envelope) is still accepted.
    with open(autosave_path, "w", encoding="utf-8") as f:
        json.dump(
            {"nombre": "Antiguo", "experiencia": [{"tipo": "Trabajo", "puesto": "Dev"}]},
            f,
            ensure_ascii=False,
        )
    legacy = api.autosave_read()
    assert legacy["name"] == "Antiguo"
    assert legacy["work"] == [{"tipo": "Trabajo", "position": "Dev"}]


def test_autosave_read_migrates_the_legacy_contacts(prefs_tmp):
    os.makedirs(prefs.APP_DIR, exist_ok=True)
    with open(os.path.join(prefs.APP_DIR, "autosave.cvjson"), "w", encoding="utf-8") as f:
        json.dump(
            {"github": "github.com/a", "birth_date": "1990", "nationality": "Ch"},
            f,
            ensure_ascii=False,
        )

    data = main.Api(None).autosave_read()
    assert data["socials"] == [
        {"network": "github", "label": "", "value": "github.com/a"},
    ]
    assert data["extra_fields"][:2] == [
        {"label": "出生年月", "value": "1990"},
        {"label": "国籍", "value": "Ch"},
    ]
    for key in ("github", "birth_date", "nationality"):
        assert key not in data, key


# ---------------------------------------------------------------------------
# Startup cache purge
# ---------------------------------------------------------------------------

def test_purge_cache_clears_build_out_and_old_media(prefs_tmp):
    cache = prefs.CACHE_DIR
    out_dir = os.path.join(cache, "out")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(prefs.BUILD_DIR, exist_ok=True)

    stale = os.path.join(cache, "foto_vieja.png")
    fresh = os.path.join(cache, "foto_nueva.jpg")
    other = os.path.join(cache, "notas.txt")
    for path, content in ((stale, b"vieja"), (fresh, b"nueva"), (other, b"texto")):
        with open(path, "wb") as f:
            f.write(content)
    old = time.time() - (main.CACHE_MAX_AGE_DAYS + 1) * 24 * 60 * 60
    os.utime(stale, (old, old))
    os.utime(other, (old, old))

    with open(os.path.join(prefs.BUILD_DIR, "main.tex"), "w", encoding="utf-8") as f:
        f.write("x")
    with open(os.path.join(out_dir, "result_1.pdf"), "wb") as f:
        f.write(b"%PDF")

    main.purge_cache()

    assert not os.path.exists(stale)
    assert os.path.exists(fresh)
    assert os.path.exists(other)  # only cache media is age-purged
    assert os.listdir(prefs.BUILD_DIR) == []
    assert os.listdir(out_dir) == []


# ---------------------------------------------------------------------------
# Messages wiring (ui_language es / en / zh / ru)
# ---------------------------------------------------------------------------

def test_import_rejection_uses_ui_language(prefs_tmp, monkeypatch):
    tmp = prefs_tmp
    tex = tmp / "ajeno.tex"
    tex.write_text(
        "\\documentclass{article}\n\\begin{document}\nHola mundo\n\\end{document}\n",
        encoding="utf-8",
    )

    # With isolated prefs the default UI language is English.
    assert prefs.load()["ui_language"] == "en"
    default = _api_opening(monkeypatch, tex).import_tex()
    assert default == {"ok": False, "errores": [messages.t("import_incompatible", "en")]}
    assert default["errores"] == [
        "This template is not fully compatible with the application. "
        "Please look for another template."
    ]

    prefs.set("ui_language", "es")
    result = _api_opening(monkeypatch, tex).import_tex()
    assert result == {"ok": False, "errores": [messages.t("import_incompatible", "es")]}
    assert result["errores"] == [
        "Esta plantilla no tiene buena compatibilidad con la aplicación. "
        "Se recomienda buscar otra plantilla."
    ]

    prefs.set("ui_language", "zh")
    result = _api_opening(monkeypatch, tex).import_tex()
    assert result == {"ok": False, "errores": [messages.t("import_incompatible", "zh")]}
    assert result["errores"] == ["此模板与应用不完全兼容。建议另选模板。"]

    prefs.set("ui_language", "ru")
    result = _api_opening(monkeypatch, tex).import_tex()
    assert result == {"ok": False, "errores": [messages.t("import_incompatible", "ru")]}
    assert result["errores"] == [
        "Этот шаблон не полностью совместим с приложением. "
        "Рекомендуется выбрать другой шаблон."
    ]


def test_messages_tables_cover_every_key_and_fall_back_to_english(prefs_tmp):
    keys = set(messages.MESSAGES["es"])
    assert messages.DEFAULT_LANGUAGE == "en"
    assert keys and keys == set(messages.MESSAGES["en"])
    assert keys == set(messages.MESSAGES["zh"])
    assert keys == set(messages.MESSAGES["ru"])

    # zh / ru translate a representative key instead of echoing English.
    assert messages.t("install_done", "zh") == "TinyTeX 安装完成。"
    assert messages.t("install_done", "ru") == "TinyTeX успешно установлен."

    # Unknown language -> English (default); unknown key -> the key itself.
    assert messages.t("install_done", "fr") == messages.t("install_done", "en")
    assert messages.t("no_such_key", "ru") == "no_such_key"


def test_window_title_languages(prefs_tmp):
    assert main.window_title("es") == "CVLaTeX — Editor de CV"
    assert main.window_title("en") == "CVLaTeX — CV Editor"
    assert main.window_title("zh") == "CVLaTeX — 简历编辑器"
    assert main.window_title("ru") == "CVLaTeX — Редактор резюме"
    # An unknown or missing language falls back to English (the default).
    assert main.window_title(None) == "CVLaTeX — CV Editor"
    assert main.window_title("fr") == "CVLaTeX — CV Editor"


def test_prefs_ui_language_defaults_to_english(prefs_tmp, monkeypatch):
    assert prefs.load()["ui_language"] == "en"

    # A legacy prefs file without ui_language gets the English default and
    # still migrates its old keys.
    with open(prefs.PREFS_FILE, "w", encoding="utf-8") as f:
        json.dump({"papel": "letter"}, f)
    monkeypatch.setattr(prefs, "_CACHE", None)
    migrated = prefs.load()
    assert migrated["ui_language"] == "en"
    assert migrated["paper"] == "letter"

    # An explicit saved language is preserved.
    prefs.set("ui_language", "es")
    assert prefs.load()["ui_language"] == "es"


def test_install_done_uses_ui_language(prefs_tmp, monkeypatch):
    prefs.set("ui_language", "en")
    monkeypatch.setattr(
        latex_engine,
        "install_tinytex",
        lambda progress, cancel_event=None: r"C:\fake\pdflatex.exe",
    )
    api = main.Api(None)
    pushes = []
    monkeypatch.setattr(api, "_push", lambda name, data: pushes.append((name, data)))

    assert api.install_latex() == "ok"
    _wait_until(lambda: bool(pushes))
    assert pushes == [
        (
            "__onInstallDone",
            {
                "ok": True,
                "msg": messages.t("install_done", "en"),
                "path": r"C:\fake\pdflatex.exe",
            },
        )
    ]
    assert pushes[0][1]["msg"] == "TinyTeX installed successfully."


def test_cancel_install_sets_the_event(prefs_tmp, monkeypatch):
    seen = {}

    def fake_install(progress, cancel_event=None):
        seen["event"] = cancel_event
        assert cancel_event is not None
        assert cancel_event.wait(5)  # released by Api.cancel_install
        raise latex_engine.LatexError(messages.t("install_cancelled"))

    monkeypatch.setattr(latex_engine, "install_tinytex", fake_install)
    api = main.Api(None)
    pushes = []
    monkeypatch.setattr(api, "_push", lambda name, data: pushes.append((name, data)))

    api.install_latex()
    _wait_until(lambda: "event" in seen)
    assert seen["event"] is not None

    assert api.cancel_install() == {"ok": True}
    assert seen["event"].is_set()
    _wait_until(lambda: bool(pushes))
    assert pushes[0][0] == "__onInstallDone"
    assert pushes[0][1]["ok"] is False
    assert pushes[0][1]["msg"] == messages.t("install_cancelled")

    # Once the install finished, cancel_install is a no-op.
    _wait_until(lambda: api._cancel_event is None)
    assert api.cancel_install() == {"ok": False, "cancelado": True}


# ---------------------------------------------------------------------------
# Close guard
# ---------------------------------------------------------------------------

class _FakeWindow:
    def __init__(self):
        self.destroyed = False

    def destroy(self):
        self.destroyed = True

    def evaluate_js(self, script):
        pass


def test_close_guard_blocks_once_and_quit_force_destroys(prefs_tmp, monkeypatch):
    win = _FakeWindow()
    api = main.Api(win)
    pushes = []
    monkeypatch.setattr(api, "_push", lambda name, data: pushes.append((name, data)))

    # A clean window closes normally.
    assert api._on_closing() is True

    assert api.set_dirty(True) == {"ok": True}
    assert api._on_closing() is False
    # The push is dispatched asynchronously (evaluate_js must never run
    # synchronously inside FormClosing): poll until the daemon thread runs.
    _wait_until(lambda: bool(pushes))
    assert pushes == [("__onCloseRequest", {})]

    # quit_app forces the close and destroys the window.
    assert api.quit_app() == {"ok": True}
    assert win.destroyed is True
    assert api._on_closing() is True

    api.set_dirty(False)
    assert api._on_closing() is True


# ---------------------------------------------------------------------------
# Skip recompile and autosave media cache
# ---------------------------------------------------------------------------

def test_identical_tex_skips_the_engine(prefs_tmp, monkeypatch):
    calls = []

    def fake_compile(tex, photo=None, extras=None):
        calls.append(tex)
        out_dir = os.path.join(prefs.CACHE_DIR, "out")
        os.makedirs(out_dir, exist_ok=True)
        pdf = os.path.join(out_dir, "result_%d.pdf" % len(calls))
        with open(pdf, "wb") as f:
            f.write(b"%PDF")
        return {"ok": True, "pdf": pdf, "errores": []}

    monkeypatch.setattr(latex_engine, "compile", fake_compile)
    api = main.Api(None)
    pushes = []
    monkeypatch.setattr(api, "_push", lambda name, data: pushes.append((name, data)))
    data = latex_gen.empty_data()

    api._compile_thread(data, "id-1")
    api._compile_thread(data, "id-2")
    assert len(calls) == 1
    assert pushes[0][1]["id"] == "id-1" and pushes[1][1]["id"] == "id-2"
    assert pushes[0][1]["pdf"] == pushes[1][1]["pdf"]
    assert pushes[1][1]["tex"] == pushes[0][1]["tex"]

    # With the cached pdf gone the engine runs again.
    os.remove(pushes[0][1]["pdf"])
    api._compile_thread(data, "id-3")
    assert len(calls) == 2


def test_collect_media_cache_hits_by_path_mtime_size(prefs_tmp):
    tmp = prefs_tmp
    photo = tmp / "foto.png"
    photo.write_bytes(b"abc")
    data = latex_gen.empty_data()
    data["photo"] = str(photo)

    cache = {}
    first = main.collect_media(data, cache)
    assert len(cache) == 1
    assert first[str(photo)]["b64"] == base64.b64encode(b"abc").decode("ascii")

    # Unchanged file: the cached entry is reused instead of re-encoded.
    cached = next(iter(cache.values()))
    second = main.collect_media(data, cache)
    assert second[str(photo)] is cached

    # Changed size/mtime -> new key and a fresh entry.
    photo.write_bytes(b"abcd")
    os.utime(photo, (time.time() + 10, time.time() + 10))
    third = main.collect_media(data, cache)
    assert third[str(photo)]["b64"] == base64.b64encode(b"abcd").decode("ascii")
    assert len(cache) == 2
