# -*- coding: utf-8 -*-
"""Generacion de curriculums en formato DOCX con python-docx.

No depende de LaTeX ni de pywebview: solo de python-docx y de los helpers de
latex_gen (tabla de traduccion LANG, orden/visibilidad/titulos de seccion).
"""

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import latex_gen
from latex_gen import ANCLAS_BLOQUE, ESTILOS_SEPARADOR, LANG, MODOS_LISTADO

# Tamano de pagina en centimetros: (ancho, alto).
PAPELES = {
    "a4": (21.0, 29.7),
    "letter": (21.59, 27.94),
    "legal": (21.59, 35.56),
}

# Extensiones de imagen admitidas para la foto.
FOTO_EXTS = {".jpg", ".jpeg", ".png"}

MARGEN_DEFECTO = 2.0
FUENTE_DEFECTO = 11.0
TAMANO_NOMBRE = 20.0
ANCHO_FOTO_DEFECTO = 4.0

# Azul de acento de la plantilla clasica (color por defecto del CV): se usa
# en los bordes y bandas de los separadores de bloques libres.
COLOR_ACENTO = "233A5E"


def _texto(valor):
    """Devuelve el valor como texto sin espacios sobrantes."""
    if valor is None:
        return ""
    return str(valor).strip()


def _num(valor, defecto):
    """Convierte a float y cae al valor por defecto si no es numerico."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(defecto)


def _rgb_de_hex(valor):
    """Normaliza "#RGB" o "#RRGGBB" a RGBColor.

    Acepta mayusculas y minusculas, recorta los espacios de fuera y expande
    la forma corta duplicando cada digito (#ABC -> #AABBCC). Cualquier otro
    valor (incluido lo que no sea str) cae a None; nunca lanza.
    """
    if not isinstance(valor, str):
        return None
    texto = valor.strip()
    if not texto.startswith("#"):
        return None
    hexa = texto[1:]
    if len(hexa) == 3 and all(c in "0123456789abcdefABCDEF" for c in hexa):
        hexa = "".join(c * 2 for c in hexa)
    if len(hexa) != 6 or any(c not in "0123456789abcdefABCDEF" for c in hexa):
        return None
    try:
        return RGBColor(int(hexa[0:2], 16), int(hexa[2:4], 16), int(hexa[4:6], 16))
    except (TypeError, ValueError):
        return None


def _color_prefs(prefs_dict, clave):
    """Color RGBColor de prefs["colores"][clave]; vacio o invalido -> None."""
    try:
        colores = prefs_dict.get("colores") if isinstance(prefs_dict, dict) else None
        if not isinstance(colores, dict):
            return None
        return _rgb_de_hex(colores.get(clave))
    except Exception:
        return None


def _hex_de_color(color):
    """RGBColor o "#RRGGBB" -> "RRGGBB"; None o invalido -> None."""
    if isinstance(color, RGBColor):
        return str(color)
    rgb = _rgb_de_hex(color)
    return str(rgb) if rgb is not None else None


def _color_rgb(color):
    """Normaliza el parametro color a RGBColor; None o invalido -> None."""
    if isinstance(color, RGBColor):
        return color
    return _rgb_de_hex(color)


def _entradas_con_contenido(lista):
    """Filtra entradas vacias, igual que hace latex_gen con las secciones."""
    if not isinstance(lista, (list, tuple)):
        return []
    return [e for e in lista if _tiene_contenido(e)]


def _tiene_contenido(entrada):
    if not isinstance(entrada, dict):
        return bool(_texto(entrada))
    return any(_texto(v) for v in entrada.values())


def _rango(desde, hasta):
    desde = _texto(desde)
    hasta = _texto(hasta)
    if desde and hasta:
        return f"{desde} – {hasta}"
    return desde or hasta


def _parrafos(doc, texto):
    """Anade un parrafo por cada linea no vacia (descripciones y perfil)."""
    for linea in str(texto or "").splitlines():
        linea = linea.strip()
        if linea:
            doc.add_paragraph(linea)


def _vineta(doc, texto):
    """Vineta simple; si la plantilla no tiene el estilo, usa un prefijo."""
    try:
        doc.add_paragraph(texto, style="List Bullet")
    except Exception:
        doc.add_paragraph("• " + texto)


def _encabezado(doc, titulo, color=None):
    """Titulo de seccion en negrita, dos puntos mayor que la fuente normal.

    ``color`` (RGBColor) tiñe el titulo; None conserva el color por defecto.
    """
    parrafo = doc.add_paragraph()
    run = parrafo.add_run(titulo)
    run.bold = True
    tamano = doc.styles["Normal"].font.size
    base = tamano.pt if tamano is not None else FUENTE_DEFECTO
    run.font.size = Pt(base + 2)
    rgb = _color_rgb(color)
    if rgb is not None:
        run.font.color.rgb = rgb
    return parrafo


def _parrafo_titulo(doc, desde, hasta, titulo):
    """Primera linea de una entrada: fecha en cursiva y titulo en negrita."""
    fecha = _rango(desde, hasta)
    titulo = _texto(titulo)
    if not fecha and not titulo:
        return None
    parrafo = doc.add_paragraph()
    if fecha:
        parrafo.add_run(fecha).italic = True
    if titulo:
        if fecha:
            parrafo.add_run("   ")
        parrafo.add_run(titulo).bold = True
    return parrafo


def _configurar_documento(doc, prefs_dict):
    """Tamano de pagina, margenes y fuente Normal segun prefs_dict."""
    p = prefs_dict or {}
    ancho, alto = PAPELES.get(str(p.get("papel") or "a4").lower(), PAPELES["a4"])
    seccion = doc.sections[0]
    seccion.page_width = Cm(ancho)
    seccion.page_height = Cm(alto)
    margenes = p.get("margenes") or {}
    seccion.top_margin = Cm(_num(margenes.get("top"), MARGEN_DEFECTO))
    seccion.bottom_margin = Cm(_num(margenes.get("bottom"), MARGEN_DEFECTO))
    seccion.left_margin = Cm(_num(margenes.get("left"), MARGEN_DEFECTO))
    seccion.right_margin = Cm(_num(margenes.get("right"), MARGEN_DEFECTO))
    doc.styles["Normal"].font.size = Pt(_num(p.get("fuente"), FUENTE_DEFECTO))


def _agregar_contactos(doc, d, L):
    """Linea de contactos con las etiquetas traducidas de LANG; omite vacios."""
    piezas = []

    def agregar(etiqueta, valor):
        valor = _texto(valor)
        if valor:
            piezas.append((etiqueta, valor))

    agregar(L["nacimiento"], d.get("nacimiento"))
    agregar(L["telefono"], d.get("telefono"))
    agregar(L["nacionalidad"], d.get("nacionalidad"))
    agregar(L["correo"], d.get("email"))
    agregar(L["direccion"], d.get("direccion"))
    agregar(L["egresado"], d.get("institucion_egresado"))
    agregar(L["puesto"], d.get("profesion"))
    agregar(L["github"], d.get("github"))
    agregar(L["linkedin"], d.get("linkedin"))
    agregar("Web:", d.get("web"))
    for x in d.get("datos_extra") or []:
        x = x or {}
        etiqueta = _texto(x.get("etiqueta"))
        valor = _texto(x.get("valor"))
        if etiqueta and valor:
            piezas.append((etiqueta + ":", valor))
    if not piezas:
        return
    parrafo = doc.add_paragraph()
    for i, (etiqueta, valor) in enumerate(piezas):
        if i:
            parrafo.add_run("   |   ")
        run = parrafo.add_run(etiqueta + " ")
        run.bold = True
        parrafo.add_run(valor)


def _agregar_foto(doc, d):
    """Inserta la foto si es un fichero valido; ignora cualquier fallo."""
    foto = _texto(d.get("foto"))
    if not foto:
        return
    if os.path.splitext(foto)[1].lower() not in FOTO_EXTS or not os.path.isfile(foto):
        return
    try:
        ancho = float(d.get("foto_ancho_cm") or ANCHO_FOTO_DEFECTO)
        parrafo = doc.add_paragraph()
        parrafo.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        parrafo.add_run().add_picture(foto, width=Cm(ancho))
    except Exception:
        # Cualquier fallo de imagen se ignora: la exportacion nunca se rompe.
        pass


def _cabecera(doc, d, L):
    parrafo = doc.add_paragraph()
    run = parrafo.add_run(_texto(d.get("nombre")))
    run.bold = True
    run.font.size = Pt(TAMANO_NOMBRE)
    profesion = _texto(d.get("profesion"))
    if profesion:
        doc.add_paragraph().add_run(profesion).italic = True
    _agregar_contactos(doc, d, L)
    _agregar_foto(doc, d)


def _entrada_educacion(doc, ent, L):
    tipo = _texto(ent.get("tipo"))
    titulo = _texto(ent.get("titulo"))
    rotulo = " — ".join(x for x in (tipo, titulo) if x)
    _parrafo_titulo(doc, ent.get("desde"), ent.get("hasta"), rotulo)
    institucion = _texto(ent.get("institucion"))
    if institucion:
        doc.add_paragraph().add_run(institucion).italic = True
    nota = _texto(ent.get("nota"))
    if nota:
        parrafo = doc.add_paragraph()
        parrafo.add_run(_texto(L["nota"]) + " ").bold = True
        parrafo.add_run(nota)


def _entrada_trabajo(doc, ent, L):
    _parrafo_titulo(doc, ent.get("desde"), ent.get("hasta"), ent.get("puesto"))
    empresa = _texto(ent.get("empresa"))
    if empresa:
        doc.add_paragraph().add_run(empresa).italic = True
    modalidad = _texto(ent.get("modalidad"))
    if modalidad:
        doc.add_paragraph().add_run("(" + modalidad + ")")
    logros = [x.strip() for x in str(ent.get("logros") or "").splitlines() if x.strip()]
    for logro in logros:
        _vineta(doc, logro)


def _entrada_proyecto(doc, ent, L, con_asignatura):
    _parrafo_titulo(doc, ent.get("desde"), ent.get("hasta"), ent.get("nombre"))
    organizacion = _texto(ent.get("organizacion"))
    asignatura = _texto(ent.get("asignatura")) if con_asignatura else ""
    if organizacion or asignatura:
        parrafo = doc.add_paragraph()
        if organizacion:
            parrafo.add_run(organizacion).italic = True
        if asignatura:
            if organizacion:
                parrafo.add_run("   ")
            parrafo.add_run(asignatura)
    _parrafos(doc, ent.get("descripcion"))
    resultado = _texto(ent.get("resultado"))
    if resultado:
        parrafo = doc.add_paragraph()
        parrafo.add_run(_texto(L["resultado"]) + " ").bold = True
        parrafo.add_run(resultado)
    enlace = _texto(ent.get("enlace"))
    if enlace:
        parrafo = doc.add_paragraph()
        parrafo.add_run(_texto(L["enlace"]) + " ").bold = True
        parrafo.add_run(enlace)


def _seccion_habilidades(doc, d, L, titulo=None, color=None):
    entradas = [e for e in (d.get("habilidades") or []) if isinstance(e, dict)]
    filas = []
    for e in entradas:
        categoria = _texto(e.get("categoria"))
        valores = [v.strip() for v in str(e.get("valores") or "").split(",") if v.strip()]
        if categoria or valores:
            filas.append((categoria, valores))
    if not filas:
        return
    _encabezado(doc, titulo or L["habilidades"], color)
    for categoria, valores in filas:
        parrafo = doc.add_paragraph()
        if categoria and valores:
            parrafo.add_run(categoria + L["sep_hab"] + " ").bold = True
            parrafo.add_run(", ".join(valores))
        elif categoria:
            parrafo.add_run(categoria).bold = True
        else:
            parrafo.add_run(", ".join(valores))


def _seccion_parejas(doc, entradas, L, clave, campo_a, campo_b, titulo=None, color=None):
    filas = []
    for e in entradas or []:
        if not isinstance(e, dict):
            continue
        a = _texto(e.get(campo_a))
        b = _texto(e.get(campo_b))
        if a or b:
            filas.append((a, b))
    if not filas:
        return
    _encabezado(doc, titulo or L[clave], color)
    for a, b in filas:
        parrafo = doc.add_paragraph()
        if a and b:
            parrafo.add_run(a).bold = True
            parrafo.add_run(" – " + b)
        elif a:
            parrafo.add_run(a).bold = True
        else:
            parrafo.add_run(b)


def _ancla_bloque(valor):
    """Ancla valida o "final" para un bloque con posicion ausente o desconocida."""
    ancla = _texto(valor)
    return ancla if ancla in ANCLAS_BLOQUE else "final"


def _agrupar_bloques(d):
    """Reparte los bloques libres por ancla; ignora lo que no sea diccionario."""
    grupos = {ancla: [] for ancla in ANCLAS_BLOQUE}
    entradas = d.get("bloques")
    if not isinstance(entradas, (list, tuple)):
        return grupos
    for bloque in entradas:
        if isinstance(bloque, dict):
            grupos[_ancla_bloque(bloque.get("posicion"))].append(bloque)
    return grupos


def _borde_inferior(parrafo, color, grosor=6):
    """Anade el borde inferior XML (w:pBdr) al parrafo indicado."""
    p_pr = parrafo._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    inferior = OxmlElement("w:bottom")
    inferior.set(qn("w:val"), "single")
    inferior.set(qn("w:sz"), str(grosor))
    inferior.set(qn("w:space"), "1")
    inferior.set(qn("w:color"), color)
    p_bdr.append(inferior)
    p_pr.append(p_bdr)


def _sombreado(parrafo, color):
    """Anade el sombreado XML (w:shd) al parrafo indicado."""
    p_pr = parrafo._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    p_pr.append(shd)


def _separador_linea(doc, color=None):
    """Separador fino: parrafo vacio con borde inferior en el color de acento."""
    parrafo = doc.add_paragraph()
    _borde_inferior(parrafo, _hex_de_color(color) or COLOR_ACENTO)
    return parrafo


def _separador_banda(doc, color=None):
    """Separador ancho: parrafo vacio sombreado con el color de acento."""
    hexa = _hex_de_color(color) or COLOR_ACENTO
    parrafo = doc.add_paragraph()
    _borde_inferior(parrafo, hexa, grosor=24)
    _sombreado(parrafo, hexa)
    return parrafo


def _bloque_separador(doc, bloque, color=None):
    """Un separador siempre se dibuja; un estilo desconocido cae a "linea"."""
    estilo = _texto(bloque.get("estilo"))
    if estilo not in ESTILOS_SEPARADOR:
        estilo = "linea"
    if estilo == "banda":
        _separador_banda(doc, color)
    elif estilo == "espacio":
        doc.add_paragraph()
    else:
        _separador_linea(doc, color)


def _bloque_seccion(doc, bloque, color=None):
    """Titulo en negrita y contenido por lineas; se omite solo si esta todo vacio."""
    titulo = _texto(bloque.get("titulo"))
    if not titulo and not _texto(bloque.get("contenido")):
        return
    if titulo:
        _encabezado(doc, titulo, color)
    _parrafos(doc, bloque.get("contenido"))


def _bloque_listado(doc, bloque, color=None):
    """Lista generica: pares titulo/detalle o periodo/descripcion.

    Las columnas del bloque degradan a una sola columna (igual que el resto
    de secciones con ``columnas`` en la exportacion Word).
    """
    modo = _texto(bloque.get("modo"))
    if modo not in MODOS_LISTADO:
        modo = "columnas"
    titulo = _texto(bloque.get("titulo"))
    entradas = bloque.get("entradas")
    filas = []
    for ent in entradas if isinstance(entradas, (list, tuple)) else []:
        if not isinstance(ent, dict):
            continue
        if modo == "periodo":
            periodo = _texto(ent.get("periodo"))
            descripcion = _texto(ent.get("descripcion"))
            if periodo or descripcion:
                filas.append((periodo, descripcion))
        else:
            encabezado = _texto(ent.get("titulo"))
            detalle = _texto(ent.get("detalle"))
            if encabezado or detalle:
                filas.append((encabezado, detalle))
    if not filas:
        return
    if titulo:
        _encabezado(doc, titulo, color)
    for a, b in filas:
        if modo == "periodo":
            if a:
                doc.add_paragraph().add_run(a).italic = True
            if b:
                doc.add_paragraph(b)
        else:
            parrafo = doc.add_paragraph()
            if a and b:
                parrafo.add_run(a).bold = True
                parrafo.add_run(" --- " + b)
            elif a:
                parrafo.add_run(a).bold = True
            else:
                parrafo.add_run(b)


def _render_bloques(doc, bloques, color=None):
    """Dibuja los bloques de un ancla en el mismo orden de la lista."""
    for bloque in bloques:
        if not isinstance(bloque, dict):
            continue
        tipo = _texto(bloque.get("tipo"))
        if tipo == "separador":
            _bloque_separador(doc, bloque, color)
        elif tipo == "seccion":
            _bloque_seccion(doc, bloque, color)
        elif tipo == "listado":
            _bloque_listado(doc, bloque, color)


def _cuerpo(doc, d, L, color=None):
    """Secciones con el mismo orden, visibilidad y titulos que latex_gen.

    El orden normalizado y las secciones ocultas se delegan en latex_gen
    (normalizar_orden_secciones / seccion_oculta) y los titulos personalizados
    en titulo_personalizado, con L[clave] como respaldo. El texto va en plano,
    sin escapado LaTeX. ``color`` (RGBColor) tiñe los encabezados; None los
    deja con el color por defecto.

    Los bloques libres se intercalan tras su seccion ancla; las anclas
    "inicio" y "final" abren y cierran el cuerpo. Una seccion vacia u oculta
    sigue mostrando los bloques anclados a ella (ancla posicional).
    """
    grupos = _agrupar_bloques(d)
    _render_bloques(doc, grupos["inicio"], color)

    for clave in latex_gen.normalizar_orden_secciones(d):
        if not latex_gen.seccion_oculta(d, clave):
            titulo = latex_gen.titulo_personalizado(d, clave) or L[clave]
            if clave == "perfil":
                if _texto(d.get("perfil")):
                    _encabezado(doc, titulo, color)
                    _parrafos(doc, d.get("perfil"))
            elif clave == "educacion":
                entradas = _entradas_con_contenido(d.get("educacion"))
                if entradas:
                    _encabezado(doc, titulo, color)
                    for ent in entradas:
                        _entrada_educacion(doc, ent, L)
            elif clave == "proyectos":
                entradas = _entradas_con_contenido(d.get("proyectos"))
                if entradas:
                    _encabezado(doc, titulo, color)
                    for ent in entradas:
                        _entrada_proyecto(doc, ent, L, False)
            elif clave == "proyectosu":
                entradas = _entradas_con_contenido(d.get("proyectosu"))
                if entradas:
                    _encabezado(doc, titulo, color)
                    for ent in entradas:
                        _entrada_proyecto(doc, ent, L, True)
            elif clave == "pasantia":
                entradas = _entradas_con_contenido(d.get("pasantia"))
                if entradas:
                    _encabezado(doc, titulo, color)
                    for ent in entradas:
                        _entrada_trabajo(doc, ent, L)
            elif clave == "trabajo":
                entradas = _entradas_con_contenido(d.get("trabajo"))
                if entradas:
                    _encabezado(doc, titulo, color)
                    for ent in entradas:
                        _entrada_trabajo(doc, ent, L)
            elif clave == "habilidades":
                _seccion_habilidades(doc, d, L, titulo, color)
            elif clave == "idiomas":
                _seccion_parejas(doc, d.get("idiomas"), L, clave, "idioma", "nivel", titulo, color)
            elif clave == "referencias":
                _seccion_parejas(doc, d.get("referencias"), L, clave, "nombre", "contacto", titulo, color)
        # Bloque anclado a esta seccion: se emite aunque la seccion este oculta
        # o vacia, para conservar el ancla posicional elegida.
        _render_bloques(doc, grupos[clave], color)
    _render_bloques(doc, grupos["final"], color)


def exportar(datos, prefs_dict, ruta):
    """Exporta `datos` a un fichero DOCX en `ruta`.

    `prefs_dict` usa las mismas claves que prefs.load(): papel, margenes,
    fuente y colores (primario y texto). Las columnas de las secciones
    degradan a una sola columna.
    """
    datos = datos or {}
    L = LANG.get(str(datos.get("idioma_cv", "zh")), LANG["zh"])
    doc = Document()
    _configurar_documento(doc, prefs_dict or {})
    # texto -> color base del estilo Normal; primario -> separadores y titulos.
    color_texto = _color_prefs(prefs_dict, "texto")
    if color_texto is not None:
        doc.styles["Normal"].font.color.rgb = color_texto
    _cabecera(doc, datos, L)
    _cuerpo(doc, datos, L, _color_prefs(prefs_dict, "primario"))
    doc.save(ruta)
