# -*- coding: utf-8 -*-
"""Sidebar templates: registry, sidebar/header split, photos, bar and compile.

Both variants move the photo, the school logo and the contacts (socials and
extra fields included) from the header into a full-height accent bar: "sidebar"
paints it on the left edge (bar at x=0) and "sidebar-right" mirrors it on the
right edge (bar at x=paperwidth-6.2cm). The main column only keeps the
name/profession header and the body sections. The bar rectangle and the first
overlay text are measured from the decompressed PDF content stream.
Compilations use the same skipif pattern as test_roundtrip_tex.py.
"""

import base64
import os
import re
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_engine  # noqa: E402
import latex_gen  # noqa: E402
import prefs  # noqa: E402
import tex_datos  # noqa: E402

MOTOR_PDF = latex_engine.find_pdflatex()
MOTOR_CJK = latex_engine.find_xelatex()

# 1x1 RGBA PNG (same constant used by test_imagen.py; no Pillow needed).
PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA"
    "60e6kgAAAABJRU5ErkJggg=="
)

PLANTILLAS = ("sidebar", "sidebar-right")
IDIOMAS = ("es", "zh")

# Start of the zero-height overlay emitted by latex_gen._sidebar().
BAR_START = {
    "sidebar": "\\hspace*{-6.2cm}",
    "sidebar-right": "\\hspace*{\\dimexpr\\textwidth+1.6cm\\relax}",
}
BAR_END = "\\end{minipage}"

# A4 in PDF points and the 6.2cm accent bar, as drawn in the content stream.
CM_PT = 72.0 / 2.54
ANCHO_A4_PT = 595.276
ALTO_A4_PT = 841.89
ANCHO_BARRA_PT = 6.2 * CM_PT


@pytest.fixture()
def prefs_tmp(tmp_path, monkeypatch):
    """Isolate prefs (dirs and cache) from the user machine."""
    app = tmp_path / "app"
    monkeypatch.setattr(prefs, "APP_DIR", str(app))
    monkeypatch.setattr(prefs, "CACHE_DIR", str(app / "cache"))
    monkeypatch.setattr(prefs, "BUILD_DIR", str(app / "cache" / "build"))
    monkeypatch.setattr(prefs, "PREFS_FILE", str(app / "prefs.json"))
    monkeypatch.setattr(prefs, "_CACHE", None)
    return tmp_path


def datos_sidebar(idioma="es", plantilla="sidebar"):
    """Minimal CV with all the personal data that must land in the bar."""
    d = latex_gen.empty_data()
    d["template"] = plantilla
    d["cv_language"] = idioma
    if idioma == "zh":
        d["name"] = "张伟"
        d["profession"] = "后端开发工程师"
        d["email"] = "zhangwei@example.com"
        d["phone"] = "13800000000"
        d["socials"] = [
            {"network": "github", "label": "", "value": "github.com/zhangwei"},
        ]
        d["extra_fields"] = [{"label": "国籍", "value": "中国"}]
    else:
        d["name"] = "Ana García"
        d["profession"] = "Ingeniera de software"
        d["email"] = "ana@example.com"
        d["phone"] = "+34 600 000 000"
        d["socials"] = [
            {"network": "linkedin", "label": "", "value": "linkedin.com/in/ana"},
        ]
        d["extra_fields"] = [{"label": "Nacimiento", "value": "12/05/1994"}]
    return d


def barra(tex, plantilla):
    """Slice of the sidebar overlay: from its shift to the minipage end."""
    inicio = tex.index(BAR_START[plantilla])
    fin = tex.index(BAR_END, inicio) + len(BAR_END)
    return tex[inicio:fin]


def resto(tex, plantilla):
    """Slice of the document after the sidebar overlay (header and body)."""
    return tex[tex.index(BAR_END, tex.index(BAR_START[plantilla])):tex.index("\\end{document}")]


def escribir_png(tmp_path, nombre):
    """Write a real (minimal) PNG file and return its path."""
    ruta = tmp_path / nombre
    ruta.write_bytes(base64.b64decode(PNG_B64))
    return ruta


# --------------------------------------------------------------------- PDF

_PDF_TOKEN_RE = re.compile(
    rb"\((?:\\.|[^\\)])*\)"           # literal string
    rb"|<[0-9A-Fa-f\s]*>"             # hex string
    rb"|/[^\s/\[\]<>(){}]+"           # name
    rb"|[-+]?(?:\d+\.?\d*|\.\d+)"     # number
    rb"|[A-Za-z*'\"]+"                # operator
)
_NUMBER_RE = re.compile(rb"[-+]?(?:\d+\.?\d*|\.\d+)\Z")


def _pdf_streams(pdf_path):
    """Decompressed FlateDecode streams of the PDF (font streams included)."""
    with open(pdf_path, "rb") as f:
        data = f.read()
    streams = []
    for match in re.finditer(rb"stream\r?\n", data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end == -1:
            continue
        raw = data[start:end].rstrip(b"\r\n")
        try:
            streams.append(zlib.decompress(raw))
        except zlib.error:
            continue
    return streams


def _matrix_mul(m1, m2):
    """Row-vector matrix product m1 x m2 in PDF [a b c d e f] form."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + b1 * c2,
        a1 * b2 + b1 * d2,
        c1 * a2 + d1 * c2,
        c1 * b2 + d1 * d2,
        e1 * a2 + f1 * c2 + e2,
        e1 * b2 + f1 * d2 + f2,
    )


def page_geometry(pdf_path):
    """(rects, texts) of the page content stream in device PDF points.

    rects are (x, y, w, h) of every `re` operator; texts are the (x, y) of the
    first `Td` line of every `BT` block, both with the current `cm` matrix
    (q/Q stack included) applied.
    """
    rects, texts = [], []
    for stream in _pdf_streams(pdf_path):
        if b"BT" not in stream or b"re" not in stream:
            continue
        ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        stack = []
        numbers = []
        in_text = False
        first_line = False
        for token in _PDF_TOKEN_RE.findall(stream):
            if _NUMBER_RE.match(token):
                numbers.append(float(token))
                continue
            if token == b"q":
                stack.append(ctm)
            elif token == b"Q":
                if stack:
                    ctm = stack.pop()
            elif token == b"cm" and len(numbers) >= 6:
                ctm = _matrix_mul(tuple(numbers[-6:]), ctm)
            elif token == b"re" and len(numbers) >= 4:
                x, y, w, h = numbers[-4:]
                rects.append((
                    ctm[0] * x + ctm[2] * y + ctm[4],
                    ctm[1] * x + ctm[3] * y + ctm[5],
                    abs(w * ctm[0]) + abs(h * ctm[2]),
                    abs(w * ctm[1]) + abs(h * ctm[3]),
                ))
            elif token == b"BT":
                in_text, first_line = True, True
            elif token == b"ET":
                in_text = False
            elif token == b"Td" and in_text and first_line and len(numbers) >= 2:
                x, y = numbers[-2:]
                texts.append((
                    ctm[0] * x + ctm[2] * y + ctm[4],
                    ctm[1] * x + ctm[3] * y + ctm[5],
                ))
                first_line = False
            numbers = []
    return rects, texts


# ------------------------------------------------------------------- tests


@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_sidebar_registrada(plantilla):
    assert plantilla in latex_gen.TEMPLATES
    assert latex_gen.TEMPLATE_FILES[plantilla] == f"{plantilla}/{plantilla}.tex"
    ruta = os.path.join(latex_gen.BASE_DIR, "templates", plantilla, f"{plantilla}.tex")
    assert os.path.isfile(ruta)


@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_sidebar_roundtrip_y_marcadores_sustituidos(plantilla, idioma, prefs_tmp):
    datos = datos_sidebar(idioma, plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())

    # {{sidebar}} and {{header}} are replaced and nothing else is left.
    assert "{{" not in tex
    assert BAR_START[plantilla] in tex
    assert "\\Huge\\bfseries\\color{accent}" in tex
    assert tex_datos.extract(tex) == datos


@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_sidebar_vacia_no_emite_barra(plantilla, idioma, prefs_tmp):
    datos = latex_gen.empty_data()
    datos["template"] = plantilla
    datos["cv_language"] = idioma
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "{{" not in tex
    assert BAR_START[plantilla] not in tex
    assert latex_gen._sidebar(datos, latex_gen.LANG[idioma]) == ""
    assert tex_datos.extract(tex) == datos


@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_sidebar_contactos_socials_y_extra_en_la_barra(plantilla, idioma, prefs_tmp):
    datos = datos_sidebar(idioma, plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())
    L = latex_gen.LANG[idioma]
    bloque = barra(tex, plantilla)

    assert (
        f"\\textbf{{{L['phone']}}} \\texttt{{{latex_gen.esc(datos['phone'])}}}" in bloque
    )
    assert (
        f"\\textbf{{{L['email']}}} \\texttt{{{latex_gen.esc(datos['email'])}}}" in bloque
    )
    redes = {
        "es": ("LinkedIn", "linkedin.com/in/ana"),
        "zh": ("GitHub", "github.com/zhangwei"),
    }
    etiqueta, valor = redes[idioma]
    assert f"\\textbf{{{etiqueta}:}} \\texttt{{{latex_gen.esc(valor)}}}" in bloque
    extras = {"es": "\\textbf{Nacimiento:} 12/05/1994", "zh": "\\textbf{国籍:} 中国"}
    assert extras[idioma] in bloque
    # The name is a header thing: it never enters the bar.
    assert latex_gen.esc(datos["name"]) not in bloque

    # After the bar, the main column keeps the name and no contact.
    after = resto(tex, plantilla)
    assert f"{{\\Huge\\bfseries\\color{{accent}} {latex_gen.esc(datos['name'])}}}" in after
    assert f"\\textbf{{{L['phone']}}}" not in after
    assert f"\\textbf{{{L['email']}}}" not in after


@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_sidebar_foto_y_logo_en_la_barra(plantilla, tmp_path, prefs_tmp):
    datos = datos_sidebar("es", plantilla)
    foto = escribir_png(tmp_path, "foto_local.png")
    logo = escribir_png(tmp_path, "logo_local.png")
    datos["photo"] = str(foto)
    datos["school_logo"] = str(logo)
    # Over-wide values: the bar clamps them to its 4.6cm inner width.
    datos["photo_width_cm"] = 9.0
    datos["school_logo_width_cm"] = 9.0

    tex = latex_gen.build_tex(datos, prefs.load())
    bloque = barra(tex, plantilla)

    assert "\\includegraphics" in bloque
    assert "foto.png" in bloque
    assert "logo_egresado.png" in bloque
    assert "width=4.6cm" in bloque
    assert "\\begin{minipage}[t]{4.6cm}" in bloque
    assert "keepaspectratio" in bloque
    assert "\\fcolorbox{white}{white}" in bloque
    # Both the image block and the contacts exist: a clear gap separates them.
    assert "\\vspace{1em}" in bloque
    assert bloque.index("foto.png") < bloque.index("\\vspace{1em}") < bloque.index("\\textbf{")

    after = resto(tex, plantilla)
    assert "foto.png" not in after
    assert "logo_egresado.png" not in after


@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_sidebar_barra_a_pagina_completa_en_la_plantilla(plantilla, prefs_tmp):
    datos = datos_sidebar("es", plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())

    assert "\\AddToHook{shipout/background}" in tex
    assert "\\rule[-\\paperheight]{6.2cm}{\\paperheight}" in tex
    if plantilla == "sidebar":
        # The left margin is fixed at 7cm (6.2cm bar + gutter): the placeholder
        # is not used by this template.
        assert "left=7cm" in tex
        assert "{{margin_left}}" not in tex
    else:
        # Mirrored: the right margin is fixed at 7cm and the left one stays
        # configurable.
        assert "right=7cm" in tex
        assert "{{margin_right}}" not in tex
    assert "{{" not in tex
    for macro in ("\\cvblockline", "\\cvblockband", "\\cvblockspace"):
        assert "\\newcommand{" + macro + "}" in tex
    assert "\\newcommand{\\cvsection}" in tex


@pytest.mark.skipif(
    MOTOR_PDF is None or MOTOR_CJK is None,
    reason="Sin motores LaTeX (pdflatex/xelatex) para medir el PDF",
)
@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_barra_y_contenido_medidos_en_el_pdf(plantilla, idioma, prefs_tmp):
    datos = datos_sidebar(idioma, plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]

    rects, texts = page_geometry(resultado["pdf"])
    barras = [
        r for r in rects
        if abs(r[2] - ANCHO_BARRA_PT) < 0.5 and abs(r[3] - ALTO_A4_PT) < 1.0
    ]
    assert barras, f"barra de 6.2cm x paperheight no encontrada: {rects}"
    x, y, w, h = barras[0]
    esperado_x = 0.0 if plantilla == "sidebar" else ANCHO_A4_PT - ANCHO_BARRA_PT
    assert abs(x - esperado_x) < 0.5, f"barra en x={x}, esperado {esperado_x}"
    assert abs(y) < 0.5

    # The overlay is emitted before the header and the body: the first text of
    # the page is the bar content. It must start 0.8cm inside the bar, i.e.
    # paperwidth-5.4cm for the right variant.
    assert texts, "el PDF no contiene texto"
    texto_x = texts[0][0]
    esperado_texto = (
        0.8 * CM_PT if plantilla == "sidebar" else ANCHO_A4_PT - 5.4 * CM_PT
    )
    assert abs(texto_x - esperado_texto) < 0.5, (
        f"texto en x={texto_x}, esperado {esperado_texto}"
    )
    assert x <= texto_x <= x + w
    if plantilla == "sidebar-right":
        assert abs((x + w) - ANCHO_A4_PT) < 0.5  # flush to the right edge


@pytest.mark.skipif(MOTOR_PDF is None, reason="Sin motor LaTeX (pdflatex) instalado")
@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_compila_pdf_sidebar_es(plantilla, prefs_tmp, tmp_path):
    foto = escribir_png(tmp_path, "foto.png")
    datos = datos_sidebar("es", plantilla)
    datos["photo"] = str(foto)
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, str(foto), latex_gen.extra_logos(datos))
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])


@pytest.mark.skipif(
    MOTOR_PDF is None or MOTOR_CJK is None,
    reason="Sin motores LaTeX (pdflatex/xelatex) para compilar texto CJK",
)
@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_compila_pdf_sidebar_zh(plantilla, prefs_tmp):
    datos = datos_sidebar("zh", plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])
