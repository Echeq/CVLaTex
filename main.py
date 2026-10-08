import functools
import http.server
import json
import mimetypes
import os
import shutil
import sys
import threading

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

    def do_GET(self):
        ruta = self._ruta_sin_query()
        if ruta in ("/", "/index.html"):
            self._servir(os.path.join(WEB_DIR, "index.html"))
        elif ruta in RUTAS:
            self._servir(RUTAS[ruta])
        elif ruta.startswith("/preview/"):
            self._servir(os.path.join(prefs.BUILD_DIR, ruta[len("/preview/"):]))
        elif ruta.startswith("/media/"):
            self._servir(os.path.join(prefs.CACHE_DIR, ruta[len("/media/"):]))
        elif ruta == "/favicon.ico":
            self._sin_contenido()
        else:
            self.send_error(404)


class Api:
    def __init__(self, win):
        self._w = win
        self._compilar_id = 0

    def init(self):
        prefs.load()
        return {
            "prefs": prefs.load(),
            "latex_ok": latex_engine.find_pdflatex() is not None,
            "needs_setup": latex_engine.find_pdflatex() is None and not prefs.get("setup_dismissed"),
        }

    def _empujar(self, nombre, datos):
        try:
            self._w.evaluate_js(
                "window.%s(%s);" % (nombre, json.dumps(datos, ensure_ascii=False))
            )
        except Exception:
            pass

    def compile(self, datos, id_compilacion):
        self._compilar_id = id_compilacion
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

    def tex_actual(self, datos):
        try:
            return latex_gen.build_tex(datos, prefs.load())
        except Exception as e:
            return f"% Error al generar: {e}"

    def compilar_tex(self, tex, id_compilacion):
        self._compilar_id = id_compilacion
        threading.Thread(target=self._compilar_tex_hilo, args=(tex, id_compilacion), daemon=True).start()
        return "ok"

    def _compilar_tex_hilo(self, tex, id_compilacion):
        try:
            resultado = latex_engine.compile(tex, None)
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

    def elegir_foto(self):
        ruta = self.elegir_archivo(("Imágenes (*.jpg;*.jpeg;*.png)",), False, None)
        if not ruta:
            return {"ok": False}
        try:
            ext = os.path.splitext(ruta)[1].lower() or ".jpg"
            if ext not in latex_engine.FOTOS_PERMITIDAS:
                return {"ok": False, "error": "Formato no admitido (usa JPG o PNG)."}
            destino = os.path.join(prefs.CACHE_DIR, "foto" + ext)
            shutil.copy2(ruta, destino)
            return {"ok": True, "path": destino, "url": "/media/foto" + ext}
        except OSError as e:
            return {"ok": False, "error": str(e)}

    def guardar_foto_recorte(self, data_url):
        try:
            import base64

            datos_img = base64.b64decode(data_url.split(",", 1)[1])
            destino = os.path.join(prefs.CACHE_DIR, "foto_recorte.png")
            with open(destino, "wb") as f:
                f.write(datos_img)
            return {"ok": True, "path": destino, "url": "/media/foto_recorte.png"}
        except Exception as e:
            return {"ok": False, "error": f"No se pudo guardar el recorte: {e}"}

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
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump({"version": 1, "datos": datos}, f, ensure_ascii=False, indent=2)
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
            datos = _migrar_datos(datos)
            vacios = latex_gen.datos_vacios()
            for k in vacios:
                if k not in datos or not isinstance(datos[k], type(vacios[k])):
                    datos[k] = vacios[k]
            return {"ok": True, "datos": datos, "ruta": ruta}
        except (OSError, json.JSONDecodeError) as e:
            return {"ok": False, "errores": [f"No se pudo abrir: {e}"]}

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
            datos = _migrar_datos(datos)
            vacios = latex_gen.datos_vacios()
            for k in vacios:
                if k not in datos or not isinstance(datos[k], type(vacios[k])):
                    datos[k] = vacios[k]
            if datos.get("plantilla") not in latex_gen.PLANTILLAS:
                datos["plantilla"] = "clasico"
            return {"ok": True, "datos": datos, "ruta": ruta}
        except OSError as e:
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


def _migrar_datos(datos):
    """Convierte archivos .cvjson antiguos al modelo actual."""
    if "experiencia" in datos and isinstance(datos.get("experiencia"), list) and not (datos.get("trabajo") or datos.get("pasantia")):
        trabajo, pasantia = [], []
        for e in datos["experiencia"]:
            if str((e or {}).get("tipo", "")).strip().lower().startswith("pasant"):
                pasantia.append(e)
            else:
                trabajo.append(e)
        datos["trabajo"] = trabajo
        datos["pasantia"] = pasantia
        datos.pop("experiencia", None)
    if "habilidades" in datos and isinstance(datos.get("habilidades"), list):
        nuevas = []
        for h in datos["habilidades"]:
            if (h or {}).get("categoria") or (h or {}).get("valores"):
                nuevas.append(h)
            elif (h or {}).get("nombre"):
                nuevas.append({"categoria": h["nombre"], "valores": h.get("nivel", "")})
        datos["habilidades"] = nuevas
    return datos


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