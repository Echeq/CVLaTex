# -*- coding: utf-8 -*-
"""Motor LaTeX: deteccion de XeLaTeX (CJK o fontspec) y compilacion zh vacia.

``_uses_xelatex`` debe devolver True tanto para texto CJK como para cualquier
documento que cargue fontspec: pdflatex aborta con "fontspec requires XeTeX
or LuaTeX" aunque no haya ni un caracter CJK (p. ej. un CV vacio en zh, cuyo
font_engine emite fontspec). La compilacion real usa el mismo patron skipif
de test_roundtrip_tex.py.
"""

import os
import re
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_engine  # noqa: E402
import latex_gen  # noqa: E402
import prefs  # noqa: E402

MOTOR_PDF = latex_engine.find_pdflatex()
MOTOR_CJK = latex_engine.find_xelatex()

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


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


def _pdf_contains(pdf_path, needle):
    """True when the raw PDF or any decompressed stream contains `needle`."""
    with open(pdf_path, "rb") as f:
        data = f.read()
    if needle in data:
        return True
    for match in re.finditer(rb"stream\r?\n", data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end == -1:
            continue
        try:
            stream = zlib.decompress(data[start:end].rstrip(b"\r\n"))
        except zlib.error:
            continue
        if needle in stream:
            return True
    return False


def test_detector_fontspec_solo_necesita_xelatex():
    tex = (
        "\\documentclass{article}\n"
        "\\usepackage{fontspec}\n"
        "\\setmainfont{Microsoft YaHei}\n"
        "\\begin{document}No CJK here\\end{document}"
    )
    assert latex_engine._uses_xelatex(tex) is True


def test_detector_fontspec_con_opciones():
    tex = "\\documentclass{article}\n\\usepackage[no-math]{fontspec}\n\\begin{document}x\\end{document}"
    assert latex_engine._uses_xelatex(tex) is True


def test_detector_lmodern_no_necesita_xelatex():
    tex = (
        "\\documentclass{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage{lmodern}\n"
        "\\begin{document}Hola, sin CJK ni fontspec.\\end{document}"
    )
    assert latex_engine._uses_xelatex(tex) is False


def test_detector_cjk_sigue_necesitando_xelatex():
    tex = "\\documentclass{article}\n\\begin{document}张伟\\end{document}"
    assert latex_engine._uses_xelatex(tex) is True


@pytest.mark.skipif(
    MOTOR_PDF is None or MOTOR_CJK is None,
    reason="Sin motores LaTeX (pdflatex/xelatex) instalados",
)
def test_compila_cv_vacia_zh_sidebar_via_xelatex(prefs_tmp):
    """The CV that used to abort with "fontspec requires XeTeX" now compiles.

    empty_data() is zh by default (fontspec in the preamble) and the sidebar
    header omits the CJK title, so the document contains no CJK character at
    all: the detector must switch to XeLaTeX because of fontspec.
    """
    datos = latex_gen.empty_data()
    datos["template"] = "sidebar"
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "\\usepackage{fontspec}" in tex
    assert not _CJK_RE.search(tex)
    assert latex_engine._uses_xelatex(tex) is True

    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])
    # Evidence of the engine actually used: xdvipdfmx/XeTeX metadata.
    assert _pdf_contains(resultado["pdf"], b"XeTeX")
