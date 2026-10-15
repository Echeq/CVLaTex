# -*- coding: utf-8 -*-
"""Espaciado de cabecera: titulo LANG separado del nombre en cada plantilla.

Para cada plantilla de ``latex_gen.TEMPLATES`` x (es, zh) comprueba con
``build_tex`` + ``datos_vacios`` que el titulo y el nombre no quedan pegados:
en modern el titulo cierra su propio parrafo (\\par) antes del nombre y en
todas las plantillas hay un ``\\vspace`` entre ambos. Las plantillas sidebar y
sidebar-right son la excepcion: su cabecera no lleva el titulo LANG (nombre +
profesion) y los contactos viven en la barra lateral (ver test_sidebar.py).
Ademas valida que
el documento no conserva marcadores y que el round-trip de datos es exacto.
Las compilaciones reales usan el mismo patron skipif de test_roundtrip_tex.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_engine  # noqa: E402
import latex_gen  # noqa: E402
import prefs  # noqa: E402
import tex_datos  # noqa: E402

TEMPLATES = latex_gen.TEMPLATES
IDIOMAS = ("es", "zh")

MOTOR_PDF = latex_engine.find_pdflatex()
MOTOR_CJK = latex_engine.find_xelatex()

# Nombres cortos y sin caracteres que esc() pueda partir con \allowbreak.
NOMBRES = {"es": "Ana García", "zh": "张伟"}


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


def datos_cabecera(idioma, plantilla):
    """CV minimo: solo cabecera (nombre) en el idioma y plantilla dados."""
    d = latex_gen.empty_data()
    d["cv_language"] = idioma
    d["template"] = plantilla
    d["name"] = NOMBRES[idioma]
    return d


@pytest.mark.parametrize("plantilla", TEMPLATES)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_cabecera_espaciada(plantilla, idioma, prefs_tmp):
    datos = datos_cabecera(idioma, plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())

    titulo = latex_gen.LANG[idioma]["title"]
    nombre = latex_gen.esc(datos["name"])
    assert nombre in tex

    if plantilla in ("sidebar", "sidebar-right"):
        # Header = name (large, accent) + profession + accent rule; the LANG
        # title is not used and the contacts stay in the side bar.
        assert titulo not in tex
        assert "{\\Huge\\bfseries\\color{accent} " + nombre + "}" in tex
        assert "{{" not in tex
        assert tex_datos.extract(tex) == datos
        return

    assert titulo in tex

    i_titulo = tex.index(titulo)
    i_nombre = tex.index(nombre)
    assert i_titulo != i_nombre
    inicio, fin = sorted((i_titulo, i_nombre))
    assert "\\vspace{" in tex[inicio:fin], "sin separacion vertical titulo-nombre"

    if plantilla == "modern":
        # El titulo cierra su parrafo antes de que empiece el nombre.
        assert i_titulo < i_nombre
        assert "\\par" in tex[i_titulo:i_nombre]

    assert "{{" not in tex
    assert tex_datos.extract(tex) == datos


@pytest.mark.parametrize("plantilla", TEMPLATES)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_cabecera_socials_dinamicos(plantilla, idioma, prefs_tmp):
    """Los socials se renderizan en la cabecera con nombres y idioma."""
    datos = datos_cabecera(idioma, plantilla)
    datos["socials"] = [
        {"network": "github", "label": "Ignorado", "value": "github.com/ana"},
        {"network": "website", "label": "", "value": "ana.dev"},
        {"network": "other", "label": "", "value": "otro.dev"},
        {"network": "other", "label": "Mastodon", "value": "mastodon/@ana"},
        {"network": "linkedin", "label": "", "value": "   "},
    ]
    tex = latex_gen.build_tex(datos, prefs.load())

    assert "\\textbf{GitHub:} \\texttt{github.com/ana}" in tex
    assert "\\textbf{%s:} \\texttt{ana.dev}" % latex_gen.LANG[idioma]["website"] in tex
    assert "\\textbf{%s:} \\texttt{otro.dev}" % latex_gen.LANG[idioma]["link"] in tex
    assert "\\textbf{Mastodon:} \\texttt{mastodon/@ana}" in tex
    assert "Ignorado" not in tex
    assert tex_datos.extract(tex) == datos


@pytest.mark.skipif(MOTOR_PDF is None, reason="Sin motor LaTeX (pdflatex) instalado")
@pytest.mark.parametrize("plantilla", TEMPLATES)
def test_compila_pdf_cabeceras_es(plantilla, prefs_tmp):
    datos = datos_cabecera("es", plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])


@pytest.mark.skipif(
    MOTOR_PDF is None or MOTOR_CJK is None,
    reason="Sin motores LaTeX (pdflatex/xelatex) para compilar texto CJK",
)
@pytest.mark.parametrize("plantilla", TEMPLATES)
def test_compila_pdf_cabeceras_zh(plantilla, prefs_tmp):
    datos = datos_cabecera("zh", plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])
