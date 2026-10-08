import os
import re
import sys

import tex_datos

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

PLANTILLAS = ("clasico", "harvard", "moderno", "creativo", "chino")
ARCHIVOS = {
    "clasico": "clasico/plantilla.tex",
    "harvard": "harvard/harvard.tex",
    "moderno": "moderno/moderno.tex",
    "creativo": "creativo/creativo.tex",
    "chino": "chino/chino.tex",
}

_ESPECIALES = re.compile(r"([\\{}$&#^_%~])")
LOGO_EXTS = {".jpg", ".jpeg", ".png"}
ANCHOS = {1: "1.0", 2: "0.48", 3: "0.31"}

LANG = {
    "zh": {
        "titulo": "个人简历 PERSONAL RESUME",
        "nacimiento": "出生年月：", "telefono": "手机号码：", "nacionalidad": "国籍：",
        "correo": "邮箱：", "egresado": "毕业院校：", "puesto": "意向岗位：",
        "github": "Github: ", "linkedin": "Linkedin: ",
        "educacion": "教育背景", "proyectos": "项目经历", "proyectosu": "校内项目",
        "pasantia": "实习经历", "trabajo": "工作经历", "habilidades": "技能特长",
        "idiomas": "语言能力", "referencias": "推荐人", "perfil": "个人简介",
        "nota": "成绩：", "resultado": "成果：", "enlace": "Github: ",
        "sep_hab": "：",
    },
    "es": {
        "titulo": "CURRÍCULUM",
        "nacimiento": "Nacimiento:", "telefono": "Teléfono:", "nacionalidad": "Nacionalidad:",
        "correo": "Correo:", "egresado": "Institución de egreso:", "puesto": "Puesto deseado:",
        "github": "Github:", "linkedin": "Linkedin:",
        "educacion": "Educación", "proyectos": "Proyectos", "proyectosu": "Proyectos universitarios",
        "pasantia": "Pasantías", "trabajo": "Experiencia laboral", "habilidades": "Habilidades",
        "idiomas": "Idiomas", "referencias": "Referencias", "perfil": "Perfil",
        "nota": "Nota:", "resultado": "Resultado:", "enlace": "Github:",
        "sep_hab": ":",
    },
    "en": {
        "titulo": "PERSONAL RESUME",
        "nacimiento": "Date of birth:", "telefono": "Phone:", "nacionalidad": "Nationality:",
        "correo": "Email:", "egresado": "Graduated from:", "puesto": "Desired role:",
        "github": "Github:", "linkedin": "Linkedin:",
        "educacion": "Education", "proyectos": "Projects", "proyectosu": "University projects",
        "pasantia": "Internships", "trabajo": "Work experience", "habilidades": "Skills",
        "idiomas": "Languages", "referencias": "References", "perfil": "Profile",
        "nota": "Grade:", "resultado": "Result:", "enlace": "Github:",
        "sep_hab": ":",
    },
}


def esc(texto):
    if not texto:
        return ""
    t = _ESPECIALES.sub(r"\\\1", str(texto))
    return " ".join(_partir_palabra(p) for p in t.split(" "))


def _partir_palabra(pal):
    if len(pal) <= 18:
        return pal
    trozos = [pal[i:i + 18] for i in range(0, len(pal), 18)]
    return "\\allowbreak ".join(trozos)


def datos_vacios():
    return {
        "idioma_cv": "zh",
        "plantilla": "clasico",
        "nombre": "", "profesion": "", "email": "", "telefono": "",
        "direccion": "", "web": "", "nacimiento": "", "nacionalidad": "",
        "github": "", "linkedin": "",
        "datos_extra": [],
        "foto": "", "foto_original": "", "foto_recorte": None,
        "foto_ancho_cm": 4.0, "foto_alto_cm": 5.0,
        "institucion_egresado": "", "logo_egresado": "",
        "logo_egresado_ancho_cm": 2.4, "logo_egresado_alto_cm": 0.85,
        "perfil": "",
        "trabajo": [],
        "pasantia": [],
        "proyectos": [],
        "proyectosu": [],
        "educacion": [],
        "habilidades": [],
        "idiomas": [],
        "referencias": [],
        "columnas": {"trabajo": 1, "pasantia": 1, "proyectos": 1, "proyectosu": 1, "educacion": 1},
    }


def logos_extra(data):
    extra = {}
    for clave in ("trabajo", "pasantia", "educacion", "proyectosu"):
        for i, ent in enumerate(data.get(clave) or []):
            logo = (ent or {}).get("logo")
            if logo and os.path.isfile(logo):
                ext = os.path.splitext(logo)[1].lower()
                if ext in LOGO_EXTS:
                    extra[f"logo_{clave}_{i}{ext}"] = logo
    logo = data.get("logo_egresado")
    if logo and os.path.isfile(logo):
        ext = os.path.splitext(logo)[1].lower()
        if ext in LOGO_EXTS:
            extra[f"logo_egresado{ext}"] = logo
    return extra


def _ref_logo(clave, i, ent):
    logo = (ent or {}).get("logo")
    if not logo or not os.path.isfile(logo):
        return None
    ext = os.path.splitext(logo)[1].lower()
    if ext not in LOGO_EXTS:
        return None
    return f"logo_{clave}_{i}{ext}"


def _con_logo(clave, i, ent, contenido):
    ref = _ref_logo(clave, i, ent)
    if not ref:
        return contenido
    return (
        "\\begin{minipage}[t]{1.15cm}\n"
        f"  \\includegraphics[width=\\linewidth,height=1.05cm,keepaspectratio]{{{ref}}}\n"
        "\\end{minipage}%\n"
        "\\begin{minipage}[t]{\\dimexpr\\linewidth-1.3cm\\relax}\n"
        f"{contenido}"
        "\\end{minipage}\n"
    )


def _caja(ancho, contenido):
    return (
        f"\\begin{{minipage}}[t]{{{ancho}\\linewidth}}\n"
        "\\raggedright\n"
        f"{contenido}"
        "\\end{minipage}"
    )


def _rango(desde, hasta):
    if desde and hasta:
        return f"{esc(desde)} -- {esc(hasta)}"
    return esc(desde) or esc(hasta)


def _itemize(lineas):
    items = "\n".join(f"\\item {l}" for l in lineas)
    return (
        "\\begin{itemize}\\setlength{\\itemsep}{1pt}\\setlength{\\parskip}{0pt}\\raggedright\n"
        f"{items}\n"
        "\\end{itemize}\n"
    )


def _parrafos(texto):
    lineas = [x.strip() for x in str(texto).splitlines() if x.strip()]
    if not lineas:
        return ""
    return "\\par\n".join(esc(x) for x in lineas) + "\n"


def _seccion(titulo, contenido):
    if not contenido.strip():
        return ""
    return f"\\cvsection{{{titulo}}}\n{contenido}\n"


def _linea_fecha(titulo, desde, hasta):
    fecha = _rango(desde, hasta)
    if fecha and titulo:
        return f"\\noindent{{\\itshape {fecha}}} \\hfill {{\\bfseries {titulo}}}"
    if fecha:
        return f"\\noindent{{\\itshape {fecha}}}"
    if titulo:
        return f"\\noindent{{\\bfseries {titulo}}}"
    return ""


def _contactos(d, L):
    lineas = []

    def ag(label, valor, mono=False):
        if not valor or not str(valor).strip():
            return
        v = str(valor).strip()
        texto = f"\\texttt{{{esc(v)}}}" if mono else esc(v)
        lineas.append(f"\\textbf{{{label}}} {texto}")

    ag(L["nacimiento"], d.get("nacimiento"))
    ag(L["telefono"], d.get("telefono"), mono=True)
    ag(L["nacionalidad"], d.get("nacionalidad"))
    ag(L["correo"], d.get("email"), mono=True)
    ag(L["egresado"], d.get("institucion_egresado"))
    ag(L["puesto"], d.get("profesion"))
    ag(L["github"], d.get("github"), mono=True)
    ag(L["linkedin"], d.get("linkedin"), mono=True)
    ag("Web:", d.get("web"), mono=True)
    for x in d.get("datos_extra") or []:
        x = x or {}
        et = str(x.get("etiqueta", "")).strip()
        v = str(x.get("valor", "")).strip()
        if et and v:
            lineas.append(f"\\textbf{{{esc(et)}:}} {esc(v)}")
    if not lineas:
        return ""
    return "{\\small\n" + " \\\\\n".join(lineas) + "\n\\par}"


def _datos_imagenes(d):
    ref_logo = None
    logo = d.get("logo_egresado")
    if logo and os.path.isfile(logo):
        ext = os.path.splitext(logo)[1].lower()
        if ext in LOGO_EXTS:
            ref_logo = f"logo_egresado{ext}"

    foto = d.get("foto")
    ext_foto = os.path.splitext(foto)[1].lower() if foto else ""
    hay_foto = bool(foto and os.path.exists(foto) and ext_foto in LOGO_EXTS)
    return ref_logo, hay_foto, ext_foto


def _piezas_imagen(d, ref_logo, hay_foto, ext_foto):
    piezas = []
    if ref_logo:
        try:
            lw = float(d.get("logo_egresado_ancho_cm") or 2.4)
            lh = float(d.get("logo_egresado_alto_cm") or 0.85)
        except (TypeError, ValueError):
            lw, lh = 2.4, 0.85
        lw = min(max(lw, 0.5), 6.0)
        lh = min(max(lh, 0.3), 4.0)
        piezas.append(
            f"\\noindent\\includegraphics[width={lw:g}cm,height={lh:g}cm,keepaspectratio]{{{ref_logo}}}\n"
        )
    if hay_foto:
        try:
            ancho = float(d.get("foto_ancho_cm") or 4.0)
            alto = float(d.get("foto_alto_cm") or 5.0)
        except (TypeError, ValueError):
            ancho, alto = 4.0, 5.0
        ancho = min(max(ancho, 1.0), 12.0)
        alto = min(max(alto, 1.0), 15.0)
        if ref_logo:
            piezas.append("\\vspace{0.15em}\n")
        piezas.append(
            "{\\setlength{\\fboxsep}{3pt}\n"
            f"\\fcolorbox{{gris}}{{white}}{{\\includegraphics[width={ancho:g}cm,height={alto:g}cm,keepaspectratio]{{foto{ext_foto}}}}}\n"
            "}\n"
        )
    return piezas


def _cabecera_clasico(d, L, piezas):
    titulo = f"{{\\small\\bfseries\\color{{gris}} {L['titulo']}}}\n"
    nombre = f"{{\\LARGE\\bfseries {esc(d.get('nombre', ''))}}}"
    contacto = _contactos(d, L)

    derecha = ""
    if piezas:
        derecha = (
            "\\begin{minipage}[t]{0.28\\textwidth}\n"
            "\\raggedleft\n"
            "\\vspace{0.5em}\n"
            + "".join(piezas)
            + "\\end{minipage}\n"
        )

    if derecha:
        fila = (
            "\\noindent\n"
            "\\begin{minipage}[t]{0.7\\textwidth}\n"
            f"  {titulo}\\par\n"
            f"  {nombre}\\par\n"
            "  \\vspace{0.4em}\n"
            f"  {contacto}\n"
            "\\end{minipage}%\n"
            f"\\hfill\n{derecha}"
        )
    else:
        fila = (
            "\\noindent\n"
            f"  {titulo}\\par\n"
            f"  {nombre}\\par\n"
            "  \\vspace{0.4em}\n"
            f"  {contacto}\n"
        )
    return fila + "\n\\vspace{0.3em}\n{\\color{accent}\\hrule height 0.8pt}\n"


def _cabecera_harvard(d, L, piezas):
    lineas = [
        "\\begin{center}\n",
        f"  {{\\small\\bfseries\\color{{gris}} {L['titulo']}}}\\par\n",
        "  \\vspace{0.3em}\n",
        f"  {{\\LARGE\\scshape {esc(d.get('nombre', ''))}}}\\par\n",
    ]
    contacto = _contactos(d, L)
    if contacto:
        lineas.append("  \\vspace{0.4em}\n")
        lineas.append("  " + contacto.replace("\n", "\n  ") + "\n")
    if piezas:
        lineas.append("  \\vspace{0.5em}\n")
        lineas.extend("  " + p for p in piezas)
    lineas.append("\\end{center}\n")
    lineas.append("\\vspace{0.15em}\n{\\color{gris}\\hrule height 0.5pt}\n")
    lineas.append("\\vspace{0.25em}\n{\\color{gris}\\hrule height 0.25pt}\n")
    return "".join(lineas)


def _cabecera_moderno(d, L, piezas):
    titulo = f"{{\\small\\bfseries\\color{{gris}} {L['titulo']}}}\n"
    nombre = f"{{\\Huge\\bfseries\\color{{accent}} {esc(d.get('nombre', ''))}}}"
    contacto = _contactos(d, L)

    if piezas:
        fila = (
            "\\noindent\n"
            "\\begin{minipage}[t]{0.7\\textwidth}\n"
            f"  {titulo}"
            f"  {nombre}\\par\n"
            "  \\vspace{0.4em}\n"
            f"  {contacto}\n"
            "\\end{minipage}%\n"
            "\\hfill\n"
            "\\begin{minipage}[t]{0.28\\textwidth}\n"
            "\\raggedleft\n"
            "\\vspace{0.4em}\n"
            + "".join(piezas)
            + "\\end{minipage}\n"
        )
    else:
        fila = (
            "\\noindent\n"
            f"  {titulo}"
            f"  {nombre}\\par\n"
            "  \\vspace{0.4em}\n"
            f"  {contacto}\n"
        )
    return fila + "\\vspace{0.4em}\n{\\color{accent}\\hrule height 2.5pt}\n"


def _cabecera_creativo(d, L, piezas):
    banda = (
        "\\noindent\\colorbox{accent}{%\n"
        "\\begin{minipage}{\\dimexpr\\textwidth-2\\fboxsep\\relax}\n"
        "\\vspace{0.55em}\n"
        f"{{\\color{{white}}\\Huge\\bfseries {esc(d.get('nombre', ''))}}}\\par\n"
        "\\vspace{0.15em}\n"
        f"{{\\color{{white}}\\small\\bfseries {L['titulo']}}}\\par\n"
        "\\vspace{0.55em}\n"
        "\\end{minipage}}\n"
    )
    contacto = _contactos(d, L)
    if piezas:
        bloques = (
            "\\vspace{0.6em}\n"
            "\\noindent\n"
            "\\begin{minipage}[t]{0.68\\textwidth}\n"
            f"{contacto}\n"
            "\\end{minipage}%\n"
            "\\hfill\n"
            "\\begin{minipage}[t]{0.28\\textwidth}\n"
            "\\raggedleft\n"
            "\\vspace{0.3em}\n"
            + "".join(piezas)
            + "\\end{minipage}\n"
        )
    elif contacto:
        bloques = "\\vspace{0.6em}\n" + contacto + "\n"
    else:
        bloques = ""
    return (
        banda
        + bloques
        + "\\vspace{0.4em}\n"
        + "{\\color{accent}\\hrule height 1.2pt}\n"
        + "\\vspace{0.15em}\n"
        + "{\\color{gris}\\hrule height 0.4pt}\n"
    )


def _cabecera_chino(d, L, piezas):
    banda = (
        "\\noindent\\begingroup\\setlength{\\fboxsep}{0pt}%\n"
        "\\colorbox{accent}{%\n"
        "\\parbox[c][1.6cm][c]{\\linewidth}{%\n"
        "\\hspace{0.4em}{\\color{white}\\bfseries\\fontsize{22}{24}\\selectfont "
        + L["titulo"] +
        "}}}\n"
        "\\endgroup\\par\n"
    )
    nombre = esc(d.get("nombre", "")).strip()
    contacto = _contactos(d, L)

    izquierda = [banda]
    if nombre:
        izquierda.append(f"{{\\color{{accent}}\\fontsize{{18}}{{21}}\\selectfont {nombre}}}\\par\n")
    if contacto:
        izquierda.append("\\vspace{0.45em}\n" + contacto + "\n")

    if piezas:
        fila = (
            "\\noindent\n"
            "\\begin{minipage}[t]{0.7\\textwidth}\n"
            + "".join(izquierda)
            + "\\end{minipage}%\n"
            "\\hfill\n"
            "\\begin{minipage}[t]{0.28\\textwidth}\n"
            "\\raggedleft\n"
            "\\vspace{0.3em}\n"
            + "".join(piezas)
            + "\\end{minipage}\n"
        )
    else:
        fila = "".join(izquierda)
    return fila + "\\vspace{0.6em}\n{\\color{accent}\\hrule height 1.0pt}\n"


def _cabecera(d, L, plantilla="clasico"):
    ref_logo, hay_foto, ext_foto = _datos_imagenes(d)
    piezas = _piezas_imagen(d, ref_logo, hay_foto, ext_foto)
    if plantilla == "harvard":
        return _cabecera_harvard(d, L, piezas)
    if plantilla == "moderno":
        return _cabecera_moderno(d, L, piezas)
    if plantilla == "creativo":
        return _cabecera_creativo(d, L, piezas)
    if plantilla == "chino":
        return _cabecera_chino(d, L, piezas)
    return _cabecera_clasico(d, L, piezas)


def _entrada_trabajo(clave, ent, idx, L=None):
    puesto = esc(ent.get("puesto", ""))
    modalidad = esc(ent.get("modalidad", "")).strip()
    lineas = []
    primero = _linea_fecha(puesto, ent.get("desde", ""), ent.get("hasta", ""))
    if primero:
        lineas.append(primero)
    if ent.get("empresa", "").strip():
        lineas.append(f"{{\\itshape {esc(ent['empresa'])}}}")
    if modalidad:
        lineas.append(f"({{\\footnotesize\\color{{gris}} {modalidad}}})")
    logros = [x.strip() for x in str(ent.get("logros", "")).splitlines() if x.strip()]
    if logros:
        lineas.append(_itemize([esc(x) for x in logros]))
    if not lineas:
        return ""
    return _con_logo(clave, idx, ent, "\n".join(lineas) + "\n")


def _entrada_educacion(clave, ent, idx, L):
    tipo = esc(ent.get("tipo", "")).strip()
    titulo = esc(ent.get("titulo", "")).strip()
    rotulo = " — ".join(x for x in (tipo, titulo) if x)
    lineas = []
    primero = _linea_fecha(rotulo, ent.get("desde", ""), ent.get("hasta", ""))
    if primero:
        lineas.append(primero)
    if ent.get("institucion", "").strip():
        lineas.append(f"{{\\itshape {esc(ent['institucion'])}}}")
    if ent.get("nota", "").strip():
        lineas.append(f"{{\\small\\color{{gris}} \\textbf{{{L['nota']}}} {esc(ent['nota'])}}}")
    if not lineas:
        return ""
    return _con_logo(clave, idx, ent, "\n".join(lineas) + "\n")


def _entrada_proyecto(clave, ent, idx, L, con_asignatura):
    titulo = esc(ent.get("nombre", ""))
    lineas = []
    primero = _linea_fecha(titulo, ent.get("desde", ""), ent.get("hasta", ""))
    if primero:
        lineas.append(primero)
    partes = []
    if ent.get("organizacion", "").strip():
        partes.append(f"{{\\itshape {esc(ent['organizacion'])}}}")
    if con_asignatura and ent.get("asignatura", "").strip():
        partes.append(f"{{\\footnotesize\\color{{gris}} {esc(ent['asignatura'])}}}")
    if partes:
        lineas.append("  ".join(partes))
    desc = _parrafos(ent.get("descripcion", ""))
    if desc:
        lineas.append(desc.rstrip("\n"))
    if ent.get("resultado", "").strip():
        lineas.append(f"{{\\footnotesize\\color{{gris}} \\textbf{{{L['resultado']}}} {esc(ent['resultado'])}}}")
    if ent.get("enlace", "").strip():
        lineas.append(f"{{\\footnotesize\\color{{gris}} {L['enlace']}\\texttt{{{esc(ent['enlace'])}}}}}")
    if not lineas:
        return ""
    return _con_logo(clave, idx, ent, "\n".join(lineas) + "\n") if con_asignatura else "\n".join(lineas) + "\n"


_RENDER = {
    "trabajo": _entrada_trabajo,
    "pasantia": _entrada_trabajo,
    "educacion": _entrada_educacion,
    "proyectos": lambda c, e, i, L: _entrada_proyecto(c, e, i, L, False),
    "proyectosu": lambda c, e, i, L: _entrada_proyecto(c, e, i, L, True),
}


def _chino_entrada_trabajo(clave, ent, idx, L):
    ent = ent or {}
    rango = _rango(ent.get("desde", ""), ent.get("hasta", ""))
    puesto = esc(ent.get("puesto", "")).strip()
    empresa = esc(ent.get("empresa", "")).strip()
    modalidad = esc(ent.get("modalidad", "")).strip()
    if modalidad:
        empresa = f"{empresa} ({modalidad})".strip()
    lineas = []
    if rango or puesto or empresa:
        lineas.append(f"\\cvcnlinea{{{rango}}}{{{puesto}}}{{{empresa}}}")
    logros = [x.strip() for x in str(ent.get("logros") or "").splitlines() if x.strip()]
    if logros:
        lineas.append(_itemize([esc(x) for x in logros]))
    if not lineas:
        return ""
    return "\n".join(lineas) + "\n"


def _chino_entrada_educacion(clave, ent, idx, L):
    ent = ent or {}
    rango = _rango(ent.get("desde", ""), ent.get("hasta", ""))
    institucion = esc(ent.get("institucion", "")).strip()
    tipo = esc(ent.get("tipo", "")).strip()
    titulo = esc(ent.get("titulo", "")).strip()
    grado = " — ".join(x for x in (tipo, titulo) if x)
    lineas = []
    if rango or institucion or grado:
        lineas.append(f"\\cvcnlinea{{{rango}}}{{{institucion}}}{{{grado}}}")
    if ent.get("nota", "").strip():
        lineas.append(f"{{\\small\\color{{gris}} \\textbf{{{L['nota']}}} {esc(ent['nota'])}}}")
    if not lineas:
        return ""
    return "\n".join(lineas) + "\n"


def _chino_entrada_proyecto(clave, ent, idx, L, con_asignatura):
    ent = ent or {}
    rango = _rango(ent.get("desde", ""), ent.get("hasta", ""))
    nombre = esc(ent.get("nombre", "")).strip()
    organizacion = esc(ent.get("organizacion", "")).strip()
    if con_asignatura:
        asignatura = esc(ent.get("asignatura", "")).strip()
        if asignatura:
            organizacion = f"{organizacion} — {asignatura}" if organizacion else asignatura
    lineas = []
    if rango or nombre or organizacion:
        lineas.append(f"\\cvcnlinea{{{rango}}}{{{nombre}}}{{{organizacion}}}")
    items = [esc(x.strip()) for x in str(ent.get("descripcion") or "").splitlines() if x.strip()]
    if ent.get("resultado", "").strip():
        items.append(f"\\textbf{{{L['resultado']}}} {esc(ent['resultado'])}")
    if ent.get("enlace", "").strip():
        items.append(f"{L['enlace'].strip()} \\texttt{{{esc(ent['enlace'])}}}")
    if items:
        lineas.append(_itemize(items))
    if not lineas:
        return ""
    return "\n".join(lineas) + "\n"


_CHINO_RENDER = {
    "trabajo": _chino_entrada_trabajo,
    "pasantia": _chino_entrada_trabajo,
    "educacion": _chino_entrada_educacion,
    "proyectos": lambda c, e, i, L: _chino_entrada_proyecto(c, e, i, L, False),
    "proyectosu": lambda c, e, i, L: _chino_entrada_proyecto(c, e, i, L, True),
}


def _chino_render_seccion(clave, titulo, data, L):
    entradas = data.get(clave) or []
    render = _CHINO_RENDER[clave]
    bloques = []
    for ent in entradas:
        cont = render(clave, ent, len(bloques), L)
        if cont.strip():
            bloques.append(cont)
    if not bloques:
        return ""
    return f"\\cvsection{{{titulo}}}\n" + "\\vspace{0.35em}\n".join(bloques)


def _render_seccion(clave, titulo, data, L):
    entradas = data.get(clave) or []
    entradas = [e for e in entradas if any(str(v).strip() for v in (e or {}).values())]
    if not entradas:
        return ""
    col = int((data.get("columnas") or {}).get(clave, 1) or 1)
    col = min(max(col, 1), 3)
    render = _RENDER[clave]
    bloques = []
    for inicio in range(0, len(entradas), col):
        fila = []
        for i, ent in enumerate(entradas[inicio:inicio + col]):
            cont = render(clave, ent, inicio + i, L)
            if cont.strip() == "":
                continue
            fila.append(_caja(ANCHOS[col], cont))
        if fila:
            bloques.append("\\noindent " + " \\hfill\n".join(fila) + "\n\\par\n\\vspace{0.7em}\n")
    if not bloques:
        return ""
    return f"\\cvsection{{{titulo}}}\n" + "\n".join(bloques)


def _categorias(lista, L):
    sep = L["sep_hab"]
    lineas = []
    for e in lista or []:
        cat = esc((e or {}).get("categoria", "")).strip()
        vals = [v.strip() for v in str((e or {}).get("valores", "")).split(",") if v.strip()]
        if not cat and not vals:
            continue
        cuerpo = ", ".join(esc(v) for v in vals)
        if cat and cuerpo:
            lineas.append(f"\\noindent\\textbf{{{cat}{sep}}} {cuerpo}")
        elif cat:
            lineas.append(f"\\noindent\\textbf{{{cat}}}")
        else:
            lineas.append(f"\\noindent {cuerpo}")
    return "\n\n".join(lineas) + "\n" if lineas else ""


def _parejas(lista, campo_nombre, campo_nivel, sep):
    lineas = []
    for e in lista or []:
        nombre = esc(e.get(campo_nombre, "")).strip()
        nivel = esc(e.get(campo_nivel, "")).strip()
        if not nombre and not nivel:
            continue
        if nombre and nivel:
            lineas.append(r"\textbf{%s}%s %s" % (nombre, sep, nivel))
        elif nombre:
            lineas.append(r"\textbf{%s}" % nombre)
        else:
            lineas.append(nivel)
    return _itemize(lineas) if lineas else ""


def build_tex(data, p):
    pid = str(data.get("plantilla", "clasico") or "clasico").strip().lower()
    if pid not in PLANTILLAS:
        pid = "clasico"
    ruta = os.path.join(BASE_DIR, "templates", ARCHIVOS[pid])
    with open(ruta, "r", encoding="utf-8") as f:
        tex = f.read()
    # Los comentarios de la plantilla documentan marcadores con {{...}}; no
    # forman parte del documento generado y no deben sobrevivir a las sustituciones.
    tex = "\n".join(
        linea for linea in tex.splitlines()
        if not (linea.lstrip().startswith("%") and "{{" in linea)
    )
    L = LANG.get(str(data.get("idioma_cv", "zh")), LANG["zh"])

    cuerpo = ""
    perfil = esc(data.get("perfil", "").strip())
    if perfil:
        cuerpo += _seccion(L["perfil"], perfil + "\n")
    render = _chino_render_seccion if pid == "chino" else _render_seccion
    cuerpo += render("educacion", L["educacion"], data, L)
    cuerpo += render("proyectos", L["proyectos"], data, L)
    cuerpo += render("proyectosu", L["proyectosu"], data, L)
    cuerpo += render("pasantia", L["pasantia"], data, L)
    cuerpo += render("trabajo", L["trabajo"], data, L)
    cuerpo += _seccion(L["habilidades"], _categorias(data.get("habilidades"), L))
    cuerpo += _seccion(L["idiomas"], _parejas(data.get("idiomas"), "idioma", "nivel", " --- "))
    cuerpo += _seccion(L["referencias"], _parejas(data.get("referencias"), "nombre", "contacto", " --- "))

    m = p["margenes"]
    papeles = {"a4": "a4paper", "letter": "letterpaper", "legal": "legalpaper"}
    papel = papeles.get(str(p["papel"]), "a4paper")
    if L is LANG["zh"]:
        motor_tipografia = (
            "\\usepackage{fontspec}\n"
            "\\setmainfont{Microsoft YaHei}\n"
            "\\setsansfont{Microsoft YaHei}\n"
            "\\setmonofont{Consolas}"
        )
    else:
        motor_tipografia = (
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[T1]{fontenc}\n"
            "\\usepackage{lmodern}"
        )
    tex = tex.replace("{{papel}}", papel)
    tex = tex.replace("{{motor_tipografia}}", motor_tipografia)
    tex = tex.replace("{{marg_sup}}", f"{m['top']:g}")
    tex = tex.replace("{{marg_inf}}", f"{m['bottom']:g}")
    tex = tex.replace("{{marg_izq}}", f"{m['left']:g}")
    tex = tex.replace("{{marg_der}}", f"{m['right']:g}")
    tex = tex.replace("{{fuente}}", str(p["fuente"]))
    tex = tex.replace("{{cabecera}}", _cabecera(data, L, pid))
    tex = tex.replace("{{cuerpo}}", cuerpo)
    return tex_datos.incrustar(tex, data)