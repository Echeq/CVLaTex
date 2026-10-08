# -*- coding: utf-8 -*-
"""Exportacion Word con docx_gen: sin LaTeX y sin GUI.

Genera un .docx temporal, lo reabre con python-docx y comprueba el nombre y
las cadenas de las secciones en espanol.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from docx import Document  # noqa: E402

import docx_gen  # noqa: E402
import latex_gen  # noqa: E402

PREFS_PRUEBA = {
    "papel": "a4",
    "margenes": {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0},
    "fuente": 11,
}


def _datos_docx():
    d = latex_gen.datos_vacios()
    d["idioma_cv"] = "es"
    d["nombre"] = "Ana García López"
    d["profesion"] = "Ingeniera de software"
    d["email"] = "ana.garcia@example.com"
    d["perfil"] = "Perfil profesional de prueba para la exportación Word."
    d["educacion"] = [{
        "tipo": "Grado", "titulo": "Ingeniería Informática",
        "institucion": "Universidad de Madrid", "desde": "2012", "hasta": "2016",
        "nota": "8.5/10",
    }]
    d["trabajo"] = [{
        "puesto": "Ingeniera backend", "empresa": "Fintech Nova", "desde": "2020",
        "hasta": "Actualidad", "logros": "Migramos a microservicios.",
    }]
    d["habilidades"] = [{"categoria": "Lenguajes", "valores": "Python, Java"}]
    d["idiomas"] = [{"idioma": "Español", "nivel": "Nativo"}]
    d["referencias"] = [{"nombre": "Luis Pérez", "contacto": "luis@example.com"}]
    return d


def test_exportar_docx_incluye_nombre_y_secciones(tmp_path):
    ruta = tmp_path / "cv.docx"
    docx_gen.exportar(_datos_docx(), PREFS_PRUEBA, str(ruta))
    assert ruta.is_file()

    doc = Document(str(ruta))
    textos = [p.text for p in doc.paragraphs]

    assert any("Ana García López" in t for t in textos)
    assert any("ana.garcia@example.com" in t for t in textos)

    for seccion in (
        "Perfil", "Educación", "Experiencia laboral", "Habilidades",
        "Idiomas", "Referencias",
    ):
        assert any(seccion in t for t in textos), seccion

    assert any("Universidad de Madrid" in t for t in textos)
    assert any("8.5/10" in t for t in textos)
    assert any("Python" in t for t in textos)
    assert any("Luis Pérez" in t for t in textos)


def test_exportar_docx_con_datos_vacios_no_falla(tmp_path):
    ruta = tmp_path / "vacio.docx"
    docx_gen.exportar(latex_gen.datos_vacios(), PREFS_PRUEBA, str(ruta))
    assert ruta.is_file()
    doc = Document(str(ruta))
    assert [p.text for p in doc.paragraphs] is not None
