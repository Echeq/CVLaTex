"""Incrustado y extraccion del bloque base64 de datos en el .tex de CVLaTeX.

El bloque se escribe como comentarios LaTeX (lineas que empiezan por "%"), de
modo que el documento sigue compilando igual, y permite reconstruir el dict de
datos original (round-trip) a partir del .tex generado.
"""

import base64
import json
import re

MARCA_INICIO = "% CVLaTeX-DATA-BEGIN"
MARCA_FIN = "% CVLaTeX-DATA-END"
ANCHO_LINEA = 76  # deja lineas de 78 caracteres: por debajo del limite de TeX

_RE_BLOQUE = re.compile(
    re.escape(MARCA_INICIO) + r".*?" + re.escape(MARCA_FIN) + r"[^\n]*\n?",
    re.DOTALL,
)
_RE_CONTENIDO = re.compile(
    re.escape(MARCA_INICIO) + r"(.*?)" + re.escape(MARCA_FIN),
    re.DOTALL,
)
_RE_DOCUMENTO = re.compile(r"^[ \t]*\\begin\{document\}", re.MULTILINE)


class SinBloqueDatos(Exception):
    """El .tex no contiene los marcadores del bloque de datos."""


class BloqueDatosInvalido(Exception):
    """El bloque existe pero su base64, su JSON o su forma no son validos."""


def bloque(datos):
    """Devuelve el bloque de comentarios LaTeX con los datos codificados."""
    crudo = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    codificado = base64.b64encode(crudo).decode("ascii")
    partes = [MARCA_INICIO + "\n"]
    for i in range(0, len(codificado), ANCHO_LINEA):
        partes.append("% " + codificado[i:i + ANCHO_LINEA] + "\n")
    partes.append(MARCA_FIN + "\n")
    return "".join(partes)


def incrustar(tex, datos):
    """Reemplaza todos los bloques existentes por el nuevo o lo inserta.

    Si no hay bloque, lo coloca justo antes de la primera linea
    \\begin{document}; si esa linea no existe, al inicio del fichero.
    """
    nuevo = bloque(datos)
    if _RE_BLOQUE.search(tex):
        tex = _RE_BLOQUE.sub(lambda _m: nuevo, tex)
        # Si habia varias copias, deja solo la primera para no duplicar datos.
        primera = tex.find(nuevo)
        return tex[:primera + len(nuevo)] + tex[primera + len(nuevo):].replace(nuevo, "")
    m = _RE_DOCUMENTO.search(tex)
    if m:
        return tex[:m.start()] + nuevo + tex[m.start():]
    return nuevo + tex


def extraer(tex):
    """Reconstruye el dict de datos incrustado en el .tex."""
    m = _RE_CONTENIDO.search(tex or "")
    if not m:
        raise SinBloqueDatos("No se encontro el bloque de datos en el .tex.")
    partes = []
    for linea in m.group(1).splitlines():
        limpia = linea.strip()
        if limpia.startswith("%"):
            limpia = limpia[1:].strip()
        partes.append(limpia)
    try:
        crudo = base64.b64decode("".join(partes))
        datos = json.loads(crudo.decode("utf-8"))
    except ValueError as e:
        raise BloqueDatosInvalido("El bloque de datos no es base64/JSON valido.") from e
    if not isinstance(datos, dict):
        raise BloqueDatosInvalido("El bloque de datos no contiene un diccionario JSON.")
    return datos
