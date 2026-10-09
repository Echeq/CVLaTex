import base64
import functools
import http.server
import json
import mimetypes
import os
import re
import shutil
import sys
import threading
import uuid

import webview

import docx_gen
import latex_engine
import latex_gen
import prefs
import tex_datos

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
RUTAS = {
    "/app.js": os.path.join(WEB_DIR, "app.js"),
    "/style.css": os.path.join(WEB_DIR, "style.css"),
}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _servir(self, ruta, descargar=False):
        try:
            if not os.path.isfile(ruta):
                self.send_error(404)
                return
            tipo, _ = mimetypes.guess_type(ruta)
            if tipo is None:
                tipo = "application/octet-stream"
            with open(ruta, "rb") as f:
                datos = f.read()
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            if descargar:
                self.send_header(
                    "Content-Disposition",
                    'attachment; filename="%s"' % os.path.basename(ruta),
                )
            self.send_header("Content-Length", str(len(datos)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(datos)
        except (OSError, ConnectionError):
            pass

    def _ruta_sin_query(self):
        from urllib.parse import urlsplit

        return urlsplit(self.path).path

    def _sin_contenido(self):
        self.send_response(204)
        self.end_headers()

    def _servir_seguro(self, base, relativo):
        """Sirve un fichero contenido en base; si la ruta escapa, devuelve 404."""
        try:
            base_real = os.path.realpath(base)
            objetivo = os.path.realpath(os.path.join(base_real, relativo))
            if os.path.commonpath([os.path.normcase(base_real), os.path.normcase(objetivo)]) != os.path.normcase(base_real):
                self.send_error(404)
                return
        except ValueError:
            self.send_error(404)
            return
        self._servir(objetivo)

    def do_GET(self):
        ruta = self._ruta_sin_query()
        if ruta in ("/", "/index.html"):
            self._servir(os.path.join(WEB_DIR, "index.html"))
        elif ruta in RUTAS:
            self._servir(RUTAS[ruta])
        elif ruta.startswith("/preview/"):
            self._servir_seguro(prefs.BUILD_DIR, ruta[len("/preview/"):])
        elif ruta.startswith("/media/"):
            self._servir_seguro(prefs.CACHE_DIR, ruta[len("/media/"):])
        elif ruta == "/favicon.ico":
            self._sin_contenido()
        else:
            self.send_error(404)


class Api:
    def __init__(self, win):
        self._w = win

    def init(self):
        prefs.load()
        ruta_latex = latex_engine.find_pdflatex()
        return {
            "prefs": prefs.load(),
            "latex_ok": ruta_latex is not None,
            "needs_setup": ruta_latex is None and not prefs.get("setup_dismissed"),
        }

    def _empujar(self, nombre, datos):
        try:
            self._w.evaluate_js(
                "window.%s(%s);" % (nombre, json.dumps(datos, ensure_ascii=False))
            )
        except Exception:
            pass

    def compile(self, datos, id_compilacion):
        threading.Thread(target=self._compilar_en_hilo, args=(datos, id_compilacion), daemon=True).start()
        return "ok"

    def _compilar_en_hilo(self, datos, id_compilacion):
        try:
            tex = latex_gen.build_tex(datos, prefs.load())
            resultado = latex_engine.compile(tex, datos.get("foto"), latex_gen.logos_extra(datos))
            resultado["tex"] = tex
        except Exception as e:
            resultado = {"ok": False, "pdf": None, "errores": [f"Error interno: {e}"]}
        resultado["id"] = id_compilacion
        self._empujar("__onCompile", resultado)

    def compilar_tex(self, tex, id_compilacion, datos=None):
        threading.Thread(target=self._compilar_tex_hilo, args=(tex, id_compilacion, datos), daemon=True).start()
        return "ok"

    def _compilar_tex_hilo(self, tex, id_compilacion, datos=None):
        try:
            resultado = latex_engine.compile(
                tex,
                datos.get("foto") if datos else None,
                latex_gen.logos_extra(datos) if datos else None,
            )
        except Exception as e:
            resultado = {"ok": False, "pdf": None, "errores": [f"Error interno: {e}"]}
        resultado["id"] = id_compilacion
        resultado["tex"] = tex
        self._empujar("__onCompile", resultado)

    def datos_vacios(self):
        return latex_gen.datos_vacios()

    def cargar_ejemplo(self, plantilla=None):
        try:
            import ejemplo

            p = str(plantilla or "clasico").strip().lower()
            if p not in latex_gen.PLANTILLAS:
                p = "clasico"
            d = ejemplo.datos_ejemplo_cn() if p == "chino" else ejemplo.datos_ejemplo()
            d["plantilla"] = p
            return {"ok": True, "datos": d}
        except Exception as e:
            return {"ok": False, "errores": [str(e)]}

    def elegir_archivo(self, tipos, guardar, nombre_sugerido):
        if guardar:
            ruta = self._w.create_file_dialog(
                webview.FileDialog.SAVE, save_filename=nombre_sugerido, file_types=tipos
            )
        else:
            ruta = self._w.create_file_dialog(
                webview.FileDialog.OPEN, file_types=tipos
            )
        if isinstance(ruta, (list, tuple)):
            ruta = ruta[0] if ruta else None
        return ruta

    def elegir_foto(self, tipo=None):
        tipo = "logo" if str(tipo or "").strip().lower() == "logo" else "foto"
        ruta = self.elegir_archivo(("Imágenes (*.jpg;*.jpeg;*.png)",), False, None)
        if not ruta:
            return {"ok": False}
        try:
            ext = os.path.splitext(ruta)[1].lower()
            if ext not in latex_engine.FOTOS_PERMITIDAS:
                return {"ok": False, "error": "Formato no admitido (usa JPG o PNG)."}
            os.makedirs(prefs.CACHE_DIR, exist_ok=True)
            nombre = "%s_%s%s" % (tipo, uuid.uuid4().hex, ext)
            destino = os.path.join(prefs.CACHE_DIR, nombre)
            shutil.copy2(ruta, destino)
            return {"ok": True, "path": destino, "url": "/media/" + nombre}
        except OSError as e:
            return {"ok": False, "error": str(e)}

    def guardar_foto_recorte(self, data_url):
        try:
            datos_img = base64.b64decode(data_url.split(",", 1)[1])
            os.makedirs(prefs.CACHE_DIR, exist_ok=True)
            nombre = "recorte_%s.png" % uuid.uuid4().hex
            destino = os.path.join(prefs.CACHE_DIR, nombre)
            with open(destino, "wb") as f:
                f.write(datos_img)
            return {"ok": True, "path": destino, "url": "/media/" + nombre}
        except Exception as e:
            return {"ok": False, "error": f"No se pudo guardar el recorte: {e}"}

    def guardar_imagen(self, data_url, tipo=None):
        """Guarda una imagen enviada como data URL base64 PNG/JPEG.

        Acepta solo cabeceras ``data:image/png;base64,`` y
        ``data:image/jpeg;base64,`` con base64 estricto. El prefijo del
        fichero es ``foto`` salvo que ``tipo`` sea logo o recorte.
        """
        try:
            if not isinstance(data_url, str):
                raise ValueError("data URL no válida.")
            coincidencia = re.fullmatch(
                r"data:(image/(?:png|jpeg));base64,([A-Za-z0-9+/]*={0,2})",
                data_url,
            )
            if coincidencia is None:
                raise ValueError("data URL no válida o MIME no admitido (usa PNG o JPEG).")
            mime, b64 = coincidencia.group(1), coincidencia.group(2)
            datos_img = base64.b64decode(b64, validate=True)
            if not datos_img:
                raise ValueError("la imagen está vacía.")
            prefijo = tipo if tipo in ("foto", "logo", "recorte") else "foto"
            ext = ".png" if mime == "image/png" else ".jpg"
            os.makedirs(prefs.CACHE_DIR, exist_ok=True)
            nombre = "%s_%s%s" % (prefijo, uuid.uuid4().hex, ext)
            destino = os.path.join(prefs.CACHE_DIR, nombre)
            with open(destino, "wb") as f:
                f.write(datos_img)
            return {"ok": True, "path": destino, "url": "/media/" + nombre}
        except Exception as e:
            return {"ok": False, "errores": [str(e)]}

    def exportar_pdf(self, datos, tex_manual=None):
        try:
            if tex_manual:
                # El bloque incrustado se refresca siempre desde los datos,
                # aunque el usuario compile su propio .tex.
                tex = tex_datos.incrustar(tex_manual, datos)
                foto = None
                extras = None
            else:
                tex = latex_gen.build_tex(datos, prefs.load())
                foto = datos.get("foto")
                extras = latex_gen.logos_extra(datos)
            resultado = latex_engine.compile(tex, foto, extras)
            if not resultado["ok"]:
                return {"ok": False, "errores": resultado["errores"]}
            sugerido = "CV.pdf"
            if datos.get("nombre"):
                sugerido = "CV-%s.pdf" % datos["nombre"].strip().replace(" ", "_")
            ruta = self.elegir_archivo(("PDF (*.pdf)",), True, sugerido)
            if not ruta:
                return {"ok": False, "cancelado": True}
            shutil.copy2(resultado["pdf"], ruta)
            return {"ok": True, "ruta": ruta}
        except Exception as e:
            return {"ok": False, "errores": [str(e)]}

    def exportar_tex(self, datos, tex_manual=None):
        try:
            tex = tex_manual if tex_manual else latex_gen.build_tex(datos, prefs.load())
            # Refresca el bloque de datos aunque exista un tex_manual.
            tex = tex_datos.incrustar(tex, datos)
            sugerido = "CV.tex"
            if datos.get("nombre"):
                sugerido = "CV-%s.tex" % datos["nombre"].strip().replace(" ", "_")
            ruta = self.elegir_archivo(("LaTeX (*.tex)",), True, sugerido)
            if not ruta:
                return {"ok": False, "cancelado": True}
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(tex)
            return {"ok": True, "ruta": ruta}
        except OSError as e:
            return {"ok": False, "errores": [str(e)]}

    def exportar_docx(self, datos):
        try:
            sugerido = "CV.docx"
            if datos.get("nombre"):
                sugerido = "CV-%s.docx" % datos["nombre"].strip().replace(" ", "_")
            ruta = self.elegir_archivo(("Word (*.docx)",), True, sugerido)
            if not ruta:
                return {"ok": False, "cancelado": True}
            # docx_gen no depende de LaTeX ni de pywebview.
            docx_gen.exportar(datos, prefs.load(), ruta)
            return {"ok": True, "ruta": ruta}
        except Exception as e:
            return {"ok": False, "errores": [str(e)]}

    def exportar_cv(self, datos):
        try:
            sugerido = "mi_cv.cvjson"
            if datos.get("nombre"):
                sugerido = "%s.cvjson" % datos["nombre"].strip().replace(" ", "_")
            ruta = self.elegir_archivo(("CVLaTeX (*.cvjson)",), True, sugerido)
            if not ruta:
                return {"ok": False, "cancelado": True}
            contenido = {"version": 2, "datos": datos, "medios": _recolectar_medios(datos)}
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(contenido, f, ensure_ascii=False, indent=2)
            return {"ok": True, "ruta": ruta}
        except OSError as e:
            return {"ok": False, "errores": [str(e)]}

    def abrir_cv(self):
        ruta = self.elegir_archivo(("CVLaTeX (*.cvjson)",), False, None)
        if not ruta:
            return {"ok": False, "cancelado": True}
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = json.load(f)
            datos = contenido.get("datos") if isinstance(contenido, dict) else None
            if not isinstance(datos, dict):
                return {"ok": False, "errores": ["Archivo no válido."]}
            try:
                datos = _migrar_datos(datos)
            except Exception as e:
                return {"ok": False, "errores": [f"No se pudo abrir: {e}"]}
            if isinstance(contenido, dict) and contenido.get("version") == 2:
                datos = _materializar_medios(datos, contenido.get("medios"))
            # Rellene solo las claves ausentes. Si el valor por defecto es None
            # (p. ej. foto_recorte), no se comprueba el tipo: un rectángulo dict
            # válido debe sobrevivir; el None solo se aplica si falta la clave.
            vacios = latex_gen.datos_vacios()
            for k, por_defecto in vacios.items():
                if k not in datos or (por_defecto is not None and not isinstance(datos[k], type(por_defecto))):
                    datos[k] = por_defecto
            return {"ok": True, "datos": datos, "ruta": ruta}
        except (OSError, UnicodeDecodeError, ValueError) as e:
            return {"ok": False, "errores": [f"No se pudo abrir: {e}"]}

    def autosave(self, datos):
        try:
            os.makedirs(prefs.APP_DIR, exist_ok=True)
            contenido = {"version": 2, "datos": datos, "medios": _recolectar_medios(datos)}
            with open(os.path.join(prefs.APP_DIR, "autosave.cvjson"), "w", encoding="utf-8") as f:
                json.dump(contenido, f, ensure_ascii=False)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "errores": [str(e)]}

    def autosave_leer(self):
        try:
            with open(os.path.join(prefs.APP_DIR, "autosave.cvjson"), "r", encoding="utf-8") as f:
                contenido = json.load(f)
            return contenido if isinstance(contenido, dict) else None
        except Exception:
            return None

    def autosave_borrar(self):
        try:
            ruta = os.path.join(prefs.APP_DIR, "autosave.cvjson")
            if os.path.isfile(ruta):
                os.remove(ruta)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "errores": [str(e)]}

    def importar_tex(self):
        ruta = self.elegir_archivo(("LaTeX (*.tex)",), False, None)
        if not ruta:
            return {"ok": False, "cancelado": True}
        try:
            with open(ruta, "r", encoding="utf-8", errors="replace") as f:
                tex = f.read()
            try:
                datos = tex_datos.extraer(tex)
            except tex_datos.SinBloqueDatos:
                if "CVLaTeX" in tex:
                    msg = (
                        "Este .tex fue generado por una versión anterior de CVLaTeX sin datos incrustados: "
                        "no se puede reimportar. Vuelve a generarlo con la versión actual."
                    )
                else:
                    msg = (
                        "Esta plantilla no tiene buena compatibilidad con la aplicación. "
                        "Se recomienda buscar otra plantilla."
                    )
                return {"ok": False, "errores": [msg]}
            except tex_datos.BloqueDatosInvalido:
                return {"ok": False, "errores": ["El bloque de datos de CVLaTeX está dañado y no se puede reimportar."]}
            try:
                datos = _migrar_datos(datos)
            except Exception as e:
                return {"ok": False, "errores": [f"No se pudo abrir: {e}"]}
            # Rellene solo las claves ausentes. Si el valor por defecto es None
            # (p. ej. foto_recorte), no se comprueba el tipo: un rectángulo dict
            # válido debe sobrevivir; el None solo se aplica si falta la clave.
            vacios = latex_gen.datos_vacios()
            for k, por_defecto in vacios.items():
                if k not in datos or (por_defecto is not None and not isinstance(datos[k], type(por_defecto))):
                    datos[k] = por_defecto
            if datos.get("plantilla") not in latex_gen.PLANTILLAS:
                datos["plantilla"] = "clasico"
            return {"ok": True, "datos": datos, "ruta": ruta}
        except (OSError, UnicodeDecodeError, ValueError) as e:
            return {"ok": False, "errores": [f"No se pudo abrir: {e}"]}

    def install_latex(self):
        threading.Thread(target=self._instalar_hilo, daemon=True).start()
        return "ok"

    def _instalar_hilo(self):
        def progreso(hecho, total):
            self._empujar("__onInstallProgress", {"hecho": hecho, "total": total})

        try:
            padre = latex_engine.install_tinytex(progreso)
            self._empujar("__onInstallDone", {"ok": True, "msg": "TinyTeX instalado correctamente.", "path": padre})
        except latex_engine.ErrorLatex as e:
            self._empujar("__onInstallDone", {"ok": False, "msg": str(e)})
        except Exception as e:
            self._empujar("__onInstallDone", {"ok": False, "msg": f"Error inesperado: {e}"})

    def elegir_ruta_latex(self):
        ruta = self.elegir_archivo(("pdflatex.exe",), False, None)
        if not ruta:
            return {"ok": False, "cancelado": True}
        prefs.set("latex_path", ruta)
        return {"ok": True, "path": ruta}

    def comprobar_latex(self):
        p = latex_engine.find_pdflatex()
        return {"ok": p is not None, "path": p}

    def set_prefs(self, clave, valor):
        prefs.set(clave, valor)
        return prefs.load()

    def get_prefs(self):
        return prefs.load()

    def marcar_setup_ignorado(self):
        prefs.set("setup_dismissed", True)


MEDIA_EXTS = (".jpg", ".jpeg", ".png")
CAMPOS_MEDIA = ("foto", "foto_original", "foto_recorte", "logo_egresado")
CAMPOS_LOGO = ("trabajo", "pasantia", "proyectos", "proyectosu", "educacion")


def _sanear_bloques(bloques):
    """Normaliza la lista de bloques libres; nunca lanza.

    Descarta entradas que no sean dict o con un ``tipo`` desconocido,
    completa ``estilo``/``posicion``/``id``, garantiza ids únicos y
    reconstruye cada bloque solo con las claves canónicas de su tipo.
    """
    try:
        if not isinstance(bloques, list):
            return []
        limpios = []
        ids = set()
        for bruto in bloques:
            try:
                if not isinstance(bruto, dict):
                    continue
                tipo = str(bruto.get("tipo") or "").strip()
                if tipo not in latex_gen.TIPOS_BLOQUE:
                    continue
                posicion = str(bruto.get("posicion") or "").strip()
                if posicion not in latex_gen.ANCLAS_BLOQUE:
                    posicion = "final"
                ident = bruto.get("id")
                if not isinstance(ident, str) or not ident or ident in ids:
                    ident = uuid.uuid4().hex
                    while ident in ids:
                        ident = uuid.uuid4().hex
                ids.add(ident)
                if tipo == "separador":
                    estilo = str(bruto.get("estilo") or "").strip()
                    if estilo not in latex_gen.ESTILOS_SEPARADOR:
                        estilo = "linea"
                    limpios.append({
                        "id": ident,
                        "tipo": tipo,
                        "estilo": estilo,
                        "posicion": posicion,
                    })
                else:
                    titulo = bruto.get("titulo")
                    contenido = bruto.get("contenido")
                    limpios.append({
                        "id": ident,
                        "tipo": tipo,
                        "titulo": "" if titulo is None else str(titulo),
                        "contenido": "" if contenido is None else str(contenido),
                        "posicion": posicion,
                    })
            except Exception:
                continue
        return limpios
    except Exception:
        return []


def _sanear_secciones_nuevas(datos):
    """Normaliza titulos_seccion / secciones_ocultas / orden_secciones.

    Nunca lanza: entradas ausentes o mal formadas caen a los valores
    canónicos (dict vacío, lista vacía, orden por defecto completo).
    """
    if not isinstance(datos, dict):
        return datos
    claves = latex_gen.ORDEN_SECCIONES_DEFECTO

    # orden_secciones: mismo contrato que latex_gen.normalizar_orden_secciones
    # (claves válidas, dedup conservando la primera, faltantes al final en
    # orden por defecto; cualquier valor que no sea lista/tupla -> lista
    # completa por defecto). Única excepción: la lista vacía es el centinela
    # canónico de "orden por defecto" (lo devuelve datos_vacios y lo expande
    # normalizar_orden_secciones al renderizar), así que se conserva para que
    # abrir/importar un CV ya canónico no invente un orden no elegido.
    try:
        bruto_orden = datos.get("orden_secciones")
        lista_vacia = isinstance(bruto_orden, (list, tuple)) and len(bruto_orden) == 0
    except Exception:
        lista_vacia = False
    if lista_vacia:
        orden = []
    else:
        try:
            orden = latex_gen.normalizar_orden_secciones(datos)
            if not isinstance(orden, list):
                orden = list(claves)
        except Exception:
            orden = list(claves)

    # titulos_seccion: solo claves válidas con valor str recortado y no vacío.
    titulos = {}
    try:
        bruto_titulos = datos.get("titulos_seccion")
    except Exception:
        bruto_titulos = None
    if isinstance(bruto_titulos, dict):
        for clave in claves:
            try:
                valor = bruto_titulos.get(clave)
                if not isinstance(valor, str):
                    continue
                valor = valor.strip()
            except Exception:
                continue
            if valor:
                titulos[clave] = valor

    # secciones_ocultas: claves válidas sin duplicados (gana la primera).
    ocultas = []
    try:
        bruto_ocultas = datos.get("secciones_ocultas")
    except Exception:
        bruto_ocultas = None
    if isinstance(bruto_ocultas, (list, tuple)):
        for valor in bruto_ocultas:
            try:
                if isinstance(valor, str) and valor in claves and valor not in ocultas:
                    ocultas.append(valor)
            except Exception:
                continue

    datos["titulos_seccion"] = titulos
    datos["secciones_ocultas"] = ocultas
    datos["orden_secciones"] = orden
    return datos


def _migrar_datos(datos):
    """Convierte archivos .cvjson antiguos al modelo actual."""
    if not isinstance(datos, dict):
        return datos
    if "experiencia" in datos and isinstance(datos.get("experiencia"), list) and not (datos.get("trabajo") or datos.get("pasantia")):
        trabajo, pasantia = [], []
        for e in datos["experiencia"]:
            if isinstance(e, dict) and str(e.get("tipo", "")).strip().lower().startswith("pasant"):
                pasantia.append(e)
            else:
                trabajo.append(e)
        datos["trabajo"] = trabajo
        datos["pasantia"] = pasantia
        datos.pop("experiencia", None)
    if "habilidades" in datos and isinstance(datos.get("habilidades"), list):
        nuevas = []
        for h in datos["habilidades"]:
            if not isinstance(h, dict):
                continue
            if h.get("categoria") or h.get("valores"):
                nuevas.append(h)
            elif h.get("nombre"):
                nuevas.append({"categoria": h["nombre"], "valores": h.get("nivel", "")})
        datos["habilidades"] = nuevas
    datos["bloques"] = _sanear_bloques(datos.get("bloques"))
    return _sanear_secciones_nuevas(datos)


def _recolectar_medios(datos):
    """Devuelve {ruta_original: {'nombre': basename, 'b64': ...}} de los medios existentes."""
    medios = {}
    if not isinstance(datos, dict):
        return medios
    candidatos = []
    for clave in CAMPOS_MEDIA:
        valor = datos.get(clave)
        if isinstance(valor, str) and valor:
            candidatos.append(valor)
    for clave in CAMPOS_LOGO:
        lista = datos.get(clave)
        if not isinstance(lista, list):
            continue
        for ent in lista:
            if isinstance(ent, dict):
                valor = ent.get("logo")
                if isinstance(valor, str) and valor:
                    candidatos.append(valor)
    for ruta in candidatos:
        if ruta in medios:
            continue
        ext = os.path.splitext(ruta)[1].lower()
        if ext not in MEDIA_EXTS or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
        except OSError:
            continue
        medios[ruta] = {"nombre": os.path.basename(ruta), "b64": b64}
    return medios


def _reescribir_medios(datos, reemplazos):
    for clave in CAMPOS_MEDIA:
        if isinstance(datos.get(clave), str):
            datos[clave] = reemplazos.get(datos[clave], datos[clave])
    for clave in CAMPOS_LOGO:
        lista = datos.get(clave)
        if not isinstance(lista, list):
            continue
        for ent in lista:
            if isinstance(ent, dict) and isinstance(ent.get("logo"), str):
                ent["logo"] = reemplazos.get(ent["logo"], ent["logo"])
    return datos


def _materializar_medios(datos, medios):
    """Escribe los medios de un .cvjson v2 en CACHE_DIR y reescribe las rutas."""
    if not isinstance(datos, dict) or not isinstance(medios, dict) or not medios:
        return datos
    try:
        os.makedirs(prefs.CACHE_DIR, exist_ok=True)
    except OSError:
        return datos
    reemplazos = {}
    for ruta_original, info in medios.items():
        if not isinstance(info, dict):
            continue
        b64 = info.get("b64")
        if not isinstance(b64, str):
            continue
        try:
            crudo = base64.b64decode(b64)
        except Exception:
            continue
        if not crudo:
            continue
        ext = os.path.splitext(str(ruta_original))[1].lower()
        if ext not in MEDIA_EXTS:
            ext = os.path.splitext(str(info.get("nombre") or ""))[1].lower()
        if ext not in MEDIA_EXTS:
            ext = ".jpg"
        nombre = "cv_%s%s" % (uuid.uuid4().hex, ext)
        destino = os.path.join(prefs.CACHE_DIR, nombre)
        try:
            with open(destino, "wb") as f:
                f.write(crudo)
        except OSError:
            continue
        reemplazos[str(ruta_original)] = destino
    if not reemplazos:
        return datos
    return _reescribir_medios(datos, reemplazos)


def _iniciar_servidor():
    os.makedirs(prefs.BUILD_DIR, exist_ok=True)
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    puerto = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, puerto


def main():
    if getattr(sys, "frozen", False):
        import multiprocessing

        multiprocessing.freeze_support()
    servidor, puerto = _iniciar_servidor()
    api = Api(None)
    win = webview.create_window(
        "CVLaTeX — Editor de CV",
        url=f"http://127.0.0.1:{puerto}",
        js_api=api,
        width=1240,
        height=800,
        min_size=(900, 580),
        background_color="#1f2430",
    )
    api._w = win
    webview.start()
    servidor.shutdown()


if __name__ == "__main__":
    main()