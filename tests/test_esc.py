# -*- coding: utf-8 -*-
"""latex_gen.esc: macros de ~ y ^, especiales escapados y no-ASCII intacto."""


import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import latex_gen  # noqa: E402


def test_esc_tilde_y_circunflejo_generan_macros():
    assert latex_gen.esc("a~b") == "a\\textasciitilde{}b"
    assert latex_gen.esc("a^b") == "a\\textasciicircum{}b"
    assert latex_gen.esc("~") == "\\textasciitilde{}"
    assert latex_gen.esc("^") == "\\textasciicircum{}"


def test_esc_especiales_clasicos():
    assert latex_gen.esc("\\") == "\\\\"
    assert latex_gen.esc("{") == "\\{"
    assert latex_gen.esc("}") == "\\}"
    assert latex_gen.esc("$") == "\\$"
    assert latex_gen.esc("&") == "\\&"
    assert latex_gen.esc("#") == "\\#"
    assert latex_gen.esc("_") == "\\_"
    assert latex_gen.esc("%") == "\\%"


def test_esc_acentos_y_cjk_intactos():
    assert latex_gen.esc("áéíóúÁÉÍÓÚñÑü") == "áéíóúÁÉÍÓÚñÑü"
    assert latex_gen.esc("Línea de prueba ¿qué?") == "Línea de prueba ¿qué?"
    assert latex_gen.esc("张伟的个人简历") == "张伟的个人简历"


def test_esc_combinado():
    assert latex_gen.esc("100% ~ 20^2") == "100\\% \\textasciitilde{} 20\\textasciicircum{}2"
    assert latex_gen.esc("a_b & c#d $e$ {f}") == "a\\_b \\& c\\#d \\$e\\$ \\{f\\}"


def test_esc_vacio():
    assert latex_gen.esc("") == ""
    assert latex_gen.esc(None) == ""


def test_palabra_larga_no_parte_los_macros():
    # 17 letras + "~" caben en el primer trozo de 18: el macro nunca se corta.
    palabra = "a" * 17 + "~b"
    assert latex_gen.esc(palabra) == "a" * 17 + "\\textasciitilde{}\\allowbreak b"


def test_palabra_larga_sin_especiales_se_parte_con_allowbreak():
    palabra = "b" * 20
    assert latex_gen.esc(palabra) == "b" * 18 + "\\allowbreak " + "b" * 2
