import hashlib
import os
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
import uuid
import zipfile

import messages
import prefs

TINYTEX_VERSION = "2026.08"
TINYTEX_URLS = [
    f"https://github.com/rstudio/tinytex-releases/releases/download/v{TINYTEX_VERSION}/TinyTeX-v{TINYTEX_VERSION}.zip",
]
ALLOWED_PHOTOS = {".jpg", ".jpeg", ".png"}
_LOCK = threading.Lock()
_SUBPROCESS_FLAGS = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW: no console window


class LatexError(Exception):
    pass


def _check(path):
    try:
        result = subprocess.run(
            [path, "-version"],
            capture_output=True,
            timeout=20,
            creationflags=_SUBPROCESS_FLAGS,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def find_pdflatex():
    path = prefs.get("latex_path")
    if path and os.path.isfile(path) and _check(path):
        return path
    bundled = os.path.join(prefs.TINYTEX_DIR, "bin", "windows", "pdflatex.exe")
    if os.path.isfile(bundled) and _check(bundled):
        return bundled
    found = shutil.which("pdflatex")
    if found:
        return found
    return None


def _raise_if_cancelled(cancel_event):
    """Abort with a localized error when the install was cancelled."""
    if cancel_event is not None and cancel_event.is_set():
        raise LatexError(messages.t("install_cancelled"))


def _download(url, destination, progress, cancel_event=None):
    request = urllib.request.Request(url, headers={"User-Agent": "CVLaTeX/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, open(destination, "wb") as f:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                _raise_if_cancelled(cancel_event)
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                progress(done, total)
    except (urllib.error.URLError, OSError) as e:
        raise LatexError(messages.t("install_download_error").format(error=e)) from e
    except KeyError as e:
        raise LatexError(messages.t("install_connection_error")) from e


def _sha256_file(path):
    """Hex SHA-256 digest of a local file."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_checksum(text):
    """First 64-character hex token of a .sha256 payload, or None."""
    for token in str(text or "").split():
        token = token.strip().lower()
        if len(token) == 64 and all(c in "0123456789abcdef" for c in token):
            return token
    return None


def verify_sha256(path, expected):
    """Verify that `path` has the SHA-256 digest `expected`.

    A missing/unnamed checksum or a mismatch raises LatexError with a
    localized message; a match returns True.
    """
    digest = _parse_checksum(expected)
    if not digest:
        raise LatexError(messages.t("install_checksum_unavailable"))
    if _sha256_file(path).lower() != digest:
        raise LatexError(messages.t("install_checksum_mismatch"))
    return True


def _fetch_checksum(url, cancel_event=None):
    """Download `<url>.sha256` and return its first hex digest.

    Raises LatexError with a localized message when the checksum cannot be
    fetched or parsed.
    """
    request = urllib.request.Request(url, headers={"User-Agent": "CVLaTeX/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            text = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise LatexError(messages.t("install_checksum_unavailable")) from e
    _raise_if_cancelled(cancel_event)
    digest = _parse_checksum(text)
    if not digest:
        raise LatexError(messages.t("install_checksum_unavailable"))
    return digest


def _extract_zip(zip_path, progress):
    staging = prefs.TINYTEX_DIR + ".tmp"
    if os.path.exists(staging):
        shutil.rmtree(staging, ignore_errors=True)
    if os.path.exists(prefs.TINYTEX_DIR):
        shutil.rmtree(prefs.TINYTEX_DIR, ignore_errors=True)
    os.makedirs(staging)
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        total = sum(i.file_size for i in infos) or 1
        done = 0
        progress(0, total if total > 1 else None)
        for info in infos:
            zf.extract(info, staging)
            done += info.file_size
            progress(done, total)
    directories = [
        d
        for d in os.listdir(staging)
        if os.path.isdir(os.path.join(staging, d))
    ]
    root = staging
    if len(directories) == 1:
        root = os.path.join(staging, directories[0])
    pdflatex = os.path.join(root, "bin", "windows", "pdflatex.exe")
    if not os.path.isfile(pdflatex):
        shutil.rmtree(staging, ignore_errors=True)
        raise LatexError(messages.t("install_invalid_zip"))
    os.makedirs(prefs.TINYTEX_DIR)
    for name in os.listdir(root):
        shutil.move(os.path.join(root, name), prefs.TINYTEX_DIR)
    shutil.rmtree(staging, ignore_errors=True)
    return os.path.join(prefs.TINYTEX_DIR, "bin", "windows", "pdflatex.exe")


def install_tinytex(progress, cancel_event=None):
    """Download and install TinyTeX. progress(done, total), total None if unknown.

    Pass a ``threading.Event`` as ``cancel_event`` to abort promptly: the
    download loop checks it on every chunk and it is checked again before
    extraction. Aborting raises LatexError with a localized message.
    """
    _raise_if_cancelled(cancel_event)
    os.makedirs(prefs.APP_DIR, exist_ok=True)
    tmp = os.path.join(prefs.APP_DIR, "tinytex-download")
    pdflatex = None
    try:
        for url in TINYTEX_URLS:
            progress(0, None)
            _download(url, tmp, progress, cancel_event)
            _raise_if_cancelled(cancel_event)
            checksum = _fetch_checksum(url + ".sha256", cancel_event)
            verify_sha256(tmp, checksum)
            try:
                pdflatex = _extract_zip(tmp, progress)
                break
            except (zipfile.BadZipFile, OSError) as e:
                raise LatexError(messages.t("install_unzip_error").format(error=e)) from e
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    if not pdflatex or not _check(pdflatex):
        raise LatexError(messages.t("install_broken"))
    prefs.set("latex_path", pdflatex)
    return pdflatex


def _read_log(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _parse_errors(log):
    lines = log.splitlines()
    errors = []
    for i, line in enumerate(lines):
        if not line.startswith("!"):
            continue
        message = line[2:].strip()
        if "not found" in message:
            start = message.find("`")
            end = message.find("'", start)
            name = message[start + 1:end] if start != -1 and end != -1 else ""
            suffix = f" ({name})" if name else ""
            errors.append(messages.t("compile_missing_package").format(package=suffix))
            continue
        context = []
        for j in range(i + 1, min(i + 6, len(lines))):
            if lines[j].startswith("!"):
                break
            if not lines[j].strip():
                continue
            context.append(lines[j].strip())
            if "l." in lines[j]:
                break
        detail = " | ".join(context[:3])
        errors.append(f"{message} ({detail})" if detail else message)
    if not errors:
        if "Emergency stop" in log:
            errors.append(messages.t("compile_emergency_stop"))
        elif "Fatal error" in log:
            errors.append(messages.t("compile_fatal_error"))
        elif "File ended while scanning" in log:
            errors.append(messages.t("compile_unclosed_brace"))
    return errors[:25]


def find_xelatex():
    path = find_pdflatex()
    if path:
        candidate = os.path.join(os.path.dirname(path), "xelatex.exe")
        if os.path.isfile(candidate):
            return candidate
    return shutil.which("xelatex")


_CJK_RE = None
_FONTSPEC_RE = None


def _uses_xelatex(tex):
    """True when the document must be compiled with XeLaTeX.

    XeLaTeX is required for CJK text, but also for any document that loads
    `fontspec`: pdflatex aborts on it with "fontspec requires XeTeX or
    LuaTeX" even when the document has no CJK glyph at all (e.g. an empty
    CV whose zh font_engine emits fontspec).
    """
    global _CJK_RE, _FONTSPEC_RE
    if _CJK_RE is None:
        import re

        _CJK_RE = re.compile(
            "[\u4e00-\u9fff\uff00-\uffef\u3040-\u30ff\uac00-\ud7af\uf900-\ufaff]"
        )
        _FONTSPEC_RE = re.compile(
            r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{fontspec\}|\\fontspec"
        )
    return bool(_CJK_RE.search(tex)) or bool(_FONTSPEC_RE.search(tex))


def compile(tex, photo=None, extras=None):
    pdflatex = find_pdflatex()
    if not pdflatex:
        return {
            "ok": False,
            "pdf": None,
            "errores": [messages.t("compile_no_engine")],
        }
    needs_xelatex = _uses_xelatex(tex)
    engine = find_xelatex() if needs_xelatex else pdflatex
    if needs_xelatex and not engine:
        return {
            "ok": False,
            "pdf": None,
            "errores": [messages.t("compile_needs_xelatex")],
        }
    with _LOCK:
        return _compile_unlocked(engine, tex, photo, extras)


def _copy_stable_pdf(source):
    """Copy the PDF to CACHE_DIR/out so exporting does not race the next compile."""
    destination_dir = os.path.join(prefs.CACHE_DIR, "out")
    os.makedirs(destination_dir, exist_ok=True)
    destination = os.path.join(destination_dir, "result_" + uuid.uuid4().hex + ".pdf")
    try:
        shutil.copy2(source, destination)
    except OSError:
        try:
            shutil.copyfile(source, destination)
        except OSError:
            return source
    return destination


def _compile_unlocked(engine, tex, photo=None, extras=None):
    os.makedirs(prefs.BUILD_DIR, exist_ok=True)
    for name in os.listdir(prefs.BUILD_DIR):
        try:
            os.remove(os.path.join(prefs.BUILD_DIR, name))
        except OSError:
            pass
    main_tex = os.path.join(prefs.BUILD_DIR, "main.tex")
    with open(main_tex, "w", encoding="utf-8") as f:
        f.write(tex)
    if photo and os.path.isfile(photo):
        ext = os.path.splitext(photo)[1].lower()
        if ext in ALLOWED_PHOTOS:
            try:
                shutil.copy2(photo, os.path.join(prefs.BUILD_DIR, "foto" + ext))
            except OSError:
                pass
    for name, source in (extras or {}).items():
        if os.path.isfile(source):
            try:
                shutil.copy2(source, os.path.join(prefs.BUILD_DIR, name))
            except OSError:
                pass
    try:
        subprocess.run(
            [
                engine,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory", prefs.BUILD_DIR,
                "main.tex",
            ],
            cwd=prefs.BUILD_DIR,
            capture_output=True,
            timeout=600,
            creationflags=_SUBPROCESS_FLAGS,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "pdf": None, "errores": [messages.t("compile_timeout")]}
    pdf = os.path.join(prefs.BUILD_DIR, "main.pdf")
    if os.path.isfile(pdf):
        return {"ok": True, "pdf": _copy_stable_pdf(pdf), "errores": []}
    log = _read_log(os.path.join(prefs.BUILD_DIR, "main.log"))
    errors = _parse_errors(log)
    if not errors:
        errors = [messages.t("compile_no_pdf")]
    return {"ok": False, "pdf": None, "errores": errors}
