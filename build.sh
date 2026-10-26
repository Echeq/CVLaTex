#!/usr/bin/env bash
# Build the CVLaTeX release bundle with PyInstaller (Linux/macOS counterpart of
# build.bat).
#
# Creates/reuses the checkout's .venv, installs requirements.txt when the build
# dependencies are missing, stages only the public runtime assets
# (web/ + the 12 template .tex files) into build/stage/, and runs PyInstaller
# against that staging tree so personal files never enter the bundle.
#
# Outputs:
#   Linux: dist/CVLaTeX_Linux (raw, for local runs) and
#          dist/CVLaTeX-v<version>-linux-x86_64.tar.gz (release archive)
#   macOS: dist/CVLaTeX.app (raw) and
#          dist/CVLaTeX-v<version>-macos-<arch>.zip (release archive)
#
# The macOS .icns is generated from assets/CVLaTex.png with sips/iconutil and
# skipped gracefully when either tool or the PNG is missing; on Linux the PNG
# is passed through (PyInstaller ignores an unsupported icon harmlessly).
set -e
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
PLATFORM="$(uname -s)"
VENV_PY=".venv/bin/python"

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

# Stage only web/ and the 12 supported template directories' .tex files.
# templates/chinese/Elvis Chen CV.docx and templates/picture samples/ are
# deliberately excluded, as are .venv, cache/ and dist/.
"$VENV_PY" tools/stage_assets.py --dest build/stage

PYINSTALLER_ARGS=(
  --noconfirm
  --onefile
  --windowed
  --name CVLaTeX
  --distpath dist
  --workpath build/pyinstaller
  --specpath build
)

case "$PLATFORM" in
  Darwin)
    PYINSTALLER_ARGS+=(--osx-bundle-identifier com.echeq.cvlatex)
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
        PYINSTALLER_ARGS+=(--icon "$(pwd)/assets/CVLaTex.icns")
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
      PYINSTALLER_ARGS+=(--icon "$(pwd)/assets/CVLaTex.png")
    fi
    ;;
esac

STAGE_DIR="$(pwd)/build/stage"
PYINSTALLER_ARGS+=(
  --add-data "$STAGE_DIR/web:web"
  --add-data "$STAGE_DIR/templates:templates"
  --add-data "$STAGE_DIR/assets:assets"
  "$(pwd)/main.py"
)
"$VENV_PY" -m PyInstaller "${PYINSTALLER_ARGS[@]}"

VERSION="$("$VENV_PY" -c 'import version; print(version.__version__)')"

case "$PLATFORM" in
  Darwin)
    if [ ! -d dist/CVLaTeX.app ]; then
      echo "error: PyInstaller did not produce dist/CVLaTeX.app" >&2
      exit 1
    fi
    if [ -x /usr/libexec/PlistBuddy ]; then
      PLIST="dist/CVLaTeX.app/Contents/Info.plist"
      set_plist() {
        /usr/libexec/PlistBuddy -c "Set :$1 $VERSION" "$PLIST" 2>/dev/null \
          || /usr/libexec/PlistBuddy -c "Add :$1 string $VERSION" "$PLIST"
      }
      set_plist CFBundleShortVersionString
      set_plist CFBundleVersion
    else
      echo "warning: /usr/libexec/PlistBuddy not found; leaving the bundle version as built" >&2
    fi
    "$VENV_PY" tools/package_release.py --platform macos --binary dist/CVLaTeX.app
    case "$(uname -m)" in
      arm64|aarch64) ARCH="arm64" ;;
      x86_64|amd64) ARCH="x86_64" ;;
      *)
        echo "error: unsupported macOS architecture: $(uname -m)" >&2
        exit 1
        ;;
    esac
    OUTPUT="dist/CVLaTeX-v${VERSION}-macos-${ARCH}.zip (unzipped app: dist/CVLaTeX.app)"
    ;;
  *)
    if [ ! -f dist/CVLaTeX ]; then
      echo "error: PyInstaller did not produce dist/CVLaTeX" >&2
      exit 1
    fi
    mv -f dist/CVLaTeX dist/CVLaTeX_Linux
    chmod +x dist/CVLaTeX_Linux
    "$VENV_PY" tools/package_release.py --platform linux --binary dist/CVLaTeX_Linux
    OUTPUT="dist/CVLaTeX-v${VERSION}-linux-x86_64.tar.gz (raw: dist/CVLaTeX_Linux)"
    ;;
esac

echo
echo "Done: $OUTPUT"
