# -*- coding: utf-8 -*-
"""Comprobaciones estaticas del frontend, sin navegador ni pywebview.

La verificacion de integracion incluye `node --check web/app.js` para validar
la sintaxis del frontend; esta suite no ejecuta Node: solo comprueba que
web/index.html y web/app.js contienen la estructura y los manejadores que el
pipeline espera (menu Anadir, modales de bloques, deshacer/rehacer y zoom).
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_HTML = os.path.join(RAIZ, "web", "index.html")
RUTA_JS = os.path.join(RAIZ, "web", "app.js")
RUTA_CSS = os.path.join(RAIZ, "web", "style.css")


def _leer(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()


HTML = _leer(RUTA_HTML)
JS = _leer(RUTA_JS)
CSS = _leer(RUTA_CSS)


def test_index_tiene_menu_anadir_con_las_acciones_de_bloque():
    assert '<button class="menu-btn">Añadir</button>' in HTML
    for accion in (
        'data-accion="bloque:linea"',
        'data-accion="bloque:banda"',
        'data-accion="bloque:espacio"',
        'data-accion="bloque:seccion"',
        'data-accion="bloques:gestion"',
    ):
        assert accion in HTML, accion


def test_index_tiene_acciones_de_historial_y_zoom():
    for accion in (
        'data-accion="deshacer"',
        'data-accion="rehacer"',
        'data-accion="zoom:75"',
        'data-accion="zoom:100"',
        'data-accion="zoom:125"',
    ):
        assert accion in HTML, accion


def test_index_tiene_modales_de_bloques_con_sus_ids():
    assert 'id="modal-bloque-seccion"' in HTML
    for id_campo in ("bs-titulo", "bs-contenido", "bs-aceptar", "bs-cancelar"):
        assert 'id="%s"' % id_campo in HTML, id_campo
    assert 'id="modal-bloques"' in HTML
    assert 'id="bloques-lista"' in HTML
    assert 'id="bloques-cerrar"' in HTML


def test_app_js_genera_ids_de_bloque_con_uuid_o_respaldo_hex():
    assert "crypto.randomUUID" in JS
    # Respaldo cuando crypto.randomUUID no esta disponible.
    assert "0123456789abcdef" in JS


def test_app_js_tiene_deshacer_rehacer_y_registro_de_historial():
    assert "function registrarHistorial(" in JS
    assert "function deshacer(" in JS
    assert "function rehacer(" in JS
    assert "ctrlKey" in JS
    # Atajos Ctrl+Z / Ctrl+Y (o Ctrl+Shift+Z) enganchados al historial.
    assert 'k === "z"' in JS
    assert 'k === "y"' in JS


def test_app_js_aplica_zoom_al_visor_pdf():
    assert '"#zoom="' in JS
    assert '"&view=FitH"' in JS


def test_app_js_muta_bloques_en_un_unico_punto():
    assert "function mutarBloques(" in JS
    assert "function moverBloque(" in JS
    assert "function crearBloqueSeparador(" in JS


def test_app_js_tiene_botones_de_duplicar_y_mover_entradas():
    assert '"Duplicar entrada"' in JS
    assert '"Subir entrada"' in JS
    assert '"Bajar entrada"' in JS


def test_app_js_tiene_estado_de_colapso_por_seccion():
    assert "colapsoUI" in JS
    assert "function aplicarColapso(" in JS
    assert "function alternarColapso(" in JS


def _cuerpo_funcion(nombre):
    """Devuelve el cuerpo de una funcion top-level (cierre '}' en columna 0)."""
    m = re.search(r"function %s\([^)]*\) \{(.*?)\n\}" % nombre, JS, re.S)
    assert m, "no se encontró la función %s" % nombre
    return m.group(1)


def test_app_js_render_formulario_recrea_form_panel_si_falta():
    """Regresión: volver del modo LaTeX crasheaba con #form-panel a null."""
    cuerpo = _cuerpo_funcion("renderFormulario")
    assert 'let cont = $("#form-panel");' in cuerpo
    assert "if (!cont) {" in cuerpo
    assert 'document.createElement("div")' in cuerpo
    assert 'cont.id = "form-panel"' in cuerpo
    assert "host.appendChild(cont)" in cuerpo


def test_app_js_entrar_modo_latex_no_destruye_el_formulario():
    """entrarModoLatex oculta #form-panel en vez de vaciar #panel-formulario."""
    cuerpo = _cuerpo_funcion("entrarModoLatex")
    assert 'form.innerHTML = ""' not in cuerpo
    assert "panelForm.hidden = true" in cuerpo
    # Se elimina cualquier #panel-latex previo para no duplicar ids.
    assert '$("#panel-latex")' in cuerpo
    assert "host.appendChild(cont)" in cuerpo


def test_app_js_salir_modo_latex_restaura_form_panel():
    """salirModoLatex quita #panel-latex, muestra #form-panel y repinta."""
    cuerpo = _cuerpo_funcion("salirModoLatex")
    assert 'const pl = $("#panel-latex");' in cuerpo
    assert "pl.remove()" in cuerpo
    assert "panelForm.hidden = false" in cuerpo
    assert "renderFormulario()" in cuerpo
    # El estado de edición manual se restablece al volver.
    assert "state.texManual = null" in cuerpo
    assert "state.texEditado = false" in cuerpo


def _bloque_css(selector):
    """Devuelve el cuerpo de la regla CSS del selector exacto."""
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    assert m, "no se encontró la regla %s en web/style.css" % selector
    return m.group(1)


def test_css_panel_latex_ocupa_la_altura_disponible():
    """Regresión: #panel-latex solo medía su altura intrínseca dentro del
    contenedor flex de #panel-formulario, así que el textarea quedaba en ~2
    filas. Debe crecer con `flex: 1 1 auto` y el textarea estirarse y
    desplazarse internamente (min-height: 0)."""
    assert "flex: 1 1 auto" in _bloque_css("#panel-latex")
    bloque_texto = _bloque_css("#texto-latex")
    assert "flex: 1 1 auto" in bloque_texto
    assert "min-height: 0" in bloque_texto

