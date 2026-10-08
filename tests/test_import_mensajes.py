# -*- coding: utf-8 -*-
"""Mensajes exactos de main.Api.importar_tex para .tex ajenos, antiguos o danados.

Copia literal de los textos de main.py; si cambian alli, este test debe fallar.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_gen  # noqa: E402
import main  # noqa: E402
import prefs  # noqa: E402

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
    monkeypatch.setattr(api, "elegir_archivo", lambda *a, **k: str(ruta))
    return api


def test_importar_tex_ajeno(tmp_path, monkeypatch):
    ruta = tmp_path / "ajeno.tex"
    ruta.write_text(
        "\\documentclass{article}\n\\begin{document}\nHola mundo\n\\end{document}\n",
        encoding="utf-8",
    )
    api = _api_que_abre(monkeypatch, ruta)
    resultado = api.importar_tex()
    assert resultado == {"ok": False, "errores": [MSG_PLANTILLA_AJENA]}


def test_importar_tex_antiguo_sin_bloque(tmp_path, monkeypatch):
    ruta = tmp_path / "antiguo.tex"
    ruta.write_text(
        "% Documento generado por CVLaTeX (version antigua)\n"
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Sin bloque de datos\n"
        "\\end{document}\n",
        encoding="utf-8",
    )
    api = _api_que_abre(monkeypatch, ruta)
    resultado = api.importar_tex()
    assert resultado == {"ok": False, "errores": [MSG_SIN_BLOQUE]}


def test_importar_tex_bloque_danado(tmp_path, monkeypatch):
    ruta = tmp_path / "danado.tex"
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
    resultado = api.importar_tex()
    assert resultado == {"ok": False, "errores": [MSG_BLOQUE_DANADO]}


def test_importar_tex_valido(prefs_tmp, monkeypatch):
    datos = latex_gen.datos_vacios()
    datos["plantilla"] = "moderno"
    datos["nombre"] = "Ana García"
    datos["email"] = "ana@example.com"
    datos["trabajo"] = [{"puesto": "Dev", "empresa": "Acme", "desde": "2020", "hasta": "2024"}]

    tex = latex_gen.build_tex(datos, prefs.load())
    ruta = prefs_tmp / "valido.tex"
    ruta.write_text(tex, encoding="utf-8")

    api = _api_que_abre(monkeypatch, ruta)
    resultado = api.importar_tex()
    assert resultado["ok"] is True
    assert resultado["ruta"] == str(ruta)
    assert resultado["datos"] == datos
