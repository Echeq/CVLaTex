# CVLaTeX

> Cross-platform desktop editor (Windows, Linux, macOS) for building a CV in a form, rendering it with LaTeX templates and compiling it to PDF with a live preview. It also exports Word (.docx) and LaTeX (.tex), and saves or loads projects as `.cvjson`.

## Requirements

- Windows 10/11 with the WebView2 runtime (preinstalled on current Windows), macOS with the built-in WKWebView, or Linux with WebKitGTK (WebKit2GTK 4.1) or Qt WebEngine plus the GObject-introspection packages (`python3-gi`, `gir1.2-webkit2-4.1`; on Debian/Ubuntu also `libwebkit2gtk-4.1-dev` for source builds).
- To run from source: Python 3.12 with pip, plus the packages in `requirements.txt`.
- A LaTeX engine is optional. Preview and PDF export need one, but the app can download and install TinyTeX itself on all three platforms; Word (.docx) and LaTeX (.tex) export never need a LaTeX installation.

## Installation

Two ways to get CVLaTeX: a standalone bundle or a source checkout.

### Standalone bundle

Build the self-contained bundle once ([Development](#development)); it bundles the frontend and the templates and needs no Python installation. Run `dist\CVLaTeX.exe` on Windows, `dist/CVLaTeX` or `dist/CVLaTeX.app` on Linux/macOS. On Linux, install the runtime packages from [Requirements](#requirements) first and keep the executable bit.

### From source

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

On Windows use `.venv\Scripts\pip` and `.venv\Scripts\python.exe` instead. On Linux, `main.py` needs the WebKitGTK/gir runtime from [Requirements](#requirements).

To skip the manual setup, `build.sh` creates the venv, installs the requirements and produces the bundle in one step:

```bash
./build.sh
```

## Usage

The form is on the left and the compiled preview on the right; changes are recompiled automatically while typing (configurable in Settings). Linux webviews cannot render PDFs inline: there the preview bar shows **Open PDF with the system viewer**, which opens the last compiled PDF with the desktop viewer (`xdg-open`).

### Templates

`Edit → CV template` offers Classic, Harvard (academic), Modern, Creative, Sidebar (left), Sidebar (right) and Chinese (standard). The Sidebar layout paints a full-height accent bar on the left of every page holding the photo, school logo, contacts, social networks and extra details, while the main column keeps the name/profession header and the professional sections; its left margin is fixed (about 7 cm) and ignores the left margin setting so the bar keeps its width. Sidebar (right) mirrors the same layout with the bar on the right of every page, with the right margin fixed (about 7 cm) and ignoring the right margin setting so the bar keeps its width. The Chinese template renders with a per-OS CJK font fallback (Microsoft YaHei, PingFang SC, Noto Sans CJK SC, WenQuanYi Zen Hei, Source Han Sans SC) and switches compilation to XeLaTeX automatically.

### Form and sections

- Personal details plus a Social networks card: use the add button, pick a network (GitHub, LinkedIn, X, Instagram, Facebook, YouTube, TikTok, Telegram, WeChat, Website or Other, which also takes a custom name) and type the URL/username; each entry can be removed.
- Extra details holds custom label/value pairs shown in the CV header; the old birth date and nationality fields now live here.
- Body sections: Profile, Education, Projects, University projects, Internships, Work, Skills, Languages, References. Each section header lets you rename the section inline, hide/show it and move it up or down; the five entry-list sections support 1–3 columns.
- `Edit → Load sample CV` fills the form with an example (a Chinese one while the Chinese template is selected) so you can see how to complete every field.

### Blocks

The `Add` menu inserts free blocks interleaved with the standard sections:

- `Columns` (1–3) and `Period + description` list templates.
- `Separator line`, `Color band` and `Blank space`.
- `Custom section` with a title and one bullet per line.

Each block is anchored to the start, after a section, or to the end, and can be moved. `Add → Manage blocks…` edits, moves and deletes existing blocks. A block anchored to a hidden section keeps its position. In the Word export, block columns degrade to a single column.

### Document colors

`File → Settings` includes the Document colors fieldset (Primary, Secondary, Text, Gray). Each color can be typed as `#RRGGBB`, picked with the color wheel, or reset with `Auto`; an empty field uses the template's own color. The palette affects the exported document (PDF, Word, .tex), not the UI theme.

### UI language and document language

- UI language: `File → Settings → Interface language` offers English (default), Español, 中文 and Русский. It is stored in the preferences and applied instantly, including the window title.
- Document language: the per-CV `CV label language` field (Chinese, Spanish, English; Chinese by default; no Russian option). It selects the labels, fonts and engine used to render the CV and is independent from the UI language.

### Export, import and save

- `File → Export → PDF…` compiles the document (requires a LaTeX engine).
- `File → Export → LaTeX…` writes the generated `.tex` with the data block embedded as comments.
- `File → Export → Word (.docx)…` exports Word with python-docx (no LaTeX needed).
- `File → Import LaTeX (.tex)…` rebuilds the form from the data block embedded in a CVLaTeX `.tex`; files without it are rejected with an alert.
- `File → Save…` / `File → Open…` use the `.cvjson` project format: version 3 stores the data plus the photo and logos embedded in base64. v1/v2 files are accepted and migrated (a backup copy with the `.v2.bak` suffix is written first, never clobbering an existing one).
- Autosave writes unsaved changes to the app data directory (`%LOCALAPPDATA%\CVLaTeX` on Windows, `~/Library/Application Support/CVLaTeX` on macOS, `$XDG_DATA_HOME/CVLaTeX` or `~/.local/share/CVLaTeX` on Linux); on the next start CVLaTeX offers to recover it only if it differs from an empty CV. Closing the window with unsaved changes opens a guard with Save / Exit without saving / Cancel; Save writes to the current `.cvjson` (and asks for a path when the CV has none yet).

### Photo and logos

`Choose photo…` normalizes the image (JPEG, longest side ≤ 1600 px) and opens the crop editor with the full image selected; cancelling keeps the normalized image, and `Adjust area…` reopens the crop later. The applied crop is saved as JPEG ≤ 1600 px. School and entry logos are normalized to PNG ≤ 512 px (no crop).

### Shortcuts

Ctrl+S saves, Ctrl+O opens, Ctrl+N starts a new CV, Ctrl+Enter recompiles, Ctrl+Z / Ctrl+Y (or Ctrl+Shift+Z) undo/redo. The preview zooms to 75%, 100% or 125%, and the form/preview split can be dragged (double-click resets it to 50%).

## LaTeX engine

PDF preview and export need a LaTeX engine. `pdflatex` is resolved in this order:

1. The `latex_path` preference, set from `Settings → LaTeX engine → Change path…`.
2. TinyTeX installed by the app in the app data directory (`tinytex/`).
3. `pdflatex` on the `PATH` (MiKTeX, TeX Live, MacTeX).

On first run the setup wizard offers to download and install TinyTeX automatically on Windows, Linux and macOS. The release asset is used exactly as published: when the release provides a SHA-256 checksum it is verified and a mismatch aborts the install; when no checksum asset is available (as in the pinned tinytex-releases version) the install proceeds after a warning that integrity could not be verified. The installation can be cancelled while in progress. Chinese text or a `fontspec` preamble switches to `xelatex` automatically. Word export requires no engine.

## Troubleshooting

- **"No LaTeX engine is configured"**: install TinyTeX from the setup wizard, or set the `pdflatex` path in `Settings → LaTeX engine`. Preview and PDF export stay disabled until an engine is found.
- **Linux: the integrated preview is empty**: Linux webviews cannot display PDFs inline; use **Open PDF with the system viewer** in the preview bar, which opens the last compiled PDF with `xdg-open`.
- **Linux: the app does not start / no webview**: install the WebKitGTK/gir packages from [Requirements](#requirements) (`python3-gi`, `gir1.2-webkit2-4.1`, `libwebkit2gtk-4.1-dev`).
- **Missing LaTeX package**: the errors shown under the preview name the problem; install the package with your TeX distribution's manager or re-run the TinyTeX installer.
- **A `.tex` file is rejected on import**: only files generated or exported by CVLaTeX can be imported, because they carry the embedded data block. Older CVLaTeX files without it must be regenerated with the current version; foreign LaTeX files are not parsed heuristically.
- **Saving from the embedded PDF viewer does nothing**: downloads are enabled in the WebView so the viewer's save button opens the native dialog; if it still fails, use `File → Export → PDF…`.
- **The PyInstaller build cannot replace `dist\CVLaTeX.exe`**: close the running app first; Windows locks the executable while it runs.
- **A bundle built on one OS does not run on another**: bundles are per-platform; build natively or use the CI artifacts.

## Development

Install the test dependencies and run the suite (539 tests pass):

```bash
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest tests -q      # 539 passed
```

The PDF compile tests are skipped (not failed) when `pdflatex`/`xelatex` are not installed. Validate the frontend syntax without a browser (optional, needs Node):

```bash
node --check web/app.js
node --check web/i18n.js
```

Backend smoke check and LaTeX round-trip check (no GUI, no LaTeX):

```bash
.venv/Scripts/python.exe -c "import latex_gen, prefs; print(latex_gen.build_tex(latex_gen.empty_data(), prefs.load())[:120])"
.venv/Scripts/python.exe -c "import latex_gen, prefs, tex_datos; d=latex_gen.empty_data(); t=tex_datos.embed(latex_gen.build_tex(d, prefs.load()), d); assert tex_datos.extract(t)==d; print('round-trip OK')"
```

Build the one-file bundle with PyInstaller. `build.sh` wraps the Linux/macOS steps (venv, requirements, `.icns` generation via `sips`/`iconutil` on macOS); on Windows:

```powershell
.venv\Scripts\pyinstaller.exe --noconfirm --onefile --windowed --name CVLaTeX --icon "assets\CVLaTex.ico" --add-data "web;web" --add-data "templates;templates" main.py
```

Builds are per-platform, so `.github/workflows/build.yml` runs a Windows/Ubuntu/macOS matrix and uploads `CVLaTeX-windows.exe`, `CVLaTeX-linux` and `CVLaTeX-macos.zip` as artifacts (build only, no release publishing).

## License

MIT — see [LICENSE](LICENSE).
