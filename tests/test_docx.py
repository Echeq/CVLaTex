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


# ---------------------------------------------------------------------------
# Bloques libres en la exportacion Word
# ---------------------------------------------------------------------------

def _datos_docx_con_bloque_educacion():
    d = _datos_docx()
    d["bloques"] = [
        {"id": "linea", "tipo": "separador", "estilo": "linea",
         "posicion": "educacion"},
        {"id": "seccion", "tipo": "seccion", "titulo": "Mi sección",
         "contenido": "Primera línea del bloque.\nSegunda línea del bloque.",
         "posicion": "educacion"},
    ]
    return d


def _textos_docx(datos, tmp_path, nombre):
    ruta = tmp_path / nombre
    docx_gen.exportar(datos, PREFS_PRUEBA, str(ruta))
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
    d["bloques"] = [
        {"id": "vacio", "tipo": "seccion", "titulo": "",
         "contenido": "", "posicion": "educacion"},
        {"id": "nulos", "tipo": "seccion", "titulo": None,
         "contenido": None, "posicion": "final"},
    ]
    con_vacios = _textos_docx(d, tmp_path, "con_vacios.docx")
    assert con_vacios == sin_bloque


def test_exportar_docx_bloques_listado(tmp_path):
    d = _datos_docx()
    d["bloques"] = [
        {"id": "l1", "tipo": "listado", "modo": "columnas", "titulo": "Enlaces",
         "columnas": 2, "posicion": "final",
         "entradas": [{"titulo": "Web", "detalle": "example.com"}]},
        {"id": "l2", "tipo": "listado", "modo": "periodo", "titulo": "Cronología",
         "columnas": 1, "posicion": "final",
         "entradas": [{"periodo": "2020", "descripcion": "Hito uno."}]},
    ]
    textos = _textos_docx(d, tmp_path, "listado.docx")
    assert "Enlaces" in textos
    assert any("Web" in t and "example.com" in t for t in textos)
    assert "Cronología" in textos
    assert "2020" in textos
    assert any("Hito uno." in t for t in textos)


def test_exportar_docx_bloques_mal_formados_no_lanzan(tmp_path):
    d = _datos_docx()
    d["bloques"] = [
        None, 3, "texto", [], (),
        {},
        {"tipo": "otro"},
        {"tipo": "seccion", "titulo": None, "contenido": None},
        {"tipo": "seccion", "titulo": 7, "contenido": 7},
        {"tipo": "separador", "estilo": "inexistente"},
        {"tipo": "separador", "estilo": None, "posicion": None},
        {"tipo": "separador", "posicion": "marte"},
    ]
    ruta = tmp_path / "mal_formados.docx"
    docx_gen.exportar(d, PREFS_PRUEBA, str(ruta))
    assert ruta.is_file()
    textos = [p.text for p in Document(str(ruta)).paragraphs]
    assert "7" in textos
    assert "Educación" in textos

    # "bloques" con un tipo que no es lista tampoco rompe la exportacion.
    d["bloques"] = "no-es-lista"
    ruta2 = tmp_path / "no_lista.docx"
    docx_gen.exportar(d, PREFS_PRUEBA, str(ruta2))
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
    # _datos_docx() hereda de datos_vacios() orden_secciones vacio y ninguna
    # seccion oculta: la secuencia por defecto debe ser la canonica.
    textos = _textos_docx(_datos_docx(), tmp_path, "defecto.docx")
    assert _secuencia_encabezados(textos, ETIQUETAS_ES) == ETIQUETAS_ES


def test_exportar_docx_orden_secciones_invertido(tmp_path):
    d = _datos_docx()
    d["orden_secciones"] = list(reversed(latex_gen.ORDEN_SECCIONES_DEFECTO))
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
    d["secciones_ocultas"] = ["educacion"]
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
    d["titulos_seccion"] = {
        "educacion": "Formación académica",
        "trabajo": "Trayectoria profesional",
        "habilidades": "Competencias",
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
    d["secciones_ocultas"] = ["trabajo"]
    d["bloques"] = [{
        "id": "nota", "tipo": "seccion", "titulo": "Nota de trayectoria",
        "contenido": "Bloque anclado a una seccion oculta.",
        "posicion": "trabajo",
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
