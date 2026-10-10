# -*- coding: utf-8 -*-
"""Paleta de colores del documento: normalizacion, LaTeX, API y Word.

Sin GUI ni pywebview. La compilacion PDF real lleva skipif cuando no hay
pdflatex (mismo patron que ``tests/test_roundtrip_tex.py``). Los valores de
los colores de plantilla se contrastan contra los ``templates/*.tex`` reales.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from docx import Document  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import RGBColor  # noqa: E402

import docx_gen  # noqa: E402
import latex_engine  # noqa: E402
import latex_gen  # noqa: E402
import prefs  # noqa: E402
import tex_datos  # noqa: E402
from main import Api  # noqa: E402

# Misma forma que tests/test_esquema.py: sin la clave "colores".
PREFS_PRUEBA = {
    "papel": "a4",
    "margenes": {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0},
    "fuente": 11,
}

COLORES_VALIDOS = {
    "primario": "#12AB34",
    "secundario": "#00AA88",
    "texto": "#112233",
    "gris": "#A1B2C3",
}

MOTOR_PDF = latex_engine.find_pdflatex()

ETIQUETAS_ES = ("Perfil", "Educación", "Experiencia laboral")


class _Explosivo:
    """Tipo hostil: convertirlo a texto o compararlo revienta."""

    def __str__(self):
        raise RuntimeError("boom")

    def __eq__(self, otro):
        raise RuntimeError("boom")

    __hash__ = None


class _DictExplosivo(dict):
    """Diccionario hostil: cualquier get() revienta."""

    def get(self, clave, defecto=None):
        raise RuntimeError("boom")


def _prefs_con(colores):
    p = dict(PREFS_PRUEBA)
    p["colores"] = colores
    return p


def _datos_prueba():
    d = latex_gen.datos_vacios()
    d["idioma_cv"] = "es"
    d["perfil"] = "Perfil con colores."
    d["trabajo"] = [{"puesto": "Desarrolladora", "empresa": "Acme"}]
    return d


def _tex_de_plantilla(pid):
    ruta = os.path.join(latex_gen.BASE_DIR, "templates", latex_gen.ARCHIVOS[pid])
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# normalizar_hex
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "valor, esperado",
    [
        ("#12AB34", (0x12, 0xAB, 0x34)),
        ("#12ab34", (0x12, 0xAB, 0x34)),
        ("  #12AB34  ", (0x12, 0xAB, 0x34)),
        ("#abc", (0xAA, 0xBB, 0xCC)),
        ("#AbC", (0xAA, 0xBB, 0xCC)),
        ("  #aBc  ", (0xAA, 0xBB, 0xCC)),
        ("#000000", (0, 0, 0)),
        ("#FFFFFF", (255, 255, 255)),
    ],
)
def test_normalizar_hex_acepta_formas_validas(valor, esperado):
    assert latex_gen.normalizar_hex(valor) == esperado


@pytest.mark.parametrize(
    "valor",
    [
        "",
        "   ",
        None,
        "red",
        "#12",
        "#12345",
        "#GGGGGG",
        "#12345Z",
        123,
        ["#FFFFFF"],
        {"x": 1},
        b"#FFFFFF",
    ],
)
def test_normalizar_hex_rechaza_invalidos(valor):
    assert latex_gen.normalizar_hex(valor) is None


# ---------------------------------------------------------------------------
# colores_de_plantilla sobre los templates reales
# ---------------------------------------------------------------------------

def test_colores_de_plantilla_clasico():
    assert latex_gen.colores_de_plantilla(_tex_de_plantilla("clasico")) == {
        "accent": "#233A5E",
        "gris": "#6E7684",
    }


def test_colores_de_plantilla_creativo():
    colores = latex_gen.colores_de_plantilla(_tex_de_plantilla("creativo"))
    assert colores["accent"] == "#E05244"
    assert colores["acento2"] == "#00897B"
    # El template real define acento3 como RGB{244,180,64} (#F4B440).
    assert colores["acento3"] == "#F4B440"


def test_colores_de_plantilla_chino():
    assert latex_gen.colores_de_plantilla(_tex_de_plantilla("chino"))["accent"] == "#1F347D"


@pytest.mark.parametrize("tex", ["", None, 7, b"%", _Explosivo()])
def test_colores_de_plantilla_no_lanza(tex):
    assert latex_gen.colores_de_plantilla(tex) == {}


# ---------------------------------------------------------------------------
# build_tex: sustituciones de la paleta
# ---------------------------------------------------------------------------

def test_build_tex_primario_reemplaza_accent():
    tex = latex_gen.build_tex(_datos_prueba(), _prefs_con({"primario": "#123456"}))
    assert "\\definecolor{accent}{RGB}{18,52,86}" in tex
    assert "35,58,94" not in tex


def test_build_tex_secundario_reemplaza_acento2_en_creativo():
    d = _datos_prueba()
    d["plantilla"] = "creativo"
    tex = latex_gen.build_tex(d, _prefs_con({"secundario": "#00AA88"}))
    assert "\\definecolor{acento2}{RGB}{0,170,136}" in tex
    assert tex.count("\\definecolor{acento2}") == 1


def test_build_tex_secundario_en_clasico_inyecta_acento2():
    # Comportamiento congelado de t1: clasico no define acento2, asi que la
    # definicion se inyecta antes de \begin{document} en vez de reemplazar
    # nada; las definiciones existentes (accent y gris) quedan intactas.
    tex = latex_gen.build_tex(_datos_prueba(), _prefs_con({"secundario": "#00AA88"}))
    inyectado = "\\definecolor{acento2}{RGB}{0,170,136}"
    assert inyectado in tex
    assert tex.index(inyectado) < tex.index("\\begin{document}")
    assert "\\definecolor{accent}{RGB}{35,58,94}" in tex
    assert "\\definecolor{gris}{RGB}{110,118,132}" in tex


def test_build_tex_gris_reemplaza_gris():
    tex = latex_gen.build_tex(_datos_prueba(), _prefs_con({"gris": "#A1B2C3"}))
    assert "\\definecolor{gris}{RGB}{161,178,195}" in tex
    assert "110,118,132" not in tex


def test_build_tex_texto_inyecta_cvtexto_antes_y_color_despues():
    tex = latex_gen.build_tex(_datos_prueba(), _prefs_con({"texto": "#112233"}))
    definicion = tex.index("\\definecolor{cvtexto}{RGB}{17,34,51}")
    begin = tex.index("\\begin{document}")
    activacion = tex.index("\\color{cvtexto}", begin)
    assert definicion < begin < activacion
    assert tex.count("\\definecolor{cvtexto}") == 1
    assert tex.count("\\color{cvtexto}") == 1


def test_build_tex_roundtrip_con_paleta_completa():
    d = _datos_prueba()
    tex = latex_gen.build_tex(d, _prefs_con(COLORES_VALIDOS))
    for esperado in (
        "\\definecolor{accent}{RGB}{18,171,52}",
        "\\definecolor{acento2}{RGB}{0,170,136}",
        "\\definecolor{gris}{RGB}{161,178,195}",
        "\\definecolor{cvtexto}{RGB}{17,34,51}",
    ):
        assert esperado in tex
    assert tex_datos.extraer(tex) == d


# ---------------------------------------------------------------------------
# build_tex: identidad byte a byte sin colores validos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "colores",
    [
        None,  # prefs sin la clave "colores"
        "no-es-dict",
        {"primario": "", "secundario": "", "texto": "", "gris": ""},
        {"primario": "red", "secundario": "#12", "texto": "#GGGGGG", "gris": "  "},
        {"primario": 123, "secundario": [], "texto": {"x": 1}, "gris": None},
        {"primario": "#", "secundario": "#12345", "texto": "#12345Z", "gris": True},
    ],
)
def test_build_tex_sin_colores_validos_no_cambia_la_salida(colores):
    d = _datos_prueba()
    p = dict(PREFS_PRUEBA)
    if colores is not None:
        p["colores"] = colores
    assert latex_gen.build_tex(d, p) == latex_gen.build_tex(d, PREFS_PRUEBA)


def test_build_tex_colores_hostiles_no_cambian_la_salida():
    d = _datos_prueba()
    base = latex_gen.build_tex(d, PREFS_PRUEBA)
    for colores in (_Explosivo(), _DictExplosivo(), _DictExplosivo(primario="#123456")):
        assert latex_gen.build_tex(d, _prefs_con(colores)) == base


# ---------------------------------------------------------------------------
# Api.colores_plantilla
# ---------------------------------------------------------------------------

def test_api_colores_plantilla_creativo():
    r = Api(None).colores_plantilla("creativo")
    assert r["ok"] is True
    assert r["colores"]["accent"] == "#E05244"
    assert r["colores"]["acento2"] == "#00897B"


@pytest.mark.parametrize("plantilla", [None, "marte", "", 123, []])
def test_api_colores_plantilla_desconocida_cae_a_clasico(plantilla):
    r = Api(None).colores_plantilla(plantilla)
    assert r["ok"] is True
    assert r["colores"]["accent"] == "#233A5E"
    assert r["colores"]["gris"] == "#6E7684"


def test_api_colores_plantilla_no_lanza():
    api = Api(None)
    for plantilla in (_Explosivo(), {"x": 1}, b"chino", object()):
        r = api.colores_plantilla(plantilla)
        assert isinstance(r, dict)
        assert isinstance(r.get("ok"), bool)
    r = api.colores_plantilla(_Explosivo())
    assert r["ok"] is False
    assert isinstance(r["errores"], list) and r["errores"]


# ---------------------------------------------------------------------------
# docx_gen: primario en encabezados y separadores, texto en Normal
# ---------------------------------------------------------------------------

def _datos_docx():
    d = latex_gen.datos_vacios()
    d["idioma_cv"] = "es"
    d["nombre"] = "Ana García"
    d["perfil"] = "Perfil de prueba."
    d["educacion"] = [{
        "tipo": "Grado", "titulo": "Informática", "institucion": "UM",
        "desde": "2012", "hasta": "2016",
    }]
    d["trabajo"] = [{"puesto": "Dev", "empresa": "Acme", "desde": "2020", "hasta": "2024"}]
    d["bloques"] = [
        {"id": "linea", "tipo": "separador", "estilo": "linea", "posicion": "final"},
        {"id": "banda", "tipo": "separador", "estilo": "banda", "posicion": "final"},
    ]
    return d


def _separadores(doc):
    """(colores de borde de linea, (borde, relleno) de banda) leidos del XML."""
    lineas, bandas = [], []
    for par in doc.paragraphs:
        p_pr = par._p.pPr
        if p_pr is None:
            continue
        borde = p_pr.find(qn("w:pBdr"))
        if borde is None:
            continue
        inferior = borde.find(qn("w:bottom"))
        color = inferior.get(qn("w:color")) if inferior is not None else None
        sombreado = p_pr.find(qn("w:shd"))
        if sombreado is None:
            lineas.append(color)
        else:
            bandas.append((color, sombreado.get(qn("w:fill"))))
    return lineas, bandas


def _colores_de_encabezado(doc, titulo):
    for par in doc.paragraphs:
        if par.text == titulo:
            return [run.font.color.rgb for run in par.runs if run.text]
    raise AssertionError("No se encontro el encabezado %r" % titulo)


def test_docx_primario_y_texto_con_paleta(tmp_path):
    ruta = tmp_path / "colores.docx"
    prefs_colores = dict(PREFS_PRUEBA, colores={"primario": "#12AB34", "texto": "#112233"})
    docx_gen.exportar(_datos_docx(), prefs_colores, str(ruta))
    doc = Document(str(ruta))

    primario = RGBColor(0x12, 0xAB, 0x34)
    for titulo in ETIQUETAS_ES:
        assert _colores_de_encabezado(doc, titulo) == [primario], titulo

    lineas, bandas = _separadores(doc)
    assert lineas == ["12AB34"]
    assert bandas == [("12AB34", "12AB34")]

    assert doc.styles["Normal"].font.color.rgb == RGBColor(0x11, 0x22, 0x33)


def test_docx_sin_paleta_usa_el_acento_por_defecto(tmp_path):
    ruta = tmp_path / "sin_colores.docx"
    docx_gen.exportar(_datos_docx(), PREFS_PRUEBA, str(ruta))
    doc = Document(str(ruta))

    lineas, bandas = _separadores(doc)
    assert lineas == [docx_gen.COLOR_ACENTO]
    assert bandas == [(docx_gen.COLOR_ACENTO, docx_gen.COLOR_ACENTO)]
    for titulo in ETIQUETAS_ES:
        assert _colores_de_encabezado(doc, titulo) == [None], titulo


# ---------------------------------------------------------------------------
# Compilacion real de un .tex con paleta
# ---------------------------------------------------------------------------

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


@pytest.mark.skipif(MOTOR_PDF is None, reason="Sin motor LaTeX (pdflatex) instalado")
def test_compila_pdf_con_paleta(prefs_tmp):
    tex = latex_gen.build_tex(_datos_prueba(), _prefs_con(COLORES_VALIDOS))
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])
