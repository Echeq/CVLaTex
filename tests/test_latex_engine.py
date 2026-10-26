# -*- coding: utf-8 -*-
"""Motor LaTeX: deteccion de XeLaTeX (CJK o fontspec) y compilacion zh vacia.

``_uses_xelatex`` debe devolver True tanto para texto CJK como para cualquier
documento que cargue fontspec: pdflatex aborta con "fontspec requires XeTeX
or LuaTeX" aunque no haya ni un caracter CJK (p. ej. un CV vacio en zh, cuyo
font_engine emite fontspec). La compilacion real usa el mismo patron skipif
de test_roundtrip_tex.py.
"""

import hashlib
import io
import os
import re
import sys
import tarfile
import urllib.error
import zipfile
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_engine  # noqa: E402
import latex_gen  # noqa: E402
import messages  # noqa: E402
import prefs  # noqa: E402

MOTOR_PDF = latex_engine.find_pdflatex()
MOTOR_CJK = latex_engine.find_xelatex()

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


@pytest.fixture()
def prefs_tmp(tmp_path, monkeypatch):
    """Isolate prefs (dirs and cache) from the user machine."""
    app = tmp_path / "app"
    monkeypatch.setattr(prefs, "APP_DIR", str(app))
    monkeypatch.setattr(prefs, "CACHE_DIR", str(app / "cache"))
    monkeypatch.setattr(prefs, "BUILD_DIR", str(app / "cache" / "build"))
    monkeypatch.setattr(prefs, "PREFS_FILE", str(app / "prefs.json"))
    monkeypatch.setattr(prefs, "_CACHE", None)
    return tmp_path


def _pdf_contains(pdf_path, needle):
    """True when the raw PDF or any decompressed stream contains `needle`."""
    with open(pdf_path, "rb") as f:
        data = f.read()
    if needle in data:
        return True
    for match in re.finditer(rb"stream\r?\n", data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end == -1:
            continue
        try:
            stream = zlib.decompress(data[start:end].rstrip(b"\r\n"))
        except zlib.error:
            continue
        if needle in stream:
            return True
    return False


def test_detector_fontspec_solo_necesita_xelatex():
    tex = (
        "\\documentclass{article}\n"
        "\\usepackage{fontspec}\n"
        "\\setmainfont{Microsoft YaHei}\n"
        "\\begin{document}No CJK here\\end{document}"
    )
    assert latex_engine._uses_xelatex(tex) is True


def test_detector_fontspec_con_opciones():
    tex = "\\documentclass{article}\n\\usepackage[no-math]{fontspec}\n\\begin{document}x\\end{document}"
    assert latex_engine._uses_xelatex(tex) is True


def test_detector_lmodern_no_necesita_xelatex():
    tex = (
        "\\documentclass{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage{lmodern}\n"
        "\\begin{document}Hola, sin CJK ni fontspec.\\end{document}"
    )
    assert latex_engine._uses_xelatex(tex) is False


def test_detector_cjk_sigue_necesitando_xelatex():
    tex = "\\documentclass{article}\n\\begin{document}张伟\\end{document}"
    assert latex_engine._uses_xelatex(tex) is True


# ---------------------------------------------------------------------------
# Per-OS TinyTeX paths, archive types and pinned URLs
# ---------------------------------------------------------------------------

def test_tinyttex_bin_dirs_per_os():
    assert latex_engine._tinyttex_bin_dirs("win32") == ["bin/windows"]
    assert latex_engine._tinyttex_bin_dirs("darwin") == ["bin/universal-darwin"]
    assert latex_engine._tinyttex_bin_dirs("linux", "x86_64") == [
        "bin/x86_64-linux", "bin/aarch64-linux",
    ]
    assert latex_engine._tinyttex_bin_dirs("linux", "aarch64") == [
        "bin/aarch64-linux", "bin/x86_64-linux",
    ]
    assert latex_engine._tinyttex_bin_dirs("linux", "arm64") == [
        "bin/aarch64-linux", "bin/x86_64-linux",
    ]


def test_engine_exe_and_archive_kind_per_os():
    assert latex_engine._engine_exe("pdflatex", "win32") == "pdflatex.exe"
    assert latex_engine._engine_exe("pdflatex", "darwin") == "pdflatex"
    assert latex_engine._engine_exe("xelatex", "linux") == "xelatex"
    assert latex_engine._archive_kind("win32") == "zip"
    assert latex_engine._archive_kind("darwin") == "tar"
    assert latex_engine._archive_kind("linux") == "tar"


def test_tinyttex_urls_per_os_pin_the_verified_assets():
    base = f"https://github.com/rstudio/tinytex-releases/releases/download/v{latex_engine.TINYTEX_VERSION}"
    assert latex_engine.TINYTEX_URLS_BY_PLATFORM["win32"] == [
        f"{base}/TinyTeX-v{latex_engine.TINYTEX_VERSION}.zip"
    ]
    assert latex_engine.TINYTEX_URLS_BY_PLATFORM["darwin"] == [
        f"{base}/TinyTeX-v{latex_engine.TINYTEX_VERSION}.tgz"
    ]
    assert latex_engine.TINYTEX_URLS_BY_PLATFORM["linux"] == [
        f"{base}/TinyTeX-v{latex_engine.TINYTEX_VERSION}.tar.gz"
    ]
    expected = latex_engine.TINYTEX_URLS_BY_PLATFORM.get(
        sys.platform, latex_engine.TINYTEX_URLS_BY_PLATFORM["linux"]
    )
    assert latex_engine.TINYTEX_URLS == expected


def test_find_pdflatex_looks_inside_tinyttex_per_os(prefs_tmp, monkeypatch):
    tiny = prefs_tmp / "tinytex"
    monkeypatch.setattr(prefs, "TINYTEX_DIR", str(tiny))
    monkeypatch.setattr(latex_engine, "_check", lambda path: True)
    monkeypatch.setattr(latex_engine.shutil, "which", lambda name: None)
    assert latex_engine.find_pdflatex("win32") is None

    mac = tiny / "bin" / "universal-darwin"
    mac.mkdir(parents=True)
    mac_exe = mac / "pdflatex"
    mac_exe.write_text("#!/bin/sh\n", encoding="utf-8")
    assert latex_engine.find_pdflatex("darwin") == str(mac_exe)

    lin = tiny / "bin" / "x86_64-linux"
    lin.mkdir(parents=True)
    lin_exe = lin / "pdflatex"
    lin_exe.write_text("#!/bin/sh\n", encoding="utf-8")
    assert latex_engine.find_pdflatex("linux") == str(lin_exe)

    # Windows keeps the legacy bin/windows/pdflatex.exe path.
    win = tiny / "bin" / "windows"
    win.mkdir(parents=True)
    win_exe = win / "pdflatex.exe"
    win_exe.write_text("MZ", encoding="utf-8")
    assert latex_engine.find_pdflatex("win32") == str(win_exe)


def test_find_xelatex_uses_the_per_os_name(prefs_tmp, monkeypatch):
    tiny = prefs_tmp / "tinytex"
    monkeypatch.setattr(prefs, "TINYTEX_DIR", str(tiny))
    monkeypatch.setattr(latex_engine, "_check", lambda path: True)
    monkeypatch.setattr(latex_engine.shutil, "which", lambda name: None)
    lin = tiny / "bin" / "x86_64-linux"
    lin.mkdir(parents=True)
    (lin / "pdflatex").write_text("x", encoding="utf-8")
    assert latex_engine.find_xelatex("linux") is None
    xe = lin / "xelatex"
    xe.write_text("x", encoding="utf-8")
    assert latex_engine.find_xelatex("linux") == str(xe)


def test_extract_archive_tar_gz_uses_the_per_os_bin_dir(prefs_tmp, monkeypatch):
    tiny = prefs_tmp / "tinytex"
    monkeypatch.setattr(prefs, "TINYTEX_DIR", str(tiny))
    archive = prefs_tmp / "tinytex-linux.tar.gz"
    payload = b"#!/bin/sh\n"
    with tarfile.open(archive, "w:gz") as tf:
        info = tarfile.TarInfo(".TinyTeX/bin/x86_64-linux/pdflatex")
        info.size = len(payload)
        info.mode = 0o755
        tf.addfile(info, io.BytesIO(payload))

    calls = []
    result = latex_engine._extract_archive(
        str(archive), lambda done, total: calls.append((done, total)), "linux"
    )
    assert result == str(tiny / "bin" / "x86_64-linux" / "pdflatex")
    assert os.path.isfile(result)
    assert not os.path.exists(str(tiny) + ".tmp")
    assert calls


def test_extract_archive_zip_uses_the_windows_bin_dir(prefs_tmp, monkeypatch):
    tiny = prefs_tmp / "tinytex"
    monkeypatch.setattr(prefs, "TINYTEX_DIR", str(tiny))
    archive = prefs_tmp / "tinytex.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("TinyTeX/bin/windows/pdflatex.exe", "MZ")

    result = latex_engine._extract_archive(str(archive), lambda done, total: None, "win32")
    assert result == str(tiny / "bin" / "windows" / "pdflatex.exe")
    assert os.path.isfile(result)


def test_extract_archive_without_pdflatex_raises(prefs_tmp, monkeypatch):
    tiny = prefs_tmp / "tinytex"
    monkeypatch.setattr(prefs, "TINYTEX_DIR", str(tiny))
    archive = prefs_tmp / "tinytex-macos.tgz"
    payload = b"readme"
    with tarfile.open(archive, "w:gz") as tf:
        info = tarfile.TarInfo("TinyTeX/README.md")
        info.size = len(payload)
        tf.addfile(info, io.BytesIO(payload))

    with pytest.raises(latex_engine.LatexError):
        latex_engine._extract_archive(str(archive), lambda done, total: None, "darwin")
    assert not os.path.exists(str(tiny))


# ---------------------------------------------------------------------------
# TinyTeX SHA-256 policy: matching -> silent, unavailable -> warning + install,
# mismatching -> abort. Everything is deterministic and offline (monkeypatch).
# ---------------------------------------------------------------------------

_FAKE_ARCHIVE = b"fake-tinytex-archive"


def _offline_install(monkeypatch, checksum, warnings, extracted):
    """install_tinytex() offline; returns the pdflatex path it installed."""

    def fake_download(url, destination, progress, cancel_event=None):
        with open(destination, "wb") as f:
            f.write(_FAKE_ARCHIVE)
        progress(len(_FAKE_ARCHIVE), len(_FAKE_ARCHIVE))

    def fake_extract(archive_path, progress, platform=None):
        extracted.append(archive_path)
        os.makedirs(prefs.TINYTEX_DIR, exist_ok=True)
        exe = os.path.join(prefs.TINYTEX_DIR, "pdflatex")
        with open(exe, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n")
        return exe

    monkeypatch.setattr(latex_engine, "_download", fake_download)
    monkeypatch.setattr(
        latex_engine, "_fetch_checksum", lambda url, cancel_event=None: checksum
    )
    monkeypatch.setattr(latex_engine, "_extract_archive", fake_extract)
    monkeypatch.setattr(latex_engine, "_check", lambda path: True)
    return latex_engine.install_tinytex(
        lambda done, total: None, None, warn=warnings.append
    )


def _tinytex_tmp(prefs_tmp, monkeypatch):
    monkeypatch.setattr(prefs, "TINYTEX_DIR", str(prefs_tmp / "tinytex"))


def test_install_tinytex_matching_checksum_installs_silently(prefs_tmp, monkeypatch):
    _tinytex_tmp(prefs_tmp, monkeypatch)
    warnings, extracted = [], []
    digest = hashlib.sha256(_FAKE_ARCHIVE).hexdigest()
    result = _offline_install(monkeypatch, digest, warnings, extracted)
    assert result == os.path.join(prefs.TINYTEX_DIR, "pdflatex")
    assert os.path.isfile(result)
    assert warnings == []
    assert len(extracted) == 1
    assert not os.path.exists(os.path.join(prefs.APP_DIR, "tinytex-download"))


def test_install_tinytex_without_checksum_warns_and_continues(prefs_tmp, monkeypatch):
    _tinytex_tmp(prefs_tmp, monkeypatch)
    warnings, extracted = [], []
    result = _offline_install(monkeypatch, None, warnings, extracted)
    assert result == os.path.join(prefs.TINYTEX_DIR, "pdflatex")
    assert warnings == [messages.t("install_checksum_warning")]
    assert len(extracted) == 1


def test_install_tinytex_checksum_mismatch_aborts(prefs_tmp, monkeypatch):
    _tinytex_tmp(prefs_tmp, monkeypatch)
    warnings, extracted = [], []
    with pytest.raises(latex_engine.LatexError) as excinfo:
        _offline_install(monkeypatch, "0" * 64, warnings, extracted)
    assert str(excinfo.value) == messages.t("install_checksum_mismatch")
    assert warnings == []
    assert extracted == []
    assert not os.path.exists(os.path.join(prefs.APP_DIR, "tinytex-download"))


def test_fetch_checksum_returns_none_when_the_asset_is_missing(monkeypatch):
    def urlopen(request, timeout=60):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(latex_engine.urllib.request, "urlopen", urlopen)
    assert (
        latex_engine._fetch_checksum("https://example.test/TinyTeX-v1.tar.gz.sha256")
        is None
    )


def test_install_checksum_warning_is_localized_in_four_languages():
    texts = [
        messages.t("install_checksum_warning", lang)
        for lang in ("es", "en", "zh", "ru")
    ]
    assert all(isinstance(text, str) and text.strip() for text in texts)
    assert len(set(texts)) == 4


# ---------------------------------------------------------------------------
# zh fontspec fallback chain
# ---------------------------------------------------------------------------

def test_zh_font_engine_uses_if_fontexiststf_chains(prefs_tmp):
    tex = latex_gen.build_tex(latex_gen.empty_data(), prefs.load())
    assert "\\usepackage{fontspec}" in tex
    # The historical strings stay in the generated tex.
    assert "\\setmainfont{Microsoft YaHei}" in tex
    assert "\\setsansfont{Microsoft YaHei}" in tex
    assert "\\setmonofont{Consolas}" in tex
    # Both chains try their candidates in order (the last one is the
    # unconditional fallback and is not wrapped in \IfFontExistsTF).
    main_positions = [
        tex.index("\\IfFontExistsTF{%s}" % font) for font in latex_gen.CJK_MAIN_FONTS[:-1]
    ]
    assert main_positions == sorted(main_positions)
    mono_positions = [
        tex.index("\\IfFontExistsTF{%s}" % font) for font in latex_gen.CJK_MONO_FONTS[:-1]
    ]
    assert mono_positions == sorted(mono_positions)
    for font in latex_gen.CJK_MAIN_FONTS + latex_gen.CJK_MONO_FONTS:
        assert font in tex, font
    assert "\\setmainfont{Source Han Sans SC}" in tex
    assert "\\setmonofont{Noto Sans Mono}" in tex
    # The fontspec detector still routes the document to XeLaTeX.
    assert latex_engine._uses_xelatex(tex) is True


@pytest.mark.latex
@pytest.mark.skipif(
    MOTOR_PDF is None or MOTOR_CJK is None,
    reason="Sin motores LaTeX (pdflatex/xelatex) instalados",
)
def test_compila_cv_vacia_zh_sidebar_via_xelatex(prefs_tmp):
    """The CV that used to abort with "fontspec requires XeTeX" now compiles.

    empty_data() is zh by default (fontspec in the preamble) and the sidebar
    header omits the CJK title, so the document contains no CJK character at
    all: the detector must switch to XeLaTeX because of fontspec.
    """
    datos = latex_gen.empty_data()
    datos["template"] = "sidebar"
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "\\usepackage{fontspec}" in tex
    assert not _CJK_RE.search(tex)
    assert latex_engine._uses_xelatex(tex) is True

    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])
    # Evidence of the engine actually used: xdvipdfmx/XeTeX metadata.
    assert _pdf_contains(resultado["pdf"], b"XeTeX")
