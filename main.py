"""pywebview shell for CVLaTeX plus the local HTTP server that feeds the UI.

`Api` methods are the JavaScript bridge (`window.pywebview.api.*`); the frozen
bridge surface is pinned by tests/test_frontend.py and documented in
docs/DEVELOPMENT.md. The local server (random
127.0.0.1 port) serves `web/` at `/`, compiled PDFs at `/preview/` and uploaded
media at `/media/`.
"""

import base64
import hmac
import http.server
import json
import mimetypes
import os
import re
import secrets
import shutil
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

import webview

import docx_gen
import latex_engine
import latex_gen
import messages
import prefs
import tex_datos

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
ICON_PATH = os.path.join(BASE_DIR, "assets", "CVLaTex.ico")
ROUTES = {
    "/app.js": os.path.join(WEB_DIR, "app.js"),
    "/style.css": os.path.join(WEB_DIR, "style.css"),
    "/i18n.js": os.path.join(WEB_DIR, "i18n.js"),
}
# Local HTTP server hardening: the app window is the only allowed client.
# A per-session secret guards every route; the browser gets it once in the
# window URL and then echoes it as a SameSite=Strict cookie for assets.
SESSION_COOKIE = "cvlatex_session"
TOKEN_PARAM = "token"
# Flat media files the app itself drops in CACHE_DIR (foto/logo/recorte plus
# uuid4().hex, and the cv_ prefix used by materialize_media()). Anything else
# in the cache (build/, out/, backups) stays unreachable over HTTP.
MEDIA_NAME_RE = re.compile(
    r"^(?:foto|logo|recorte|cv)_[0-9a-f]{32}\.(?:png|jpg|jpeg)$", re.IGNORECASE
)
PDF_NAME_RE = re.compile(r"^[^/\\]+\.pdf$", re.IGNORECASE)


def window_title(ui_language):
    """Native window title for the given UI language (English by default)."""
    language = str(ui_language or "").strip().lower()
    if language == "es":
        return "CVLaTeX — Editor de CV"
    if language == "zh":
        return "CVLaTeX — 简历编辑器"
    if language == "ru":
        return "CVLaTeX — Редактор резюме"
    return "CVLaTeX — CV Editor"

AUTOSAVE_FILE = "autosave.cvjson"
# The restore point is written atomically: `<file>.tmp` is flushed and fsynced
# in the same directory and then renamed over the primary, while the previous
# good copy stays as `<file>.bak` for autosave_read() to fall back to.
AUTOSAVE_TMP_FILE = AUTOSAVE_FILE + ".tmp"
AUTOSAVE_BAK_FILE = AUTOSAVE_FILE + ".bak"
CACHE_MAX_AGE_DAYS = 30
MEDIA_EXTS = (".jpg", ".jpeg", ".png")
MEDIA_FIELDS = ("photo", "photo_original", "photo_crop", "school_logo")
LOGO_FIELDS = ("work", "internships", "projects", "university_projects", "education")


class Handler(http.server.BaseHTTPRequestHandler):
    # Per-session secret, set by _start_server() before the server accepts
    # connections. Empty means "locked": every request is rejected.
    TOKEN = ""
    _set_session_cookie = False

    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        """Add the security headers to every response, including errors."""
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if self._set_session_cookie:
            self.send_header(
                "Set-Cookie",
                "%s=%s; Path=/; HttpOnly; SameSite=Strict"
                % (SESSION_COOKIE, self.TOKEN),
            )
        super().end_headers()
        self._set_session_cookie = False

    def _serve(self, path):
        try:
            if not os.path.isfile(path):
                self.send_error(404)
                return
            content_type, _ = mimetypes.guess_type(path)
            if content_type is None:
                content_type = "application/octet-stream"
            with open(path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except (OSError, ConnectionError):
            pass

    def _request_path(self):
        return urlsplit(self.path).path

    def _no_content(self):
        self.send_response(204)
        self.end_headers()

    def _serve_within(self, base, relative):
        """Serve a file contained in `base`; a path escaping it returns 404."""
        try:
            real_base = os.path.realpath(base)
            target = os.path.realpath(os.path.join(real_base, relative))
            if os.path.commonpath([os.path.normcase(real_base), os.path.normcase(target)]) != os.path.normcase(real_base):
                self.send_error(404)
                return
        except ValueError:
            self.send_error(404)
            return
        self._serve(target)

    def _serve_media(self, relative):
        """Only flat app-created media files; build/out/tex stay unreachable."""
        if not MEDIA_NAME_RE.fullmatch(relative):
            self.send_error(404)
            return
        self._serve_within(prefs.CACHE_DIR, relative)

    def _serve_preview(self, relative):
        """Only flat PDFs produced by the compiler in BUILD_DIR."""
        if not PDF_NAME_RE.fullmatch(relative):
            self.send_error(404)
            return
        self._serve_within(prefs.BUILD_DIR, relative)

    def _authorized(self):
        """Host, Origin and session-token gate shared by every route."""
        port = self.server.server_address[1]
        expected = "127.0.0.1:%d" % port
        if self.headers.get("Host") != expected:
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin != "http://" + expected:
            return False
        token = self.TOKEN
        if not token:
            return False
        supplied = parse_qs(urlsplit(self.path).query).get(TOKEN_PARAM, [""])[0]
        expected_token = token.encode("utf-8")
        if supplied and hmac.compare_digest(supplied.encode("utf-8"), expected_token):
            self._set_session_cookie = True
            return True
        for piece in self.headers.get("Cookie", "").split(";"):
            name, _, value = piece.strip().partition("=")
            if name == SESSION_COOKIE and hmac.compare_digest(
                value.encode("utf-8"), expected_token
            ):
                return True
        return False

    def do_GET(self):
        self._set_session_cookie = False
        if not self._authorized():
            self.send_error(403)
            return
        path = self._request_path()
        if path in ("/", "/index.html"):
            self._serve(os.path.join(WEB_DIR, "index.html"))
        elif path in ROUTES:
            self._serve(ROUTES[path])
        elif path.startswith("/preview/"):
            self._serve_preview(path[len("/preview/"):])
        elif path.startswith("/media/"):
            self._serve_media(path[len("/media/"):])
        elif path.startswith("/pdfjs/"):
            self._serve_within(os.path.join(WEB_DIR, "pdfjs"), path[len("/pdfjs/"):])
        elif path == "/favicon.ico":
            self._no_content()
        else:
            self.send_error(404)


class Api:
    def __init__(self, win):
        self._w = win
        self._dirty = False
        self._force_close = False
        self._cancel_event = None
        self._media_cache = {}
        self._last_tex = None
        self._last_result = None

    def _push(self, name, data):
        # ensure_ascii=True is a hard requirement, not a cosmetic choice:
        # pywebview's GTK backend passes len(script) (characters) to WebKit's
        # evaluate_javascript(), which expects a byte length. Any raw non-ASCII
        # character therefore truncates the script by (utf8_bytes - chars)
        # bytes and WebKit rejects it with "SyntaxError: Unexpected EOF"; the
        # push is then lost and the frontend's single-flight flag never clears.
        # Escaping every non-ASCII character keeps the script pure ASCII, so
        # len(script) == byte length and the JSON is decoded unchanged by JS.
        try:
            self._w.evaluate_js(
                "window.%s(%s);" % (name, json.dumps(data, ensure_ascii=True))
            )
        except Exception:
            pass

    # ------------------------------------------------------------- window

    def set_dirty(self, flag):
        """Track whether the form has unsaved changes (close guard)."""
        self._dirty = bool(flag)
        return {"ok": True}

    def quit_app(self):
        """Force-close the window, bypassing the dirty close guard."""
        self._force_close = True
        try:
            self._w.destroy()
        except Exception:
            pass
        return {"ok": True}

    def _on_closing(self):
        """Window `closing` handler: hold the window open while dirty.

        Returning False cancels the close and asks the UI through
        `window.__onCloseRequest`; the UI then saves, exits without saving or
        cancels. Never call `evaluate_js` synchronously here: this handler runs
        inside WinForms `FormClosing` on the UI thread, and `evaluate_js` would
        block waiting for a JS result that needs that same UI thread
        (deadlock). The request is pushed from a daemon thread while the close
        is cancelled immediately.
        """
        if self._force_close or not self._dirty:
            return True
        threading.Thread(
            target=self._push, args=("__onCloseRequest", {}), daemon=True
        ).start()
        return False

    # ------------------------------------------------------------ compile

    def compile(self, data, compile_id):
        threading.Thread(target=self._compile_thread, args=(data, compile_id), daemon=True).start()
        return "ok"

    def _compile_thread(self, data, compile_id):
        try:
            tex = latex_gen.build_tex(data, prefs.load())
            result = self._cached_result(tex)
            if result is None:
                result = latex_engine.compile(tex, data.get("photo"), latex_gen.extra_logos(data))
                self._remember_success(tex, result)
            result["tex"] = tex
        except Exception as e:
            result = {"ok": False, "pdf": None, "errores": [messages.t("internal_error").format(error=e)]}
        result["id"] = compile_id
        self._push("__onCompile", result)

    def compile_tex(self, tex, compile_id, data=None):
        threading.Thread(target=self._compile_tex_thread, args=(tex, compile_id, data), daemon=True).start()
        return "ok"

    def _compile_tex_thread(self, tex, compile_id, data=None):
        try:
            result = self._cached_result(tex)
            if result is None:
                result = latex_engine.compile(
                    tex,
                    data.get("photo") if data else None,
                    latex_gen.extra_logos(data) if data else None,
                )
                self._remember_success(tex, result)
        except Exception as e:
            result = {"ok": False, "pdf": None, "errores": [messages.t("internal_error").format(error=e)]}
        result["id"] = compile_id
        result["tex"] = tex
        self._push("__onCompile", result)

    def _cached_result(self, tex):
        """Return the successful result for an identical tex whose pdf exists."""
        result = self._last_result
        if (
            self._last_tex == tex
            and isinstance(result, dict)
            and result.get("ok")
            and result.get("pdf")
            and os.path.isfile(result["pdf"])
        ):
            return dict(result)
        return None

    def _remember_success(self, tex, result):
        """Keep the last successful tex/result pair for the skip-recompile."""
        if isinstance(result, dict) and result.get("ok"):
            self._last_tex = tex
            self._last_result = {
                "ok": True,
                "pdf": result.get("pdf"),
                "errores": list(result.get("errores") or []),
            }

    # --------------------------------------------------------------- data

    def init(self):
        current = prefs.load()
        latex_path = latex_engine.find_pdflatex()
        return {
            "prefs": current,
            "latex_ok": latex_path is not None,
            "needs_setup": latex_path is None and not current.get("setup_dismissed"),
            "needs_language": not current.get("ui_language_chosen"),
            "platform": sys.platform,
        }

    def empty_data(self):
        """New CV data whose document language follows the interface language.

        `latex_gen.empty_data()` stays canonical (`zh`) for tests; the bridge
        maps the stored UI language (es/en/zh, Russian falls back to English)
        so a new CV does not default to the xelatex path by accident.
        """
        data = latex_gen.empty_data()
        ui = str(prefs.get("ui_language") or "en").strip().lower()
        data["cv_language"] = ui if ui in ("zh", "es", "en") else "en"
        return data

    def load_sample(self, cv_language=None):
        try:
            import ejemplo

            try:
                lang = str(cv_language or "es").strip().lower()
            except Exception:
                lang = "es"
            if lang not in ("zh", "es", "en"):
                lang = "es"
            return {"ok": True, "datos": ejemplo.sample_data(lang)}
        except Exception as e:
            return {"ok": False, "errores": [messages.t("internal_error").format(error=e)]}

    def template_colors(self, template=None):
        """Accent colors defined by the given template (classic by default)."""
        try:
            name = str(template or "classic").strip().lower()
            if name not in latex_gen.TEMPLATES:
                name = "classic"
            path = os.path.join(latex_gen.BASE_DIR, "templates", latex_gen.TEMPLATE_FILES[name])
            with open(path, "r", encoding="utf-8") as f:
                tex = f.read()
            return {"ok": True, "colores": latex_gen.template_colors(tex)}
        except Exception as e:
            return {"ok": False, "errores": [messages.t("internal_error").format(error=e)]}

    # -------------------------------------------------------------- files

    def choose_file(self, file_types, save, suggested_name):
        if save:
            path = self._w.create_file_dialog(
                webview.FileDialog.SAVE, save_filename=suggested_name, file_types=file_types
            )
        else:
            path = self._w.create_file_dialog(
                webview.FileDialog.OPEN, file_types=file_types
            )
        if isinstance(path, (list, tuple)):
            path = path[0] if path else None
        return path

    def choose_photo(self, kind=None):
        prefix = "logo" if str(kind or "").strip().lower() == "logo" else "foto"
        path = self.choose_file(("Imágenes (*.jpg;*.jpeg;*.png)",), False, None)
        if not path:
            return {"ok": False}
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext not in latex_engine.ALLOWED_PHOTOS:
                return {"ok": False, "error": messages.t("export_bad_format")}
            os.makedirs(prefs.CACHE_DIR, exist_ok=True)
            name = "%s_%s%s" % (prefix, uuid.uuid4().hex, ext)
            destination = os.path.join(prefs.CACHE_DIR, name)
            shutil.copy2(path, destination)
            return {"ok": True, "path": destination, "url": "/media/" + name}
        except OSError as e:
            return {"ok": False, "error": str(e)}

    def save_image(self, data_url, kind=None):
        """Save an image sent as a base64 PNG/JPEG data URL.

        Accepts only ``data:image/png;base64,`` and ``data:image/jpeg;base64,``
        headers with strict base64. The file prefix is ``foto`` unless ``kind``
        is logo or recorte.
        """
        try:
            if not isinstance(data_url, str):
                raise ValueError(messages.t("image_invalid_data_url"))
            match = re.fullmatch(
                r"data:(image/(?:png|jpeg));base64,([A-Za-z0-9+/]*={0,2})",
                data_url,
            )
            if match is None:
                raise ValueError(messages.t("image_invalid_mime"))
            mime, b64 = match.group(1), match.group(2)
            image_bytes = base64.b64decode(b64, validate=True)
            if not image_bytes:
                raise ValueError(messages.t("image_empty"))
            prefix = kind if kind in ("foto", "logo", "recorte") else "foto"
            ext = ".png" if mime == "image/png" else ".jpg"
            os.makedirs(prefs.CACHE_DIR, exist_ok=True)
            name = "%s_%s%s" % (prefix, uuid.uuid4().hex, ext)
            destination = os.path.join(prefs.CACHE_DIR, name)
            with open(destination, "wb") as f:
                f.write(image_bytes)
            return {"ok": True, "path": destination, "url": "/media/" + name}
        except Exception as e:
            return {"ok": False, "errores": [str(e)]}

    def export_pdf(self, data, manual_tex=None):
        try:
            if manual_tex:
                # The embedded data block is always refreshed from the data,
                # even when the user compiles their own .tex.
                tex = tex_datos.embed(manual_tex, data)
                photo = None
                extras = None
            else:
                tex = latex_gen.build_tex(data, prefs.load())
                photo = data.get("photo")
                extras = latex_gen.extra_logos(data)
            result = latex_engine.compile(tex, photo, extras)
            if not result["ok"]:
                return {"ok": False, "errores": result["errores"]}
            suggested = "CV.pdf"
            if data.get("name"):
                suggested = "CV-%s.pdf" % data["name"].strip().replace(" ", "_")
            path = self.choose_file(("PDF (*.pdf)",), True, suggested)
            if not path:
                return {"ok": False, "cancelado": True}
            shutil.copy2(result["pdf"], path)
            return {"ok": True, "ruta": path}
        except Exception as e:
            return {"ok": False, "errores": [str(e)]}

    def export_tex(self, data, manual_tex=None):
        try:
            tex = manual_tex if manual_tex else latex_gen.build_tex(data, prefs.load())
            # Refresh the data block even when there is a manual tex.
            tex = tex_datos.embed(tex, data)
            suggested = "CV.tex"
            if data.get("name"):
                suggested = "CV-%s.tex" % data["name"].strip().replace(" ", "_")
            path = self.choose_file(("LaTeX (*.tex)",), True, suggested)
            if not path:
                return {"ok": False, "cancelado": True}
            with open(path, "w", encoding="utf-8") as f:
                f.write(tex)
            return {"ok": True, "ruta": path}
        except OSError as e:
            return {"ok": False, "errores": [str(e)]}

    def export_docx(self, data):
        try:
            suggested = "CV.docx"
            if data.get("name"):
                suggested = "CV-%s.docx" % data["name"].strip().replace(" ", "_")
            path = self.choose_file(("Word (*.docx)",), True, suggested)
            if not path:
                return {"ok": False, "cancelado": True}
            # docx_gen does not depend on LaTeX nor pywebview.
            docx_gen.export(data, prefs.load(), path)
            return {"ok": True, "ruta": path}
        except Exception as e:
            return {"ok": False, "errores": [str(e)]}

    def export_cv(self, data, path=None):
        try:
            if isinstance(path, str) and path:
                # Direct save (used by the close guard): no file dialog.
                target = path
            else:
                suggested = "mi_cv.cvjson"
                if data.get("name"):
                    suggested = "%s.cvjson" % data["name"].strip().replace(" ", "_")
                target = self.choose_file(("CVLaTeX (*.cvjson)",), True, suggested)
                if not target:
                    return {"ok": False, "cancelado": True}
            content = {
                "version": 3,
                "data": data,
                "media": collect_media(data, self._media_cache),
            }
            with open(target, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            return {"ok": True, "ruta": target}
        except OSError as e:
            return {"ok": False, "errores": [str(e)]}

    def open_cv(self):
        path = self.choose_file(("CVLaTeX (*.cvjson)",), False, None)
        if not path:
            return {"ok": False, "cancelado": True}
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
            data, media = read_cvjson(content, path)
            if data is None:
                return {"ok": False, "errores": [messages.t("open_invalid_file")]}
            try:
                data = migrate_data(data)
            except Exception as e:
                return {"ok": False, "errores": [messages.t("open_failed").format(error=e)]}
            data = materialize_media(data, media)
            fill_defaults(data)
            return {"ok": True, "datos": data, "ruta": path}
        except (OSError, UnicodeDecodeError, ValueError) as e:
            return {"ok": False, "errores": [messages.t("open_failed").format(error=e)]}

    # ----------------------------------------------------------- autosave

    def autosave(self, data):
        """Write the restore point atomically and keep the previous one.

        The JSON goes to `<file>.tmp` in APP_DIR, is flushed and fsynced, the
        current good file is copied to `<file>.bak` and only then `os.replace`
        promotes the tmp file. A crash mid-write therefore leaves either the
        old primary or the old .bak readable, never a truncated file.
        """
        target = os.path.join(prefs.APP_DIR, AUTOSAVE_FILE)
        tmp = os.path.join(prefs.APP_DIR, AUTOSAVE_TMP_FILE)
        backup = os.path.join(prefs.APP_DIR, AUTOSAVE_BAK_FILE)
        try:
            os.makedirs(prefs.APP_DIR, exist_ok=True)
            content = {
                "version": 3,
                "data": data,
                "media": collect_media(data, self._media_cache),
            }
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            if os.path.isfile(target):
                try:
                    shutil.copy2(target, backup)
                except OSError:
                    # Best-effort: a missing backup must not block the save.
                    pass
            os.replace(tmp, target)
            return {"ok": True}
        except Exception as e:
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except OSError:
                pass
            return {"ok": False, "errores": [str(e)]}

    def _read_autosave_file(self, path):
        """Plain data of one autosave file, or None. Never raises."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
            if not isinstance(content, dict):
                return None
            version = content.get("version")
            if version == 3:
                data, media = content.get("data"), content.get("media")
            elif version == 2:
                data, media = content.get("datos"), content.get("medios")
            elif "datos" in content:
                # v1 envelope without embedded media.
                data, media = content.get("datos"), None
            else:
                # Old autosave: the JSON was the data dict itself.
                data, media = content, None
            if not isinstance(data, dict):
                return None
            data = migrate_data(data)
            data = materialize_media(data, media)
            return fill_defaults(data)
        except Exception:
            return None

    def autosave_read(self):
        """Return the restore point ready for the form, or None.

        Tries `autosave.cvjson` first and falls back to `autosave.cvjson.bak`
        when the primary is missing or corrupt. Mirrors `open_cv`: migrates
        the data, materializes the embedded media of a v2/v3 envelope into
        CACHE_DIR and fills the missing schema keys. The frontend receives
        plain data, never the {version, data, media} envelope. Never raises.
        """
        for name in (AUTOSAVE_FILE, AUTOSAVE_BAK_FILE):
            data = self._read_autosave_file(os.path.join(prefs.APP_DIR, name))
            if data is not None:
                return data
        return None

    def autosave_clear(self):
        """Delete the restore point: primary, .bak fallback and a stale .tmp."""
        try:
            for name in (AUTOSAVE_FILE, AUTOSAVE_BAK_FILE, AUTOSAVE_TMP_FILE):
                path = os.path.join(prefs.APP_DIR, name)
                if os.path.isfile(path):
                    os.remove(path)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "errores": [str(e)]}

    # ------------------------------------------------------------ LaTeX

    def import_tex(self):
        path = self.choose_file(("LaTeX (*.tex)",), False, None)
        if not path:
            return {"ok": False, "cancelado": True}
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                tex = f.read()
            try:
                data = tex_datos.extract(tex)
            except tex_datos.MissingDataBlock:
                if "CVLaTeX" in tex:
                    msg = messages.t("import_no_data")
                else:
                    msg = messages.t("import_incompatible")
                return {"ok": False, "errores": [msg]}
            except tex_datos.InvalidDataBlock:
                return {"ok": False, "errores": [messages.t("import_damaged")]}
            try:
                data = migrate_data(data)
            except Exception as e:
                return {"ok": False, "errores": [messages.t("open_failed").format(error=e)]}
            fill_defaults(data)
            if data.get("template") not in latex_gen.TEMPLATES:
                data["template"] = "classic"
            return {"ok": True, "datos": data, "ruta": path}
        except (OSError, UnicodeDecodeError, ValueError) as e:
            return {"ok": False, "errores": [messages.t("open_failed").format(error=e)]}

    def install_latex(self):
        self._cancel_event = threading.Event()
        cancel_event = self._cancel_event
        threading.Thread(target=self._install_thread, args=(cancel_event,), daemon=True).start()
        return "ok"

    def cancel_install(self):
        """Abort the in-flight TinyTeX install, if any."""
        cancel_event = self._cancel_event
        if cancel_event is None:
            return {"ok": False, "cancelado": True}
        cancel_event.set()
        return {"ok": True}

    def _install_thread(self, cancel_event):
        warnings = []

        def progress(done, total):
            self._push("__onInstallProgress", {"hecho": done, "total": total})

        def warn(message):
            # Non-fatal warnings (e.g. checksum unavailable): show them live
            # and repeat them with the success message.
            warnings.append(message)
            self._push("__onInstallProgress", {"warning": message})

        try:
            path = latex_engine.install_tinytex(progress, cancel_event, warn)
            result = {"ok": True, "msg": messages.t("install_done"), "path": path}
            if warnings:
                result["warning"] = " ".join(dict.fromkeys(warnings))
            self._push("__onInstallDone", result)
        except latex_engine.LatexError as e:
            self._push("__onInstallDone", {"ok": False, "msg": str(e)})
        except Exception as e:
            self._push("__onInstallDone", {"ok": False, "msg": messages.t("install_unexpected_error").format(error=e)})
        finally:
            if self._cancel_event is cancel_event:
                self._cancel_event = None

    def choose_latex_path(self):
        path = self.choose_file(("pdflatex.exe",), False, None)
        if not path:
            return {"ok": False, "cancelado": True}
        prefs.set("latex_path", path)
        return {"ok": True, "path": path}

    def check_latex(self):
        path = latex_engine.find_pdflatex()
        return {"ok": path is not None, "path": path}

    def open_preview(self):
        """Open the last compiled PDF with the system default viewer.

        Linux webviews cannot display a PDF inline, so the frontend offers
        this fallback when `init()` reports platform "linux". Uses the PDF of
        the last successful compile; without one it returns an error.
        """
        result = self._last_result if isinstance(self._last_result, dict) else {}
        pdf = result.get("pdf")
        if result.get("ok") and pdf and os.path.isfile(pdf):
            try:
                webbrowser.open(Path(pdf).as_uri())
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "errores": [str(e)]}
        return {"ok": False, "errores": [messages.t("preview_not_available")]}

    # ------------------------------------------------------------ prefs

    def set_prefs(self, key, value):
        prefs.set(key, value)
        if key == "ui_language":
            # Keep the native window title in sync; never fail the bridge call
            # when the window is not available (e.g. tests).
            try:
                self._w.set_title(window_title(value))
            except Exception:
                pass
        return prefs.load()

    def get_prefs(self):
        return prefs.load()

    def dismiss_setup(self):
        prefs.set("setup_dismissed", True)


def _block_text(value):
    """Convert to text without raising (hostile values fall back to "")."""
    try:
        return "" if value is None else str(value)
    except Exception:
        return ""


# Data key renames (legacy Spanish keys -> canonical English keys).
_DATA_RENAMES = {
    "idioma_cv": "cv_language",
    "plantilla": "template",
    "nombre": "name",
    "profesion": "profession",
    "telefono": "phone",
    "direccion": "address",
    "web": "website",
    "nacimiento": "birth_date",
    "nacionalidad": "nationality",
    "datos_extra": "extra_fields",
    "foto": "photo",
    "foto_original": "photo_original",
    "foto_recorte": "photo_crop",
    "foto_ancho_cm": "photo_width_cm",
    "foto_alto_cm": "photo_height_cm",
    "institucion_egresado": "school_name",
    "logo_egresado": "school_logo",
    "logo_egresado_ancho_cm": "school_logo_width_cm",
    "logo_egresado_alto_cm": "school_logo_height_cm",
    "perfil": "summary",
    "trabajo": "work",
    "pasantia": "internships",
    "proyectos": "projects",
    "proyectosu": "university_projects",
    "educacion": "education",
    "habilidades": "skills",
    "idiomas": "languages",
    "referencias": "references",
    "bloques": "blocks",
    "titulos_seccion": "section_titles",
    "secciones_ocultas": "hidden_sections",
    "orden_secciones": "section_order",
    "columnas": "columns",
}

# Renames inside each entry list (the remaining keys are preserved).
_ENTRY_RENAMES = {
    "work": {
        "modalidad": "work_mode", "puesto": "position", "empresa": "company",
        "desde": "start", "hasta": "end", "logros": "achievements",
    },
    "internships": {
        "modalidad": "work_mode", "puesto": "position", "empresa": "company",
        "desde": "start", "hasta": "end", "logros": "achievements",
    },
    "education": {
        "tipo": "degree_type", "titulo": "degree", "institucion": "institution",
        "desde": "start", "hasta": "end", "nota": "grade",
    },
    "projects": {
        "nombre": "name", "organizacion": "organization", "asignatura": "course",
        "desde": "start", "hasta": "end", "descripcion": "description",
        "resultado": "result", "enlace": "link",
    },
    "university_projects": {
        "nombre": "name", "organizacion": "organization", "asignatura": "course",
        "desde": "start", "hasta": "end", "descripcion": "description",
        "resultado": "result", "enlace": "link",
    },
    "skills": {"categoria": "category", "valores": "values"},
    "languages": {"idioma": "language", "nivel": "level"},
    "references": {"nombre": "name", "contacto": "contact"},
    "extra_fields": {"etiqueta": "label", "valor": "value"},
}

# Canonical select values; unknown values pass through (free text).
_TEMPLATE_VALUES = {
    "clasico": "classic", "moderno": "modern",
    "creativo": "creative", "chino": "chinese",
}
_WORK_MODES = {"Presencial": "onsite", "Híbrido": "hybrid", "Remoto": "remote"}
_DEGREE_TYPES = {
    "Primaria": "primary",
    "Secundaria (ESO)": "secondary",
    "Bachillerato": "high_school",
    "FP Grado Medio": "vocational_mid",
    "FP Grado Superior": "vocational_high",
    "Grado Universitario": "bachelor",
    "Ingeniería": "engineering",
    "Licenciatura": "licentiate",
    "Diplomatura": "diploma",
    "Arquitectura": "architecture",
    "Máster": "master",
    "Doctorado (PhD)": "phd",
    "Posgrado / Especialización": "postgraduate",
    "Curso / Certificación": "course",
    "Otro": "other",
}

# Legacy section keys -> canonical keys (LANG, anchors and columns).
_SECTION_RENAMES = {
    "perfil": "summary",
    "educacion": "education",
    "proyectos": "projects",
    "proyectosu": "university_projects",
    "pasantia": "internships",
    "trabajo": "work",
    "habilidades": "skills",
    "idiomas": "languages",
    "referencias": "references",
}

# Blocks: legacy keys and values -> canonical.
_BLOCK_RENAMES = {
    "tipo": "type", "estilo": "style", "posicion": "position", "titulo": "title",
    "contenido": "content", "modo": "mode", "columnas": "columns",
    "entradas": "entries",
}
_BLOCK_TYPE_ALIASES = {"separador": "separator", "seccion": "section", "listado": "list"}
_BLOCK_STYLES = {"linea": "line", "banda": "band", "espacio": "space"}
_BLOCK_MODES = {"columnas": "columns", "periodo": "period"}
_BLOCK_ANCHOR_ALIASES = dict(_SECTION_RENAMES)
_BLOCK_ANCHOR_ALIASES.update({"inicio": "start", "final": "end"})


def _rename_keys(d, mapping):
    """New dict with `mapping` keys translated; the rest are preserved.

    When the new and the old key coexist, the new one wins.
    """
    new = {}
    for key, value in d.items():
        target = mapping.get(key, key)
        if target not in new or key not in mapping:
            new[target] = value
    return new


def _migrate_option(value, mapping):
    """Canonical value of a select; unknown values pass through as free text."""
    if not isinstance(value, str):
        return value
    return mapping.get(value.strip(), value)


def _migrate_entries(key, entries):
    """Translate keys and values of an entry list to the new schema."""
    if not isinstance(entries, list):
        return entries
    mapping = _ENTRY_RENAMES.get(key) or {}
    new_entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            if key != "skills":
                new_entries.append(entry)
            continue
        entry = _rename_keys(entry, mapping)
        if key == "skills":
            if entry.get("category") or entry.get("values"):
                pass
            elif entry.get("nombre"):
                entry = {"category": entry.get("nombre"), "values": entry.get("nivel", "")}
            else:
                continue
        elif key in ("work", "internships") and "work_mode" in entry:
            entry["work_mode"] = _migrate_option(entry["work_mode"], _WORK_MODES)
        elif key == "education" and "degree_type" in entry:
            entry["degree_type"] = _migrate_option(entry["degree_type"], _DEGREE_TYPES)
        new_entries.append(entry)
    return new_entries


def _migrate_columns(value):
    if not isinstance(value, dict):
        return value
    try:
        return {_SECTION_RENAMES.get(k, k): v for k, v in value.items()}
    except Exception:
        return value


def sanitize_socials(socials):
    """Normalize the ``socials`` list; never raises.

    Every kept entry is a dict with the canonical keys ``network``/``label``/
    ``value``: the network falls back to ``other`` and entries whose value is
    empty (after stripping) are dropped.
    """
    try:
        if not isinstance(socials, (list, tuple)):
            return []
        clean = []
        for raw in socials:
            try:
                if not isinstance(raw, dict):
                    continue
                network = _block_text(raw.get("network")).strip()
                if network not in latex_gen.SOCIAL_NETWORKS:
                    network = "other"
                value = _block_text(raw.get("value"))
                if not value.strip():
                    continue
                clean.append({
                    "network": network,
                    "label": _block_text(raw.get("label")),
                    "value": value,
                })
            except Exception:
                continue
        return clean
    except Exception:
        return []


def _legacy_contact_label(cv_language, key):
    """LANG label of a legacy birth date/nationality, without its colon.

    Uses the CV language (Chinese by default) and falls back to the Spanish
    wording when that table or key is missing. Never raises.
    """
    try:
        language = cv_language or "zh"
    except Exception:
        language = "zh"
    try:
        table = latex_gen.LANG.get(language)
    except Exception:
        table = None
    if not isinstance(table, dict):
        table = latex_gen.LANG["es"]
    try:
        value = table.get(key)
    except Exception:
        value = None
    if not isinstance(value, str) or not value.strip():
        try:
            value = latex_gen.LANG["es"].get(key)
        except Exception:
            value = None
    if not isinstance(value, str):
        return ""
    return value.strip().rstrip(":").rstrip("：").strip()


def _migrate_legacy_contacts(data):
    """Move the legacy personal fields into socials/extra_fields (in place).

    Non-empty ``github``/``linkedin``/``website`` become socials entries and
    non-empty ``birth_date``/``nationality`` become extra fields (with the
    label translated to the CV language). The legacy keys are always removed,
    so a second pass changes nothing.
    """
    socials = data.get("socials")
    if isinstance(socials, (list, tuple)):
        socials = list(socials)
    else:
        socials = []
    for key in ("github", "linkedin", "website"):
        value = _block_text(data.get(key)).strip()
        if value:
            socials.append({"network": key, "label": "", "value": value})
        data.pop(key, None)
    data["socials"] = socials

    cv_language = data.get("cv_language")
    for key in ("birth_date", "nationality"):
        value = _block_text(data.get(key)).strip()
        if value:
            extra = data.get("extra_fields")
            if not isinstance(extra, list):
                extra = []
            extra.append({"label": _legacy_contact_label(cv_language, key), "value": value})
            data["extra_fields"] = extra
        data.pop(key, None)
    return data


def sanitize_blocks(blocks):
    """Normalize the free blocks list; never raises.

    Accepts blocks with legacy keys and values (tipo/estilo/posicion,
    seccion/listado, linea/banda/espacio...) and translates them to the
    canonical schema before sanitizing. Entries that are not a dict or have an
    unknown ``type`` are dropped; ``style``/``position``/``id`` are completed,
    ids are guaranteed unique and each block is rebuilt with only the
    canonical keys of its type.
    """
    try:
        if not isinstance(blocks, list):
            return []
        clean = []
        ids = set()
        for raw in blocks:
            try:
                if not isinstance(raw, dict):
                    continue
                raw = _rename_keys(raw, _BLOCK_RENAMES)
                block_type = str(raw.get("type") or "").strip()
                block_type = _BLOCK_TYPE_ALIASES.get(block_type, block_type)
                if block_type not in latex_gen.BLOCK_TYPES:
                    continue
                position = str(raw.get("position") or "").strip()
                position = _BLOCK_ANCHOR_ALIASES.get(position, position)
                if position not in latex_gen.BLOCK_ANCHORS:
                    position = "end"
                ident = raw.get("id")
                if not isinstance(ident, str) or not ident or ident in ids:
                    ident = uuid.uuid4().hex
                    while ident in ids:
                        ident = uuid.uuid4().hex
                ids.add(ident)
                if block_type == "separator":
                    style = str(raw.get("style") or "").strip()
                    style = _BLOCK_STYLES.get(style, style)
                    if style not in latex_gen.SEPARATOR_STYLES:
                        style = "line"
                    clean.append({
                        "id": ident,
                        "type": block_type,
                        "style": style,
                        "position": position,
                    })
                elif block_type == "list":
                    mode = _block_text(raw.get("mode")).strip()
                    mode = _BLOCK_MODES.get(mode, mode)
                    if mode not in latex_gen.LIST_MODES:
                        mode = "columns"
                    try:
                        columns = int(raw.get("columns") or 1)
                    except Exception:
                        columns = 1
                    columns = min(max(columns, 1), 3)
                    entries = []
                    raw_entries = raw.get("entries")
                    if isinstance(raw_entries, (list, tuple)):
                        for entry in raw_entries:
                            if not isinstance(entry, dict):
                                continue
                            entry = _rename_keys(
                                entry, {"titulo": "title", "detalle": "detail",
                                        "periodo": "period", "descripcion": "description"}
                            )
                            if mode == "period":
                                entries.append({
                                    "period": _block_text(entry.get("period")),
                                    "description": _block_text(entry.get("description")),
                                })
                            else:
                                entries.append({
                                    "title": _block_text(entry.get("title")),
                                    "detail": _block_text(entry.get("detail")),
                                })
                    clean.append({
                        "id": ident,
                        "type": block_type,
                        "mode": mode,
                        "title": _block_text(raw.get("title")),
                        "columns": columns,
                        "entries": entries,
                        "position": position,
                    })
                else:
                    title = raw.get("title")
                    content = raw.get("content")
                    clean.append({
                        "id": ident,
                        "type": block_type,
                        "title": "" if title is None else str(title),
                        "content": "" if content is None else str(content),
                        "position": position,
                    })
            except Exception:
                continue
        return clean
    except Exception:
        return []


def _canonical_section(value):
    """Canonical section name; unknown values pass through."""
    try:
        return _SECTION_RENAMES.get(value, value)
    except TypeError:
        return value


def sanitize_sections(data):
    """Normalize section_titles / hidden_sections / section_order.

    Accepts the legacy keys (titulos_seccion, secciones_ocultas,
    orden_secciones) and legacy section names inside their values, and
    migrates them to the canonical schema before sanitizing. Never raises:
    missing or malformed entries fall back to the canonical values (empty
    dict, empty list, full default order).
    """
    if not isinstance(data, dict):
        return data
    keys = latex_gen.DEFAULT_SECTION_ORDER

    def _raw(new_key, old_key):
        if new_key in data:
            return data.get(new_key)
        return data.get(old_key)

    # section_order: same contract as latex_gen.normalize_section_order
    # (valid keys, dedup keeping the first, missing ones appended at the end
    # in default order; any non-list value -> full default list). One
    # exception: the empty list is the canonical "default order" sentinel
    # (returned by empty_data and expanded by normalize_section_order when
    # rendering), so it is preserved to avoid inventing an order when
    # opening/importing an already canonical CV.
    try:
        raw_order = _raw("section_order", "orden_secciones")
        empty_list = isinstance(raw_order, (list, tuple)) and len(raw_order) == 0
    except Exception:
        empty_list = False
    if empty_list:
        order = []
    else:
        try:
            translated = []
            if isinstance(raw_order, (list, tuple)):
                for value in raw_order:
                    translated.append(_canonical_section(value))
            order = latex_gen.normalize_section_order({"section_order": translated})
            if not isinstance(order, list):
                order = list(keys)
        except Exception:
            order = list(keys)

    # section_titles: only valid keys with a non-empty stripped str value.
    titles = {}
    try:
        raw_titles = _raw("section_titles", "titulos_seccion")
    except Exception:
        raw_titles = None
    if isinstance(raw_titles, dict):
        try:
            items = list(raw_titles.items())
        except Exception:
            items = []
        for key, value in items:
            try:
                key = _canonical_section(key)
                if key not in keys or not isinstance(value, str):
                    continue
                value = value.strip()
            except Exception:
                continue
            if value:
                titles[key] = value

    # hidden_sections: valid keys without duplicates (the first one wins).
    hidden = []
    try:
        raw_hidden = _raw("hidden_sections", "secciones_ocultas")
    except Exception:
        raw_hidden = None
    if isinstance(raw_hidden, (list, tuple)):
        for value in raw_hidden:
            try:
                value = _canonical_section(value)
                if isinstance(value, str) and value in keys and value not in hidden:
                    hidden.append(value)
            except Exception:
                continue

    data["section_titles"] = titles
    data["hidden_sections"] = hidden
    data["section_order"] = order
    for old_key in ("titulos_seccion", "secciones_ocultas", "orden_secciones"):
        data.pop(old_key, None)
    return data


def migrate_data(data):
    """Convert legacy .cvjson payloads to the canonical English model.

    Translates every key (top level and per entry), the select values
    (work_mode, degree_type) and the blocks/sections to the new schema.
    Unknown values pass through as free text and hostile shapes are tolerated
    without raising.
    """
    if not isinstance(data, dict):
        return data
    if "experiencia" in data and isinstance(data.get("experiencia"), list) and not (
        data.get("trabajo") or data.get("pasantia")
        or data.get("work") or data.get("internships")
    ):
        work, internships = [], []
        for entry in data["experiencia"]:
            if isinstance(entry, dict) and str(entry.get("tipo", "")).strip().lower().startswith("pasant"):
                internships.append(entry)
            else:
                work.append(entry)
        data["trabajo"] = work
        data["pasantia"] = internships
        data.pop("experiencia", None)
    data = _rename_keys(data, _DATA_RENAMES)
    if isinstance(data.get("template"), str):
        data["template"] = _migrate_option(data["template"], _TEMPLATE_VALUES)
    for key in (
        "work", "internships", "projects", "university_projects", "education",
        "skills", "languages", "references", "extra_fields",
    ):
        data[key] = _migrate_entries(key, data.get(key))
    _migrate_legacy_contacts(data)
    data["socials"] = sanitize_socials(data.get("socials"))
    if "columns" in data:
        data["columns"] = _migrate_columns(data.get("columns"))
    data["blocks"] = sanitize_blocks(data.get("blocks"))
    return sanitize_sections(data)


def fill_defaults(data):
    """Fill only the missing schema keys of `data` (in place).

    If the default is None (e.g. photo_crop) the type is not checked: a valid
    dict rectangle must survive and None only applies when the key is absent.
    """
    empty = latex_gen.empty_data()
    for key, default in empty.items():
        if key not in data or (default is not None and not isinstance(data[key], type(default))):
            data[key] = default
    return data


def _backup_legacy_file(path):
    """Copy a pre-v3 .cvjson to `<path>.v2.bak` (never clobbers an existing one)."""
    backup = path + ".v2.bak"
    if os.path.exists(backup):
        return
    try:
        shutil.copy2(path, backup)
    except OSError:
        pass


def read_cvjson(content, path=None):
    """Return ``(data, media)`` from a .cvjson payload.

    v3 uses the ``{version, data, media}`` envelope; v1/v2 use the legacy
    Spanish ``{version, datos, medios}`` keys, and only v2 carries embedded
    media. Before migrating a file older than v3 it is copied to
    ``<path>.v2.bak``. Returns ``(None, None)`` when there is no usable data.
    """
    if not isinstance(content, dict):
        return None, None
    version = content.get("version")
    if version == 3:
        data, media = content.get("data"), content.get("media")
    else:
        data, media = content.get("datos"), content.get("medios")
        if version != 2:
            media = None
        if isinstance(data, dict) and path:
            _backup_legacy_file(path)
    if not isinstance(data, dict):
        return None, None
    return data, media


def collect_media(data, cache=None):
    """Return {original_path: {"name": basename, "b64": ...}} of existing media.

    `cache` is an optional per-Api dict keyed by ``(path, mtime, size)`` so
    unchanged files are not re-encoded on every autosave tick.
    """
    media = {}
    if not isinstance(data, dict):
        return media
    candidates = []
    for key in MEDIA_FIELDS:
        value = data.get(key)
        if isinstance(value, str) and value:
            candidates.append(value)
    for key in LOGO_FIELDS:
        entries = data.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict):
                value = entry.get("logo")
                if isinstance(value, str) and value:
                    candidates.append(value)
    for path in candidates:
        if path in media:
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext not in MEDIA_EXTS or not os.path.isfile(path):
            continue
        try:
            cache_key = (path, os.path.getmtime(path), os.path.getsize(path))
        except OSError:
            continue
        entry = cache.get(cache_key) if cache is not None else None
        if entry is None:
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
            except OSError:
                continue
            entry = {"name": os.path.basename(path), "b64": b64}
            if cache is not None:
                cache[cache_key] = entry
        media[path] = entry
    return media


def rewrite_media(data, replacements):
    for key in MEDIA_FIELDS:
        if isinstance(data.get(key), str):
            data[key] = replacements.get(data[key], data[key])
    for key in LOGO_FIELDS:
        entries = data.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("logo"), str):
                entry["logo"] = replacements.get(entry["logo"], entry["logo"])
    return data


def materialize_media(data, media):
    """Write the media of a v2/v3 envelope into CACHE_DIR and rewrite paths.

    v3 media entries use ``{"name", "b64"}``; v2 entries used the equivalent
    Spanish ``nombre`` key, which is still accepted.
    """
    if not isinstance(data, dict) or not isinstance(media, dict) or not media:
        return data
    try:
        os.makedirs(prefs.CACHE_DIR, exist_ok=True)
    except OSError:
        return data
    replacements = {}
    for original_path, info in media.items():
        if not isinstance(info, dict):
            continue
        b64 = info.get("b64")
        if not isinstance(b64, str):
            continue
        try:
            raw = base64.b64decode(b64)
        except Exception:
            continue
        if not raw:
            continue
        ext = os.path.splitext(str(original_path))[1].lower()
        if ext not in MEDIA_EXTS:
            ext = os.path.splitext(str(info.get("name") or info.get("nombre") or ""))[1].lower()
        if ext not in MEDIA_EXTS:
            ext = ".jpg"
        name = "cv_%s%s" % (uuid.uuid4().hex, ext)
        destination = os.path.join(prefs.CACHE_DIR, name)
        try:
            with open(destination, "wb") as f:
                f.write(raw)
        except OSError:
            continue
        replacements[str(original_path)] = destination
    if not replacements:
        return data
    return rewrite_media(data, replacements)


def _empty_dir(path):
    """Remove every entry under `path`, keeping the directory itself."""
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return
    try:
        names = os.listdir(path)
    except OSError:
        return
    for name in names:
        target = os.path.join(path, name)
        try:
            if os.path.isdir(target) and not os.path.islink(target):
                shutil.rmtree(target, ignore_errors=True)
            else:
                os.remove(target)
        except OSError:
            pass


def purge_cache():
    """Startup cleanup: empty the build/out caches and drop old media files.

    Called only once from the application startup (never on window
    operations): clears cache/build and cache/out and deletes cache media
    files older than CACHE_MAX_AGE_DAYS.
    """
    _empty_dir(prefs.BUILD_DIR)
    _empty_dir(os.path.join(prefs.CACHE_DIR, "out"))
    cutoff = time.time() - CACHE_MAX_AGE_DAYS * 24 * 60 * 60
    try:
        names = os.listdir(prefs.CACHE_DIR)
    except OSError:
        return
    for name in names:
        path = os.path.join(prefs.CACHE_DIR, name)
        if not os.path.isfile(path):
            continue
        if os.path.splitext(name)[1].lower() not in MEDIA_EXTS:
            continue
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


def _start_server():
    os.makedirs(prefs.BUILD_DIR, exist_ok=True)
    token = secrets.token_urlsafe(32)
    Handler.TOKEN = token
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port, token


def main():
    if getattr(sys, "frozen", False):
        import multiprocessing

        multiprocessing.freeze_support()
    # The embedded WebView2 PDF viewer saves through a download: pywebview
    # cancels downloads by default (ALLOW_DOWNLOADS=False), so the floppy
    # button in the preview would do nothing. Enabling it makes WebView2 open
    # its native save dialog.
    webview.settings["ALLOW_DOWNLOADS"] = True
    purge_cache()
    server, port, token = _start_server()
    api = Api(None)
    win = webview.create_window(
        window_title(prefs.get("ui_language")),
        url="http://127.0.0.1:%d/?%s=%s" % (port, TOKEN_PARAM, quote(token, safe="")),
        js_api=api,
        width=1240,
        height=800,
        min_size=(900, 580),
        background_color="#1f2430",
    )
    api._w = win
    win.events.closing += api._on_closing
    # Window/taskbar icon when the asset is present (dev tree or a build that
    # bundles assets/); otherwise pass None and Windows falls back to the exe
    # icon embedded by PyInstaller --icon. The guard also avoids handing GTK a
    # missing path.
    webview.start(icon=ICON_PATH if os.path.isfile(ICON_PATH) else None)
    server.shutdown()


if __name__ == "__main__":
    main()
