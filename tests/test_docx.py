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
    "paper": "a4",
    "margins": {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0},
    "font_size": 11,
}


def _datos_docx():
    d = latex_gen.empty_data()
    d["cv_language"] = "es"
    d["name"] = "Ana García López"
    d["profession"] = "Ingeniera de software"
    d["email"] = "ana.garcia@example.com"
    d["summary"] = "Perfil profesional de prueba para la exportación Word."
    d["education"] = [{
        "degree_type": "bachelor", "degree": "Ingeniería Informática",
        "institution": "Universidad de Madrid", "start": "2012", "end": "2016",
        "grade": "8.5/10",
    }]
    d["work"] = [{
        "position": "Ingeniera backend", "company": "Fintech Nova", "start": "2020",
        "end": "Actualidad", "achievements": "Migramos a microservicios.",
    }]
    d["skills"] = [{"category": "Lenguajes", "values": "Python, Java"}]
    d["languages"] = [{"language": "Español", "level": "Nativo"}]
    d["references"] = [{"name": "Luis Pérez", "contact": "luis@example.com"}]
    return d


def test_exportar_docx_incluye_nombre_y_secciones(tmp_path):
    ruta = tmp_path / "cv.docx"
    docx_gen.export(_datos_docx(), PREFS_PRUEBA, str(ruta))
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
    docx_gen.export(latex_gen.empty_data(), PREFS_PRUEBA, str(ruta))
    assert ruta.is_file()
    doc = Document(str(ruta))
    assert [p.text for p in doc.paragraphs] is not None


# ---------------------------------------------------------------------------
# Cabecera dinamica: socials y datos adicionales
# ---------------------------------------------------------------------------

def test_exportar_docx_cabecera_socials(tmp_path):
    d = _datos_docx()
    d["socials"] = [
        {"network": "github", "label": "Ignorado", "value": "github.com/ana"},
        {"network": "linkedin", "label": "", "value": "linkedin.com/in/a"},
        {"network": "website", "label": "", "value": "ana.dev"},
        {"network": "other", "label": "Mastodon", "value": "mastodon/@ana"},
        {"network": "x", "label": "", "value": "   "},
    ]
    d["extra_fields"] = [{"label": "Nacimiento", "value": "12/05/1994"}]
    textos = _textos_docx(d, tmp_path, "cabecera_socials.docx")
    cabecera = " ".join(textos)

    assert "GitHub: github.com/ana" in cabecera
    assert "LinkedIn: linkedin.com/in/a" in cabecera
    assert "Web: ana.dev" in cabecera
    assert "Mastodon: mastodon/@ana" in cabecera
    assert "Nacimiento: 12/05/1994" in cabecera
    assert "Ignorado" not in cabecera
    # Los socials van antes de los datos adicionales.
    assert cabecera.index("GitHub:") < cabecera.index("Nacimiento:")


# ---------------------------------------------------------------------------
# Bloques libres en la exportacion Word
# ---------------------------------------------------------------------------

def _datos_docx_con_bloque_educacion():
    d = _datos_docx()
    d["blocks"] = [
        {"id": "linea", "type": "separator", "style": "line",
         "position": "education"},
        {"id": "seccion", "type": "section", "title": "Mi sección",
         "content": "Primera línea del bloque.\nSegunda línea del bloque.",
         "position": "education"},
    ]
    return d


def _textos_docx(datos, tmp_path, nombre):
    ruta = tmp_path / nombre
    docx_gen.export(datos, PREFS_PRUEBA, str(ruta))
    return [p.text for p in Document(str(ruta)).paragraphs]


def test_exportar_docx_bloque_anclado_a_educacion(tmp_path):
    textos = _textos_docx(_datos_docx_con_bloque_educacion(), tmp_path, "bloques.docx")

    i_educacion = textos.index("Educación")
    i_bloque = textos.index("Mi sección")
    i_siguiente = textos.index("Experiencia laboral")
    assert i_educacion < i_bloque < i_siguiente
    assert any("Primera línea del bloque." in t for t in textos)
    assert any("Segunda línea del bloque." in t for t in textos)


def test_exportar_docx_bloque_seccion_vacio_se_omite(tmp_path):
    sin_bloque = _textos_docx(_datos_docx(), tmp_path, "sin_bloque.docx")

    d = _datos_docx()
    d["blocks"] = [
        {"id": "vacio", "type": "section", "title": "",
         "content": "", "position": "education"},
        {"id": "nulos", "type": "section", "title": None,
         "content": None, "position": "end"},
    ]
    con_vacios = _textos_docx(d, tmp_path, "con_vacios.docx")
    assert con_vacios == sin_bloque


def test_exportar_docx_bloques_listado(tmp_path):
    d = _datos_docx()
    d["blocks"] = [
        {"id": "l1", "type": "list", "mode": "columns", "title": "Enlaces",
         "columns": 2, "position": "end",
         "entries": [{"title": "Web", "detail": "example.com"}]},
        {"id": "l2", "type": "list", "mode": "period", "title": "Cronología",
         "columns": 1, "position": "end",
         "entries": [{"period": "2020", "description": "Hito uno."}]},
    ]
    textos = _textos_docx(d, tmp_path, "listado.docx")
    assert "Enlaces" in textos
    assert any("Web" in t and "example.com" in t for t in textos)
    assert "Cronología" in textos
    assert "2020" in textos
    assert any("Hito uno." in t for t in textos)


def test_exportar_docx_bloques_mal_formados_no_lanzan(tmp_path):
    d = _datos_docx()
    d["blocks"] = [
        None, 3, "texto", [], (),
        {},
        {"type": "other"},
        {"type": "section", "title": None, "content": None},
        {"type": "section", "title": 7, "content": 7},
        {"type": "separator", "style": "inexistente"},
        {"type": "separator", "style": None, "position": None},
        {"type": "separator", "position": "marte"},
    ]
    ruta = tmp_path / "mal_formados.docx"
    docx_gen.export(d, PREFS_PRUEBA, str(ruta))
    assert ruta.is_file()
    textos = [p.text for p in Document(str(ruta)).paragraphs]
    assert "7" in textos
    assert "Educación" in textos

    # "blocks" con un tipo que no es lista tampoco rompe la exportacion.
    d["blocks"] = "no-es-lista"
    ruta2 = tmp_path / "no_lista.docx"
    docx_gen.export(d, PREFS_PRUEBA, str(ruta2))
    assert ruta2.is_file()


# ---------------------------------------------------------------------------
# Orden, ocultacion y titulos personalizados de seccion
# ---------------------------------------------------------------------------

# Encabezados visibles con _datos_docx() en el orden por defecto (solo las
# secciones que tienen contenido).
ETIQUETAS_ES = [
    "Perfil", "Educación", "Experiencia laboral", "Habilidades", "Idiomas",
    "Referencias",
]


def _indice(textos, aguja):
    """Primera posicion cuyo texto contiene `aguja`; falla si no aparece."""
    for i, texto in enumerate(textos):
        if aguja in texto:
            return i
    raise AssertionError(f"No se encontro {aguja!r}")


def _secuencia_encabezados(textos, etiquetas):
    """Solo los parrafos que son exactamente un encabezado de seccion."""
    conocidas = set(etiquetas)
    return [t for t in textos if t in conocidas]


def test_exportar_docx_orden_por_defecto_no_cambia(tmp_path):
    # _datos_docx() hereda de datos_vacios() section_order vacio y ninguna
    # seccion oculta: la secuencia por defecto debe ser la canonica.
    textos = _textos_docx(_datos_docx(), tmp_path, "defecto.docx")
    assert _secuencia_encabezados(textos, ETIQUETAS_ES) == ETIQUETAS_ES


def test_exportar_docx_orden_secciones_invertido(tmp_path):
    d = _datos_docx()
    d["section_order"] = list(reversed(latex_gen.DEFAULT_SECTION_ORDER))
    textos = _textos_docx(d, tmp_path, "orden_inverso.docx")

    assert _secuencia_encabezados(textos, ETIQUETAS_ES) == [
        "Referencias", "Idiomas", "Habilidades", "Experiencia laboral",
        "Educación", "Perfil",
    ]

    # Las entradas acompanan a su seccion, no solo cambian las cabeceras.
    indices = [
        _indice(textos, aguja) for aguja in (
            "Luis Pérez",                       # referencias
            "Español",                          # idiomas
            "Python, Java",                     # habilidades
            "Ingeniera backend",                # trabajo
            "Universidad de Madrid",            # educacion
            "Perfil profesional de prueba",     # perfil
        )
    ]
    assert indices == sorted(indices)


def test_exportar_docx_seccion_oculta_sin_encabezado_ni_entradas(tmp_path):
    d = _datos_docx()
    d["hidden_sections"] = ["education"]
    textos = _textos_docx(d, tmp_path, "oculta.docx")

    assert "Educación" not in textos
    assert not any("Universidad de Madrid" in t for t in textos)
    assert not any("Ingeniería Informática" in t for t in textos)
    assert not any("8.5/10" in t for t in textos)

    assert _secuencia_encabezados(textos, ETIQUETAS_ES) == [
        "Perfil", "Experiencia laboral", "Habilidades", "Idiomas",
        "Referencias",
    ]


def test_exportar_docx_titulos_seccion_sustituyen_etiquetas(tmp_path):
    d = _datos_docx()
    d["section_titles"] = {
        "education": "Formación académica",
        "work": "Trayectoria profesional",
        "skills": "Competencias",
    }
    textos = _textos_docx(d, tmp_path, "titulos.docx")

    esperados = [
        "Perfil", "Formación académica", "Trayectoria profesional",
        "Competencias", "Idiomas", "Referencias",
    ]
    assert _secuencia_encabezados(textos, esperados) == esperados
    for etiqueta in ("Educación", "Experiencia laboral", "Habilidades"):
        assert etiqueta not in textos
    # Las entradas de las secciones renombradas siguen presentes.
    assert any("Universidad de Madrid" in t for t in textos)
    assert any("Ingeniera backend" in t for t in textos)
    assert any("Python" in t for t in textos)


def test_exportar_docx_bloque_anclado_a_seccion_oculta_conserva_posicion(tmp_path):
    d = _datos_docx()
    d["hidden_sections"] = ["work"]
    d["blocks"] = [{
        "id": "nota", "type": "section", "title": "Nota de trayectoria",
        "content": "Bloque anclado a una seccion oculta.",
        "position": "work",
    }]
    textos = _textos_docx(d, tmp_path, "oculta_con_bloque.docx")

    # La seccion oculta no deja encabezado ni entradas...
    assert "Experiencia laboral" not in textos
    assert not any("Ingeniera backend" in t for t in textos)
    assert not any("Migramos a microservicios." in t for t in textos)

    # ...pero el bloque anclado a ella conserva su posicion: entre la seccion
    # visible anterior y la siguiente.
    i_educacion = textos.index("Educación")
    i_bloque = textos.index("Nota de trayectoria")
    i_habilidades = textos.index("Habilidades")
    assert i_educacion < i_bloque < i_habilidades
    assert i_educacion < _indice(textos, "Bloque anclado a una seccion oculta.") < i_habilidades
