# -*- coding: utf-8 -*-
"""Sidebar templates: registry, sidebar/header split, photos, first-page bar.

Both variants move the photo, the school logo and the contacts (socials and
extra fields included) from the header into a full-height accent bar on the
first page only: "sidebar" paints it on the left edge (bar at x=0) and
"sidebar-right" mirrors it on the right edge (bar at x=paperwidth-6.2cm). The
main column only keeps the name/profession header and the body sections.
`shipout/background` checks `\\ReadonlyShipoutCounter=1` (the kernel increments
it before the first shipout) and an `afterpage` block runs
`\\globaldefs=1 \\newgeometry{...}` so pages 2+ use the configured margins and
the full text width. The bar rectangle and the first overlay text are measured
from the decompressed PDF content stream.
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


def datos_sidebar_largo(plantilla):
    """Spanish CV long enough to force several pages in both sidebar variants."""
    d = datos_sidebar("es", plantilla)
    d["address"] = "Madrid, España"
    d["summary"] = (
        "Ingeniera de software con más de diez años de experiencia diseñando y "
        "operando plataformas distribuidas de alta disponibilidad. Especializada en "
        "arquitecturas orientadas a servicios, observabilidad y automatización de "
        "infraestructura. " * 8
    )
    d["work"] = []
    for i in range(6):
        d["work"].append({
            "position": f"Senior Software Engineer {i + 1}",
            "company": f"Empresa Tecnológica {i + 1}",
            "start": "2018-01",
            "end": "2021-12",
            "work_mode": "presencial",
            "achievements": "\n".join([
                "Diseñé y desplegué una plataforma de servicios distribuidos con más de cien microservicios.",
                "Reduje la latencia media del sistema en un cuarenta por ciento mediante caché multinivel.",
                "Lideré la migración a Kubernetes de cargas críticas sin interrupción del servicio.",
                "Automaticé el ciclo de vida de las aplicaciones con pipelines de integración continua.",
            ] * 2),
        })
    d["projects"] = []
    for i in range(4):
        d["projects"].append({
            "name": f"Proyecto Open Source {i + 1}",
            "role": "Mantenedora",
            "start": "2020-01",
            "end": "2022-12",
            "description": (
                "Biblioteca de herramientas para el procesamiento de datos en tiempo real, "
                "con más de mil estrellas y contribuyentes de todo el mundo. " * 4
            ),
            "url": "github.com/ana/project",
        })
    d["education"] = [{
        "degree_type": "grado",
        "degree": "Ingeniería Informática",
        "institution": "Universidad Politécnica de Madrid",
        "start": "2010",
        "end": "2014",
        "grade": "9.1",
    }]
    d["skills"] = [
        {"category": "Lenguajes", "items": "Python, Go, TypeScript, SQL"},
        {"category": "Infraestructura", "items": "Kubernetes, Terraform, AWS, GCP"},
    ]
    d["languages"] = [
        {"language": "Español", "level": "Nativo"},
        {"language": "Inglés", "level": "C1"},
    ]
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


def _page_streams(pdf_path):
    """Decompressed page content streams, in page order.

    Font programs also contain BT/ET text operators, so they are filtered out:
    page content streams use Tf/Td/TJ and never start with the PostScript
    ``%!PS-AdobeFont`` header.
    """
    pages = []
    for stream in _pdf_streams(pdf_path):
        if (
            b"BT" in stream
            and b"ET" in stream
            and b"Tf" in stream
            and b"Td" in stream
            and not stream.lstrip().startswith(b"%!PS")
        ):
            pages.append(stream)
    return pages


def _pdf_page_count(pdf_path):
    """Number of page objects: detects a trailing blank page in the PDF."""
    count = 0
    for stream in _pdf_streams(pdf_path):
        if b"/MediaBox" in stream and b"/Contents" in stream:
            count += len(re.findall(rb"/Type\s*/Page\b", stream))
    if not count:
        with open(pdf_path, "rb") as f:
            count = len(re.findall(rb"/Type\s*/Page\b", f.read()))
    return count


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


def _parse_content_stream(stream):
    """(rects, texts) of one decompressed page content stream.

    rects are (x, y, w, h) of every `re` operator; texts are the (x, y) of the
    first `Td` line of every `BT` block, both with the current `cm` matrix
    (q/Q stack included) applied.
    """
    rects, texts = [], []
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


def page_geometry(pdf_path):
    """(rects, texts) of every page content stream in device PDF points."""
    rects, texts = [], []
    for stream in _page_streams(pdf_path):
        page_rects, page_texts = _parse_content_stream(stream)
        rects.extend(page_rects)
        texts.extend(page_texts)
    return rects, texts


def pages_geometry(pdf_path):
    """Per-page (rects, texts), in page order."""
    return [_parse_content_stream(stream) for stream in _page_streams(pdf_path)]


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
def test_sidebar_barra_solo_en_la_primera_pagina(plantilla, prefs_tmp):
    datos = datos_sidebar("es", plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())
    margenes = prefs.load()["margins"]

    ruta = os.path.join(latex_gen.BASE_DIR, "templates", plantilla, f"{plantilla}.tex")
    with open(ruta, "r", encoding="utf-8") as f:
        crudo = f.read()

    # The bar is drawn only while the first page is shipped. The kernel
    # increments \ReadonlyShipoutCounter before shipout/background runs, so the
    # first page sees 1 (not 0); pages 2+ see 2, 3, ...
    assert "\\usepackage{afterpage}" in tex
    assert "\\ifnum\\ReadonlyShipoutCounter=1\\relax" in tex
    inicio_hook = tex.index("\\AddToHook{shipout/background}{%")
    hook = tex[inicio_hook:tex.index("\\begin{document}", inicio_hook)]
    assert hook.index("\\ifnum\\ReadonlyShipoutCounter=1\\relax") < hook.index(
        "\\rule[-\\paperheight]{6.2cm}{\\paperheight}"
    ) < hook.index("\\fi")
    assert tex.count("\\rule[-\\paperheight]{6.2cm}{\\paperheight}") == 1

    # afterpage restores the configured margins right after page 1. \globaldefs
    # is required: without it \newgeometry inside afterpage is reverted when the
    # package's group ends. \globaldefs=0 is set explicitly right after
    # \newgeometry instead of relying on that group ending.
    inicio_after = tex.index("\\afterpage{%")
    assert tex.index("\\begin{document}") < inicio_after
    bloque_after = tex[inicio_after:tex.index("\\sloppy", inicio_after)]
    assert "\\newgeometry{%" in bloque_after
    assert bloque_after.index("\\globaldefs=1") < bloque_after.index("\\newgeometry{%")
    assert bloque_after.index("\\newgeometry{%") < bloque_after.index("\\globaldefs=0")
    for clave in ("top", "bottom", "left", "right"):
        assert f"{clave}={margenes[clave]:g}cm" in bloque_after

    # Raw template: the first page keeps the fixed 7cm bar margin on one side
    # and the configured value on the other; pages 2+ use both configured
    # values. \newgeometry inherits the paper size, so the paper key is absent.
    bloque_crudo = crudo[crudo.index("\\afterpage{%"):crudo.index("\\sloppy")]
    assert "\\globaldefs=1" in bloque_crudo
    assert "\\globaldefs=0" in bloque_crudo
    assert "\\newgeometry{%" in bloque_crudo
    assert bloque_crudo.index("\\newgeometry{%") < bloque_crudo.index("\\globaldefs=0")
    assert "{{paper}}" not in bloque_crudo
    for clave in ("{{margin_top}}", "{{margin_bottom}}", "{{margin_left}}", "{{margin_right}}"):
        assert f"{clave}cm" in bloque_crudo
    cabecera = crudo[:crudo.index("\\begin{document}")]
    if plantilla == "sidebar":
        # The left margin is fixed at 7cm (6.2cm bar + gutter) on page 1 only.
        assert "left=7cm" in cabecera
        assert "right={{margin_right}}cm" in cabecera
    else:
        # Mirrored: the right margin is fixed at 7cm on page 1 only.
        assert "right=7cm" in cabecera
        assert "left={{margin_left}}cm" in cabecera
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
def test_sidebar_largo_sin_barra_desde_la_pagina_2(plantilla, prefs_tmp):
    datos = datos_sidebar_largo(plantilla)
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]

    paginas = pages_geometry(resultado["pdf"])
    assert len(paginas) >= 2, f"el CV largo solo tiene {len(paginas)} página(s)"
    assert _pdf_page_count(resultado["pdf"]) == len(paginas), (
        "el PDF declara más páginas que las que tienen contenido (página en blanco)"
    )

    def barras(rects):
        return [
            r for r in rects
            if abs(r[2] - ANCHO_BARRA_PT) < 0.5 and abs(r[3] - ALTO_A4_PT) < 1.0
        ]

    assert barras(paginas[0][0]), f"falta la barra en la página 1: {paginas[0][0]}"
    assert not barras(paginas[1][0]), f"la barra se repite en la página 2: {paginas[1][0]}"
    for numero, (_, texts) in enumerate(paginas, 1):
        assert texts, f"la página {numero} está en blanco"

    # Page 2 starts at the configured left margin, not at the old 7cm bar
    # margin; the rest of the page (and later pages) use the full text width.
    # Glyph widths are not parsed here: the manual report checks the right edge
    # with `pdftotext -bbox`.
    textos_p2 = paginas[1][1]
    x_min = min(x for x, _ in textos_p2)
    margen_izq = prefs.load()["margins"]["left"]
    assert abs(x_min - margen_izq * CM_PT) < 0.5, (
        f"la página 2 empieza en x={x_min}, esperado {margen_izq * CM_PT}"
    )
    assert x_min < 7 * CM_PT - 10, f"la página 2 sigue usando el margen de 7cm (x={x_min})"


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
    # The afterpage block runs at \end{document}: it must not add a blank page.
    assert _pdf_page_count(resultado["pdf"]) == 1


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
