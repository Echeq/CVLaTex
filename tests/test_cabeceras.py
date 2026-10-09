# -*- coding: utf-8 -*-
"""Espaciado de cabecera: titulo LANG separado del nombre en las 5 plantillas.

Para cada plantilla de ``latex_gen.PLANTILLAS`` x (es, zh) comprueba con
``build_tex`` + ``datos_vacios`` que el titulo y el nombre no quedan pegados:
en moderno el titulo cierra su propio parrafo (\\par) antes del nombre y en
todas las plantillas hay un ``\\vspace`` entre ambos. Ademas valida que el
documento no conserva marcadores y que el round-trip de datos es exacto.
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

PLANTILLAS = latex_gen.PLANTILLAS
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
    d = latex_gen.datos_vacios()
    d["idioma_cv"] = idioma
    d["plantilla"] = plantilla
    d["nombre"] = NOMBRES[idioma]
    return d


@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_cabecera_espaciada(plantilla, idioma, prefs_tmp):
    datos = datos_cabecera(idioma, plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())

    titulo = latex_gen.LANG[idioma]["titulo"]
    nombre = latex_gen.esc(datos["nombre"])
    assert titulo in tex
    assert nombre in tex

    i_titulo = tex.index(titulo)
    i_nombre = tex.index(nombre)
    assert i_titulo != i_nombre
    inicio, fin = sorted((i_titulo, i_nombre))
    assert "\\vspace{" in tex[inicio:fin], "sin separacion vertical titulo-nombre"

    if plantilla == "moderno":
        # El titulo cierra su parrafo antes de que empiece el nombre.
        assert i_titulo < i_nombre
        assert "\\par" in tex[i_titulo:i_nombre]

    assert "{{" not in tex
    assert tex_datos.extraer(tex) == datos


@pytest.mark.skipif(MOTOR_PDF is None, reason="Sin motor LaTeX (pdflatex) instalado")
@pytest.mark.parametrize("plantilla", PLANTILLAS)
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
@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_compila_pdf_cabeceras_zh(plantilla, prefs_tmp):
    datos = datos_cabecera("zh", plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])
