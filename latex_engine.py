import os
import shutil
import subprocess
import threading
import urllib.request
import uuid
import zipfile

import latex_gen
import prefs

TINYTEX_VERSION = "2026.08"
TINYTEX_URLS = [
    f"https://github.com/rstudio/tinytex-releases/releases/download/v{TINYTEX_VERSION}/TinyTeX-v{TINYTEX_VERSION}.zip",
]
FOTOS_PERMITIDAS = {".jpg", ".jpeg", ".png"}
_CANDADO = threading.Lock()
_FLAGS_SUBPROCESO = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW: sin ventana de consola


class ErrorLatex(Exception):
    pass


def _check(path):
    try:
        r = subprocess.run(
            [path, "-version"],
            capture_output=True,
            timeout=20,
            creationflags=_FLAGS_SUBPROCESO,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def find_pdflatex():
    p = prefs.get("latex_path")
    if p and os.path.isfile(p) and _check(p):
        return p
    bundled = os.path.join(prefs.TINYTEX_DIR, "bin", "windows", "pdflatex.exe")
    if os.path.isfile(bundled) and _check(bundled):
        return bundled
    w = shutil.which("pdflatex")
    if w:
        return w
    return None


def _descargar(url, destino, progreso):
    req = urllib.request.Request(url, headers={"User-Agent": "CVLaTeX/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(destino, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            hecho = 0
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                hecho += len(chunk)
                progreso(hecho, total)
    except (urllib.error.URLError, OSError) as e:
        raise ErrorLatex(f"No se pudo descargar TinyTeX: {e}") from e
    except KeyError as e:
        raise ErrorLatex("Error de conexión durante la descarga.") from e


def _descomprimir_zip(ruta_zip, progreso):
    staging = prefs.TINYTEX_DIR + ".tmp"
    if os.path.exists(staging):
        shutil.rmtree(staging, ignore_errors=True)
    if os.path.exists(prefs.TINYTEX_DIR):
        shutil.rmtree(prefs.TINYTEX_DIR, ignore_errors=True)
    os.makedirs(staging)
    with zipfile.ZipFile(ruta_zip) as zf:
        infos = zf.infolist()
        total = sum(i.file_size for i in infos) or 1
        hecho = 0
        progreso(0, total if total > 1 else None)
        for i in infos:
            zf.extract(i, staging)
            hecho += i.file_size
            progreso(hecho, total)
    tops = [
        d
        for d in os.listdir(staging)
        if os.path.isdir(os.path.join(staging, d))
    ]
    raiz = staging
    if len(tops) == 1:
        raiz = os.path.join(staging, tops[0])
    pdflatex = os.path.join(raiz, "bin", "windows", "pdflatex.exe")
    if not os.path.isfile(pdflatex):
        shutil.rmtree(staging, ignore_errors=True)
        raise ErrorLatex("El archivo de TinyTeX descargado no parece válido (falta pdflatex.exe).")
    os.makedirs(prefs.TINYTEX_DIR)
    for nombre in os.listdir(raiz):
        shutil.move(os.path.join(raiz, nombre), prefs.TINYTEX_DIR)
    shutil.rmtree(staging, ignore_errors=True)
    return os.path.join(prefs.TINYTEX_DIR, "bin", "windows", "pdflatex.exe")


def install_tinytex(progreso):
    """Descarga e instala TinyTeX. progreso(done, total) con total None si se desconoce."""
    os.makedirs(prefs.APP_DIR, exist_ok=True)
    tmp = os.path.join(prefs.APP_DIR, "descarga-tinytex")
    for url in TINYTEX_URLS:
        progreso(0, None)
        _descargar(url, tmp, progreso)
        try:
            pdflatex = _descomprimir_zip(tmp, progreso)
            break
        except (zipfile.BadZipFile, OSError) as e:
            raise ErrorLatex(f"El archivo descargado no se pudo descomprimir: {e}") from e
    if os.path.exists(tmp):
        os.remove(tmp)
    if not _check(pdflatex):
        raise ErrorLatex("TinyTeX se instaló pero pdflatex no funciona.")
    prefs.set("latex_path", pdflatex)
    return pdflatex


def _leer_log(ruta):
    try:
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _parsear_errores(log):
    lineas = log.splitlines()
    errores = []
    for i, l in enumerate(lineas):
        if not l.startswith("!"):
            continue
        msg = l[2:].strip()
        if "not found" in msg:
            ini = msg.find("`")
            fin = msg.find("'", ini)
            nombre = msg[ini + 1:fin] if ini != -1 and fin != -1 else ""
            titulo = "Falta un paquete LaTeX"
            if nombre:
                titulo += f" ({nombre})"
            errores.append(f"{titulo}. Instala el paquete con el administrador de tu TeX o vuelve a ejecutar el instalador de TinyTeX.")
            continue
        contexto = []
        for j in range(i + 1, min(i + 6, len(lineas))):
            if lineas[j].startswith("!"):
                break
            if not lineas[j].strip():
                continue
            contexto.append(lineas[j].strip())
            if "l." in lineas[j]:
                break
        detalle = " | ".join(contexto[:3])
        errores.append(f"{msg} ({detalle})" if detalle else msg)
    if not errores:
        if "Emergency stop" in log:
            errores.append("Compilación detenida por un error fatal.")
        elif "Fatal error" in log:
            errores.append("Error fatal de LaTeX.")
        elif "File ended while scanning" in log:
            errores.append("Hay una llave { o } sin cerrar en el contenido.")
    return errores[:25]


def find_xelatex():
    p = find_pdflatex()
    if p:
        candidato = os.path.join(os.path.dirname(p), "xelatex.exe")
        if os.path.isfile(candidato):
            return candidato
    return shutil.which("xelatex")


_CJK_RE = None


def _usa_xelatex(tex):
    global _CJK_RE
    if _CJK_RE is None:
        import re as _re

        _CJK_RE = _re.compile(
            "[\u4e00-\u9fff\uff00-\uffef\u3040-\u30ff\uac00-\ud7af\uf900-\ufaff]"
        )
    return bool(_CJK_RE.search(tex))


def compile(tex, foto=None, extras=None):
    pdflatex = find_pdflatex()
    if not pdflatex:
        return {
            "ok": False,
            "pdf": None,
            "errores": [
                "No se encontró un motor LaTeX. Configúralo en Preferencias o instálalo desde el asistente."
            ],
        }
    con_cjk = _usa_xelatex(tex)
    motor = find_xelatex() if con_cjk else pdflatex
    if con_cjk and not motor:
        return {
            "ok": False,
            "pdf": None,
            "errores": [
                "El CV contiene texto en chino y necesita XeLaTeX. Instala TinyTeX (o una distribución completa) desde el asistente."
            ],
        }
    with _CANDADO:
        return _compilar_sin_candado(motor, tex, foto, extras)


def _copiar_pdf_estable(origen):
    """Copia el PDF a CACHE_DIR/out para que la exportación no compita con la próxima compilación."""
    destino_dir = os.path.join(prefs.CACHE_DIR, "out")
    os.makedirs(destino_dir, exist_ok=True)
    destino = os.path.join(destino_dir, "result_" + uuid.uuid4().hex + ".pdf")
    try:
        shutil.copy2(origen, destino)
    except OSError:
        try:
            shutil.copyfile(origen, destino)
        except OSError:
            return origen
    return destino


def _compilar_sin_candado(pdflatex, tex, foto=None, extras=None):
    os.makedirs(prefs.BUILD_DIR, exist_ok=True)
    for nombre in os.listdir(prefs.BUILD_DIR):
        try:
            os.remove(os.path.join(prefs.BUILD_DIR, nombre))
        except OSError:
            pass
    main_tex = os.path.join(prefs.BUILD_DIR, "main.tex")
    with open(main_tex, "w", encoding="utf-8") as f:
        f.write(tex)
    if foto and os.path.isfile(foto):
        ext = os.path.splitext(foto)[1].lower()
        if ext in FOTOS_PERMITIDAS:
            try:
                shutil.copy2(foto, os.path.join(prefs.BUILD_DIR, "foto" + ext))
            except OSError:
                pass
    for nombre, origen in (extras or {}).items():
        if os.path.isfile(origen):
            try:
                shutil.copy2(origen, os.path.join(prefs.BUILD_DIR, nombre))
            except OSError:
                pass
    try:
        proc = subprocess.run(
            [
                pdflatex,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory", prefs.BUILD_DIR,
                "main.tex",
            ],
            cwd=prefs.BUILD_DIR,
            capture_output=True,
            timeout=600,
            creationflags=_FLAGS_SUBPROCESO,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "pdf": None, "errores": ["La compilación tardó demasiado."]}
    pdf = os.path.join(prefs.BUILD_DIR, "main.pdf")
    if os.path.isfile(pdf):
        return {"ok": True, "pdf": _copiar_pdf_estable(pdf), "errores": []}
    log = _leer_log(os.path.join(prefs.BUILD_DIR, "main.log"))
    errores = _parsear_errores(log)
    if not errores:
        errores = ["pdflatex no generó el PDF; revisa main.log."]
    return {"ok": False, "pdf": None, "errores": errores}