# -*- coding: utf-8 -*-
"""Mensajes exactos de main.Api.import_tex para .tex ajenos, antiguos o danados.

Copia literal de los textos congelados de messages.py; si cambian alli, este
test debe fallar. Cada test fija ui_language=es sobre prefs aisladas: los
textos congelados son los espanoles, no el idioma por defecto.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_gen  # noqa: E402
import main  # noqa: E402
import prefs  # noqa: E402
import tex_datos  # noqa: E402

MSG_PLANTILLA_AJENA = (
    "Esta plantilla no tiene buena compatibilidad con la aplicación. "
    "Se recomienda buscar otra plantilla."
)
MSG_SIN_BLOQUE = (
    "Este .tex fue generado por una versión anterior de CVLaTeX sin datos incrustados: "
    "no se puede reimportar. Vuelve a generarlo con la versión actual."
)
MSG_BLOQUE_DANADO = (
    "El bloque de datos de CVLaTeX está dañado y no se puede reimportar."
)


@pytest.fixture()
def prefs_tmp(tmp_path, monkeypatch):
    app = tmp_path / "app"
    monkeypatch.setattr(prefs, "APP_DIR", str(app))
    monkeypatch.setattr(prefs, "CACHE_DIR", str(app / "cache"))
    monkeypatch.setattr(prefs, "BUILD_DIR", str(app / "cache" / "build"))
    monkeypatch.setattr(prefs, "PREFS_FILE", str(app / "prefs.json"))
    monkeypatch.setattr(prefs, "_CACHE", None)
    return tmp_path


def _api_que_abre(monkeypatch, ruta):
    api = main.Api(None)
    monkeypatch.setattr(api, "choose_file", lambda *a, **k: str(ruta))
    return api


def test_import_tex_ajeno(prefs_tmp, monkeypatch):
    prefs.set("ui_language", "es")
    ruta = prefs_tmp / "ajeno.tex"
    ruta.write_text(
        "\\documentclass{article}\n\\begin{document}\nHola mundo\n\\end{document}\n",
        encoding="utf-8",
    )
    api = _api_que_abre(monkeypatch, ruta)
    resultado = api.import_tex()
    assert resultado == {"ok": False, "errores": [MSG_PLANTILLA_AJENA]}


def test_import_tex_antiguo_sin_bloque(prefs_tmp, monkeypatch):
    prefs.set("ui_language", "es")
    ruta = prefs_tmp / "antiguo.tex"
    ruta.write_text(
        "% Documento generado por CVLaTeX (version antigua)\n"
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Sin bloque de datos\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    api = _api_que_abre(monkeypatch, ruta)
    resultado = api.import_tex()
    assert resultado == {"ok": False, "errores": [MSG_SIN_BLOQUE]}


def test_import_tex_bloque_danado(prefs_tmp, monkeypatch):
    prefs.set("ui_language", "es")
    ruta = prefs_tmp / "danado.tex"
    ruta.write_text(
        "% CVLaTeX-DATA-BEGIN\n"
        "% esto-no-es-base64-valido!!!\n"
        "% CVLaTeX-DATA-END\n"
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Documento con bloque corrupto\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    api = _api_que_abre(monkeypatch, ruta)
    resultado = api.import_tex()
    assert resultado == {"ok": False, "errores": [MSG_BLOQUE_DANADO]}


def test_import_tex_valido(prefs_tmp, monkeypatch):
    datos = latex_gen.empty_data()
    datos["template"] = "modern"
    datos["name"] = "Ana García"
    datos["email"] = "ana@example.com"
    datos["work"] = [{"position": "Dev", "company": "Acme", "start": "2020", "end": "2024"}]

    tex = latex_gen.build_tex(datos, prefs.load())
    ruta = prefs_tmp / "valido.tex"
    ruta.write_text(tex, encoding="utf-8")

    api = _api_que_abre(monkeypatch, ruta)
    resultado = api.import_tex()
    assert resultado["ok"] is True
    assert resultado["ruta"] == str(ruta)
    assert resultado["datos"] == datos


def test_import_tex_migra_los_campos_fijos_antiguos(prefs_tmp, monkeypatch):
    """Un .tex con github/linkedin/website/nacimiento/nacionalidad antiguos."""
    antiguos = {
        "cv_language": "es",
        "nombre": "Ana",
        "github": "github.com/ana",
        "website": "ana.dev",
        "birth_date": "12/05/1994",
        "nationality": "Española",
    }
    tex = tex_datos.embed(
        "\\documentclass{article}\n\\begin{document}\nX\n\\end{document}\n",
        antiguos,
    )
    ruta = prefs_tmp / "antiguo_datos.tex"
    ruta.write_text(tex, encoding="utf-8")

    resultado = _api_que_abre(monkeypatch, ruta).import_tex()
    assert resultado["ok"] is True
    datos = resultado["datos"]
    assert datos["name"] == "Ana"
    assert datos["socials"] == [
        {"network": "github", "label": "", "value": "github.com/ana"},
        {"network": "website", "label": "", "value": "ana.dev"},
    ]
    assert datos["extra_fields"][:2] == [
        {"label": "Nacimiento", "value": "12/05/1994"},
        {"label": "Nacionalidad", "value": "Española"},
    ]
    for clave in ("github", "website", "birth_date", "nationality"):
        assert clave not in datos, clave
