#!/usr/bin/env bash
# Build the CVLaTeX bundle with PyInstaller (Linux/macOS counterpart of
# build.bat, which stays Windows-only).
#
# Creates/reuses the checkout's .venv, installs requirements.txt when the
# build dependencies are missing, bundles web/ and templates/ with the same
# PyInstaller flags as build.bat and writes a platform-suffixed bundle to
# dist/: dist/CVLaTeX_Linux on Linux, dist/CVLaTeX_macOS.zip (containing
# CVLaTeX.app, which stays unzipped in dist/ for local runs) on macOS. The
# PyInstaller app itself is still named CVLaTeX. The macOS .icns is generated
# from assets/CVLaTex.png with sips/iconutil and skipped gracefully when
# either tool or the PNG is missing; on Linux the PNG is passed through
# (PyInstaller ignores an unsupported icon harmlessly).
set -e
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
PLATFORM="$(uname -s)"

# PyInstaller must see the distro PyGObject (python3-gi / python-gobject) to
# bundle the GTK backend. A plain venv hides it, so on Linux keep the build
# venv linked to system site-packages and recreate an unusable one.
case "$PLATFORM" in
  Darwin)
    if [ ! -x .venv/bin/python ]; then
      "$PYTHON" -m venv .venv
    fi
    ;;
  *)
    if [ -d .venv ] && [ ! -x .venv/bin/python ]; then
      echo "warning: .venv has no bin/python (Windows venv?); recreating it" >&2
      rm -rf .venv
    fi
    if [ -x .venv/bin/python ] && ! .venv/bin/python -c "import gi" >/dev/null 2>&1; then
      echo "warning: .venv cannot import gi; recreating .venv with --system-site-packages" >&2
      rm -rf .venv
    fi
    if [ ! -x .venv/bin/python ]; then
      "$PYTHON" -m venv --system-site-packages .venv
    fi
    ;;
esac
VENV_PY=".venv/bin/python"

# Fail fast if the build venv cannot load the GTK webview backend: PyInstaller
# would otherwise produce a bundle that dies at startup with
# "You must have either QT or GTK..." / "No module named 'gi'".
if [ "$PLATFORM" != Darwin ]; then
  if ! "$VENV_PY" -c "import gi; gi.require_version('WebKit2', '4.1'); from gi.repository import WebKit2" >/dev/null 2>&1; then
    echo "error: PyGObject/WebKit2 4.1 is missing from the build venv ($VENV_PY)." >&2
    echo "       Debian/Ubuntu: sudo apt-get install python3-gi gir1.2-webkit2-4.1 libwebkit2gtk-4.1-dev" >&2
    echo "       Arch:          sudo pacman -S python-gobject webkit2gtk-4.1" >&2
    echo "       Then rerun ./build.sh; it recreates the venv with --system-site-packages." >&2
    exit 1
  fi
fi

# python-docx + PyInstaller detect a complete requirements.txt; the gi/WebKit2
# check above guarantees the distro PyGObject is importable from this venv.
if ! "$VENV_PY" -c "import docx, PyInstaller" >/dev/null 2>&1; then
  "$VENV_PY" -m pip install -r requirements.txt
fi

PYINSTALLER_ARGS=(--noconfirm --onefile --windowed --name CVLaTeX)

case "$PLATFORM" in
  Darwin)
    if [ -f assets/CVLaTex.png ] && command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
      ICONSET_TMP="$(mktemp -d)"
      ICONSET="$ICONSET_TMP/CVLaTex.iconset"
      mkdir -p "$ICONSET"
      # iconutil expects the 1x and @2x variant of every base size.
      generate() {
        sips -z "$2" "$2" assets/CVLaTex.png --out "$ICONSET/$1" >/dev/null
      }
      icon_ok=1
      generate icon_16x16.png 16 || icon_ok=0
      generate "icon_16x16@2x.png" 32 || icon_ok=0
      generate icon_32x32.png 32 || icon_ok=0
      generate "icon_32x32@2x.png" 64 || icon_ok=0
      generate icon_128x128.png 128 || icon_ok=0
      generate "icon_128x128@2x.png" 256 || icon_ok=0
      generate icon_256x256.png 256 || icon_ok=0
      generate "icon_256x256@2x.png" 512 || icon_ok=0
      generate icon_512x512.png 512 || icon_ok=0
      generate "icon_512x512@2x.png" 1024 || icon_ok=0
      if [ "$icon_ok" = 1 ] && iconutil -c icns "$ICONSET" -o assets/CVLaTex.icns; then
        PYINSTALLER_ARGS+=(--icon assets/CVLaTex.icns)
      else
        echo "warning: could not generate assets/CVLaTex.icns; building without a macOS icon" >&2
      fi
      rm -rf "$ICONSET_TMP"
    else
      echo "warning: sips/iconutil or assets/CVLaTex.png missing; building without a macOS icon" >&2
    fi
    ;;
  *)
    if [ -f assets/CVLaTex.png ]; then
      PYINSTALLER_ARGS+=(--icon assets/CVLaTex.png)
    fi
    ;;
esac

PYINSTALLER_ARGS+=(--add-data "web:web" --add-data "templates:templates" main.py)
"$VENV_PY" -m PyInstaller "${PYINSTALLER_ARGS[@]}"

# Platform-suffixed final artifact; the PyInstaller app keeps the plain name.
case "$PLATFORM" in
  Darwin)
    if [ -d dist/CVLaTeX.app ]; then
      rm -f dist/CVLaTeX_macOS.zip
      (cd dist && zip -qry CVLaTeX_macOS.zip CVLaTeX.app)
      OUTPUT="dist/CVLaTeX_macOS.zip (unzipped app: dist/CVLaTeX.app)"
    elif [ -f dist/CVLaTeX ]; then
      rm -f dist/CVLaTeX_macOS.zip
      (cd dist && zip -qry CVLaTeX_macOS.zip CVLaTeX)
      OUTPUT="dist/CVLaTeX_macOS.zip"
    else
      echo "error: PyInstaller produced neither dist/CVLaTeX.app nor dist/CVLaTeX" >&2
      exit 1
    fi
    ;;
  *)
    if [ -f dist/CVLaTeX ]; then
      mv -f dist/CVLaTeX dist/CVLaTeX_Linux
      OUTPUT="dist/CVLaTeX_Linux"
    else
      echo "error: PyInstaller did not produce dist/CVLaTeX" >&2
      exit 1
    fi
    ;;
esac

echo
echo "Done: $OUTPUT"
