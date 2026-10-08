# -*- coding: utf-8 -*-
"""Generacion de curriculums en formato DOCX con python-docx.

No depende de LaTeX ni de pywebview: solo de python-docx y de la tabla de
traduccion (LANG) de latex_gen.
"""

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from latex_gen import LANG

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


def _encabezado(doc, titulo):
    """Titulo de seccion en negrita, dos puntos mayor que la fuente normal."""
    parrafo = doc.add_paragraph()
    run = parrafo.add_run(titulo)
    run.bold = True
    tamano = doc.styles["Normal"].font.size
    base = tamano.pt if tamano is not None else FUENTE_DEFECTO
    run.font.size = Pt(base + 2)
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


def _seccion_habilidades(doc, d, L):
    entradas = [e for e in (d.get("habilidades") or []) if isinstance(e, dict)]
    filas = []
    for e in entradas:
        categoria = _texto(e.get("categoria"))
        valores = [v.strip() for v in str(e.get("valores") or "").split(",") if v.strip()]
        if categoria or valores:
            filas.append((categoria, valores))
    if not filas:
        return
    _encabezado(doc, L["habilidades"])
    for categoria, valores in filas:
        parrafo = doc.add_paragraph()
        if categoria and valores:
            parrafo.add_run(categoria + L["sep_hab"] + " ").bold = True
            parrafo.add_run(", ".join(valores))
        elif categoria:
            parrafo.add_run(categoria).bold = True
        else:
            parrafo.add_run(", ".join(valores))


def _seccion_parejas(doc, entradas, L, clave, campo_a, campo_b):
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
    _encabezado(doc, L[clave])
    for a, b in filas:
        parrafo = doc.add_paragraph()
        if a and b:
            parrafo.add_run(a).bold = True
            parrafo.add_run(" – " + b)
        elif a:
            parrafo.add_run(a).bold = True
        else:
            parrafo.add_run(b)


def _cuerpo(doc, d, L):
    """Secciones en el mismo orden que latex_gen.build_tex, a una columna."""
    perfil = _texto(d.get("perfil"))
    if perfil:
        _encabezado(doc, L["perfil"])
        _parrafos(doc, d.get("perfil"))

    educacion = _entradas_con_contenido(d.get("educacion"))
    if educacion:
        _encabezado(doc, L["educacion"])
        for ent in educacion:
            _entrada_educacion(doc, ent, L)

    proyectos = _entradas_con_contenido(d.get("proyectos"))
    if proyectos:
        _encabezado(doc, L["proyectos"])
        for ent in proyectos:
            _entrada_proyecto(doc, ent, L, False)

    proyectosu = _entradas_con_contenido(d.get("proyectosu"))
    if proyectosu:
        _encabezado(doc, L["proyectosu"])
        for ent in proyectosu:
            _entrada_proyecto(doc, ent, L, True)

    pasantia = _entradas_con_contenido(d.get("pasantia"))
    if pasantia:
        _encabezado(doc, L["pasantia"])
        for ent in pasantia:
            _entrada_trabajo(doc, ent, L)

    trabajo = _entradas_con_contenido(d.get("trabajo"))
    if trabajo:
        _encabezado(doc, L["trabajo"])
        for ent in trabajo:
            _entrada_trabajo(doc, ent, L)

    _seccion_habilidades(doc, d, L)
    _seccion_parejas(doc, d.get("idiomas"), L, "idiomas", "idioma", "nivel")
    _seccion_parejas(doc, d.get("referencias"), L, "referencias", "nombre", "contacto")


def exportar(datos, prefs_dict, ruta):
    """Exporta `datos` a un fichero DOCX en `ruta`.

    `prefs_dict` usa las mismas claves que prefs.load(): papel, margenes y
    fuente. Las columnas de las secciones degradan a una sola columna.
    """
    datos = datos or {}
    L = LANG.get(str(datos.get("idioma_cv", "zh")), LANG["zh"])
    doc = Document()
    _configurar_documento(doc, prefs_dict or {})
    _cabecera(doc, datos, L)
    _cuerpo(doc, datos, L)
    doc.save(ruta)
