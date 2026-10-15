#!/usr/bin/env bash
# Build the CVLaTeX bundle with PyInstaller (Linux/macOS counterpart of
# build.bat, which stays Windows-only).
#
# Creates/reuses the checkout's .venv, installs requirements.txt when the
# build dependencies are missing, bundles web/ and templates/ with the same
# PyInstaller flags as build.bat and writes the result to dist/ (on macOS
# PyInstaller also produces dist/CVLaTeX.app). The macOS .icns is generated
# from assets/CVLaTex.png with sips/iconutil and skipped gracefully when
# either tool or the PNG is missing; on Linux the PNG is passed through
# (PyInstaller ignores an unsupported icon harmlessly).
set -e
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
if [ ! -x .venv/bin/python ]; then
  "$PYTHON" -m venv .venv
fi
VENV_PY=".venv/bin/python"

# python-docx + PyInstaller detect a complete requirements.txt; importing
# pywebview on Linux needs the GTK system packages, which an isolated venv
# does not necessarily see, so it is not used as the probe.
if ! "$VENV_PY" -c "import docx, PyInstaller" >/dev/null 2>&1; then
  "$VENV_PY" -m pip install -r requirements.txt
fi

PYINSTALLER_ARGS=(--noconfirm --onefile --windowed --name CVLaTeX)

case "$(uname -s)" in
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

echo
echo "Done: dist/CVLaTeX (macOS: dist/CVLaTeX.app)"
