# CVLaTeX

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> Cross-platform desktop editor (Windows, Linux, macOS) for building a CV in a form, rendering it with LaTeX templates and compiling it to PDF with a live preview. It also exports Word (.docx) and LaTeX (.tex), and saves or loads projects as `.cvjson`.

## Download

These are the recommended downloads for most users: self-contained builds that need **no Python and no LaTeX installation**. The app can install TinyTeX on first run when you want PDF preview and export.

| Platform | Download |
| --- | --- |
| Windows x64 | [CVLaTeX-v0.2.0-windows-x64.zip](https://github.com/Echeq/CVLaTex/releases/download/v0.2.0/CVLaTeX-v0.2.0-windows-x64.zip) |
| macOS Apple Silicon (arm64) | [CVLaTeX-v0.2.0-macos-arm64.zip](https://github.com/Echeq/CVLaTex/releases/download/v0.2.0/CVLaTeX-v0.2.0-macos-arm64.zip) |
| Linux x86_64 | [CVLaTeX-v0.2.0-linux-x86_64.tar.gz](https://github.com/Echeq/CVLaTex/releases/download/v0.2.0/CVLaTeX-v0.2.0-linux-x86_64.tar.gz) |
| Checksums | [SHA256SUMS.txt](https://github.com/Echeq/CVLaTex/releases/download/v0.2.0/SHA256SUMS.txt) |

All four files are attached to the [v0.2.0 release](https://github.com/Echeq/CVLaTex/releases/tag/v0.2.0). **v0.2.0 is the first public pre-release** and the first release assembled by CI; v0.1.0 was a manual upload. The macOS build is Apple Silicon only; Intel Macs are not supported in v0.2.0. All 12 templates, the web assets and the Linux PDF.js viewer ship inside every bundle.

## Requirements

- Windows 10/11 with the WebView2 runtime (preinstalled on current Windows), macOS with the built-in WKWebView, or Linux with WebKitGTK 4.1 plus GObject introspection (`python3-gi`, `gir1.2-webkit2-4.1`; the WebKitGTK 4.1 runtime library is pulled in by these packages on Debian/Ubuntu). Building a bundle additionally needs the `libwebkit2gtk-4.1-dev` package, because PyInstaller must import `gi` and the GTK backend; running from source or from the bundle does not require `-dev`.
- To run from source: Python 3.12 with pip, plus the packages in `requirements.txt`. The standalone bundles need no Python installation.
- A LaTeX engine is optional. Preview and PDF export need one, but the app can download and install TinyTeX itself on all three platforms; Word (.docx) and LaTeX (.tex) export never need a LaTeX installation.

## Installation

For most users: download the archive above, extract it, and run the app. No Python or LaTeX installation is required; the app can install TinyTeX on first run. On first run the language picker asks for the interface language and the app starts with a blank CV; `Edit → Load sample CV` fills it with a fictional example when you want one.

### Windows

1. Download and extract the `.zip`.
2. Run `CVLaTeX.exe`.
3. Windows SmartScreen will warn because the build is unsigned: click **More info → Run anyway**.
4. WebView2 is required and normally preinstalled on Windows 10/11; if missing, install the [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/).
5. On first run, let the app install TinyTeX if you want PDF preview/export.

### macOS

1. Download and unzip; drag `CVLaTeX.app` to Applications (optional).
2. Open it. If Gatekeeper blocks it, right-click the app → **Open**, or use **System Settings → Privacy & Security → Open Anyway**.
3. This build is **Apple Silicon (arm64) only**; Intel Macs are not supported in v0.2.0.
4. Let the app install TinyTeX if you want PDF preview/export.

### Linux

1. Install the runtime packages: Debian/Ubuntu `sudo apt install python3-gi gir1.2-webkit2-4.1`; Arch `sudo pacman -S python-gobject webkit2gtk-4.1`.
2. Extract and run:

   ```bash
   tar -xzf CVLaTeX-v0.2.0-linux-x86_64.tar.gz
   chmod +x CVLaTeX
   ./CVLaTeX
   ```

3. `libwebkit2gtk-4.1-dev` is build-only and not needed to run.
4. Let the app install TinyTeX if you want PDF preview/export.

### From source

Linux:

```bash
sudo apt-get install python3-gi gir1.2-webkit2-4.1 python3-venv
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Add `libwebkit2gtk-4.1-dev` only when building a bundle with `./build.sh`; it is not needed to run from source.

macOS:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

On Linux the `--system-site-packages` flag is required so the venv sees the distro PyGObject/WebKitGTK packages; on macOS it is unnecessary. Full setup, test and build instructions are in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Releases

**v0.2.0 is the first public pre-release.** The direct downloads are in [Download](#download) and the same files are attached to the [v0.2.0 release](https://github.com/Echeq/CVLaTex/releases/tag/v0.2.0). Versions in the `0.*` series are published as GitHub pre-releases. (v0.1.0 was uploaded manually; v0.2.0 is the first archive set produced by the release workflow.)

| Platform | Architecture | Asset |
| --- | --- | --- |
| Windows | x64 | `CVLaTeX-v0.2.0-windows-x64.zip` (contains `CVLaTeX.exe`) |
| Linux | x86_64 | `CVLaTeX-v0.2.0-linux-x86_64.tar.gz` (contains `CVLaTeX`) |
| macOS | Apple Silicon (arm64) | `CVLaTeX-v0.2.0-macos-arm64.zip` (contains `CVLaTeX.app`) |
| All platforms | — | `SHA256SUMS.txt` |

GitHub's `macos-latest` runner currently builds natively on Apple Silicon, so
the v0.2.0 macOS asset is named `CVLaTeX-v0.2.0-macos-arm64.zip`. No universal
macOS binary and no Intel macOS build are produced for v0.2.0.

Verify a download with the checksum manifest (Linux/macOS, with the downloaded
files and `SHA256SUMS.txt` in the current directory):

```bash
sha256sum -c SHA256SUMS.txt
```

On Windows, compare `Get-FileHash -Algorithm SHA256 <file>` with the matching
line in `SHA256SUMS.txt`.

**Unsigned builds:** the Windows and macOS bundles are not code-signed or
notarized. Windows SmartScreen may warn about the executable, and macOS
Gatekeeper may block the `.app` on first launch (open it from Finder with
right-click → Open, or allow it in System Settings → Privacy & Security).
Verify the SHA-256 checksum and build provenance before running a bundle.

**Linux runtime:** the bundle needs WebKitGTK 4.1 and GObject introspection from
your distribution — on Debian/Ubuntu `python3-gi` and
`gir1.2-webkit2-4.1` (the build-only `libwebkit2gtk-4.1-dev` is needed only
when building), on Arch `python-gobject` and `webkit2gtk-4.1`.

Release notes live in [CHANGELOG.md](CHANGELOG.md), the security policy in
[SECURITY.md](SECURITY.md) and the third-party licenses in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Usage

The form is on the left and the compiled preview on the right; changes are recompiled automatically while typing (configurable in Settings). On Windows and macOS the preview is the webview's native PDF viewer. On Linux, where WebKitGTK cannot render PDFs inline, it is drawn by the PDF.js build vendored in `web/pdfjs/` and served locally at `/pdfjs/`. If PDF.js fails to load or render, the notice above the preview offers **Open PDF with the system viewer**, which opens the last compiled PDF with the desktop's default viewer.

### Templates

`Edit → CV template` groups the 12 templates into ATS Friendly (Classic, Harvard (academic)), Chinese styles (Chinese (standard), Black tabs, Blue ribbon, Navy minimal, Playful, Sword) and Normal CV (Modern, Creative, Sidebar (left), Sidebar (right)).

The Sidebar layout paints a full-height accent bar on the left of the first page only, holding the photo, school logo, contacts, social networks and extra details, while the main column keeps the name/profession header and the professional sections; the first page reserves about 7 cm on the left for the bar (ignoring the left margin setting) and pages 2+ use the configured margins and the full text width. Sidebar (right) mirrors the same layout with the bar on the right of the first page only, reserving about 7 cm on the right (ignoring the right margin setting) and using the configured margins and full text width afterwards. TeX fixes line breaks before pagination, so a single paragraph that straddles the page 1/2 break keeps its first-page line width; breaks between sections or entries reflow normally.

Chinese (standard) renders with a per-OS CJK font fallback (Microsoft YaHei, PingFang SC, Noto Sans CJK SC, WenQuanYi Zen Hei, Source Han Sans SC) and switches compilation to XeLaTeX automatically. Black tabs wraps every page in a heavy frame with black section tabs, Blue ribbon uses a slanted blue header band and a gold accent, Navy minimal keeps navy rules and dense three-column academic entries, Playful combines a large name, badge-style headings, diamond bullets and purple links, and Sword pairs a slanted navy name banner with a two-column contact grid (personal data on the left, profile links on the right, no row hairlines) and navy section plates over gray bars.

Every header shows the person's name as its main element instead of a redundant "resume" label, and long names shrink automatically to fit their banner or column.

### Form and sections

- Personal details plus a Social networks card: pick a network (GitHub, LinkedIn, X, Instagram, Facebook, YouTube, TikTok, Telegram, WeChat, Website or Other, which also takes a custom name), type the URL/username, and remove entries you no longer need.
- Extra details holds custom label/value pairs shown in the CV header; the old birth date and nationality fields now live here.
- Body sections: Education, Profile, Work, Internships, Projects, Campus activities, Skills & certificates, Languages, References. Each section header lets you rename it inline, hide/show it and move it up or down; the five entry-list sections support 1–3 columns.

### Sample CV

`Edit → Load sample CV` fills the form in the current `CV label language` (Spanish, English or Chinese), independent of the selected template. The same career story is translated for the three languages and the active template is kept, so you can see how to complete every field.

### Blocks

The `Add` menu inserts free blocks interleaved with the standard sections:

- `Columns` (1–3) and `Period + description` list templates.
- `Separator line`, `Color band` and `Blank space`.
- `Custom section` with a title and multi-line content.

Each block is anchored to the start, after a section, or to the end, and can be moved. `Add → Manage blocks…` edits, moves and deletes existing blocks. A block anchored to a hidden section keeps its position. In the Word export, free-block columns stay a single column.

### Document colors

`File → Settings` includes the Document colors fieldset (Primary, Secondary, Text, Gray). Each color can be typed as `#RRGGBB`, picked with the color wheel, or reset with `Auto`; an empty field uses the template's own color. The palette affects the exported document (PDF, Word, .tex), not the UI theme.

### UI language and document language

- **UI language** applies to the interface. On first launch CVLaTeX asks for it (English preselected) before the LaTeX setup wizard; the choice is stored in the preferences and applied instantly, including the window title. `File → Settings → Interface language` offers English (default), Español, 中文 and Русский and can change it later.
- **Document language** is the per-CV `CV label language` field (Spanish, English or Chinese; no Russian option). It selects the labels, fonts and engine used to render the CV. A new CV defaults to the UI language (English when the UI is Russian); the value is then saved with the document, so saved CVs keep their language and do not follow later UI changes.

### Export, import and save

- `File → Export → PDF…` compiles the document (requires a LaTeX engine).
- `File → Export → LaTeX…` writes the generated `.tex` with the data block embedded as comments.
- `File → Export → Word (.docx)…` writes a `.docx` with python-docx (no LaTeX needed) that follows the selected template instead of one generic layout: the header composition, section-heading shape, entry lines (right-tabbed date/title lines in the Latin templates, three-column entries in the Chinese-style ones), bullet markers and separators are reproduced with the template palette, and Preferences override its colors. The Latin templates also honour the 1–3 columns of the five entry-list sections; the Chinese-style templates keep their three-column entries and ignore that setting, as in the PDF.
- `File → Import LaTeX (.tex)…` rebuilds the form from the data block embedded in a CVLaTeX `.tex`; files without it are rejected with an alert.
- `File → Save…` / `File → Open…` use the `.cvjson` project format: version 3 stores the data plus the photo and logos embedded in base64. v1/v2 files are accepted and migrated (a backup copy with the `.v2.bak` suffix is written first, never clobbering an existing one).
- Autosave writes unsaved changes to the app data directory (`%LOCALAPPDATA%\CVLaTeX` on Windows, `~/Library/Application Support/CVLaTeX` on macOS, `$XDG_DATA_HOME/CVLaTeX` or `~/.local/share/CVLaTeX` on Linux); on the next start CVLaTeX offers to recover it only if it differs from an empty CV. Closing the window with unsaved changes opens a guard with Save / Exit without saving / Cancel; Save writes to the current `.cvjson` (and asks for a path when the CV has none yet).

The Word layout is an approximation built from WordprocessingML primitives, not a pixel copy of the PDF. Shapes are built from shading and borders rather than DrawingML or VML, and nothing is rotated, so the slanted ornaments (the Sword blade tip, the Blue ribbon wing) are drawn as stair-stepped bars. The Sidebar bar starts at the top margin instead of the paper edge and continues on later pages, while the PDF draws that bar on page 1 only; on the last page it ends with the content. Fonts are written explicitly (Cambria, Calibri for Playful, Microsoft YaHei for CJK), so a machine without them gets the system substitution. Word's line breaking and pagination differ from TeX, and free-block columns stay single-column.

### Photo and logos

`Choose photo…` normalizes the image (JPEG, longest side ≤ 1600 px) and opens the crop editor with the full image selected; cancelling keeps the normalized image, and `Adjust area…` reopens the crop later. The applied crop is saved as JPEG ≤ 1600 px. School and entry logos are normalized to PNG ≤ 512 px (no crop).

### Shortcuts

Ctrl+S saves, Ctrl+O opens, Ctrl+N starts a new CV, Ctrl+Enter recompiles, Ctrl+Z / Ctrl+Y (or Ctrl+Shift+Z) undo/redo. The preview zooms to 75%, 100% or 125%, and the form/preview split can be dragged (double-click resets it to 50%).

## LaTeX engine

PDF preview and export need a LaTeX engine. `pdflatex` is resolved in this order:

1. The `latex_path` preference, set from `Settings → LaTeX engine → Change path…`.
2. TinyTeX installed by the app in the app data directory (`tinytex/`).
3. `pdflatex` on the `PATH` (MiKTeX, TeX Live, MacTeX).

On first run, after the interface-language picker, the setup wizard offers to download and install TinyTeX automatically on Windows, Linux and macOS. The release asset is used exactly as published: when the release provides a SHA-256 checksum it is verified and a mismatch aborts the install; when no checksum asset is available (as in the pinned tinytex-releases version) the install proceeds after a warning that integrity could not be verified. The installation can be cancelled while in progress. Chinese text or a `fontspec` preamble switches to `xelatex` automatically. Word export requires no engine.

## Troubleshooting

- **"No LaTeX engine found" or the "No LaTeX engine is configured" warning**: install TinyTeX from the setup wizard, or set the `pdflatex` path in `Settings → LaTeX engine`. Preview and PDF export stay disabled until an engine is found.
- **Linux: the integrated preview is empty**: the preview is rendered with the bundled PDF.js, so a blank preview usually means `web/pdfjs/` was not bundled (the build includes it via `--add-data`) or PDF.js failed to load. The notice then offers **Open PDF with the system viewer**, which opens the last compiled PDF with the desktop's default viewer as a fallback.
- **Linux: the app does not start / no webview**: install the WebKitGTK/gir runtime packages from [Requirements](#requirements) (`python3-gi`, `gir1.2-webkit2-4.1`; add the build-only `libwebkit2gtk-4.1-dev` package only if you are building a bundle).
- **Linux bundle exits with `You must have either QT or GTK...` or `No module named 'gi'`**: the build machine's venv could not see the distro PyGObject, so the bundle shipped without the GTK backend. Install the system packages from [Requirements](#requirements) and rebuild with `./build.sh`; it recreates the venv with `--system-site-packages` so PyInstaller can import `gi`.
- **Missing LaTeX package**: the errors shown under the preview name the problem; install the package with your TeX distribution's manager or re-run the TinyTeX installer.
- **A `.tex` file is rejected on import**: only files generated or exported by CVLaTeX can be imported, because they carry the embedded data block. Foreign LaTeX files are not parsed heuristically.
- **Saving from the embedded PDF viewer does nothing**: downloads are enabled in the WebView so the viewer's save button opens the native dialog; if it still fails, use `File → Export → PDF…`.
- **Building on Windows cannot replace the executable**: close the running app first; Windows locks the executable while it runs.
- **A bundle built on one OS does not run on another**: bundles are per-platform; build natively or use the CI artifacts.

## Development

Install the test dependencies and run the suite:

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -m "not latex" -q   # fast loop: skips LaTeX compiles
.venv/bin/python -m pytest -n auto             # full suite, parallel
```

The fast loop excludes the slow PDF compilations, so use it while iterating and run the full suite before opening a pull request. The PDF compile tests are skipped, not failed, when `pdflatex`/`xelatex` are not installed. Validate the frontend syntax without a browser (optional, needs Node):

```bash
node --check web/app.js
node --check web/i18n.js
```

Build the release archives with `./build.sh` on Linux/macOS or `build.bat` on Windows. Each script stages the public assets, runs PyInstaller and calls `tools/package_release.py`, producing `dist/CVLaTeX-v0.2.0-linux-x86_64.tar.gz`, `dist/CVLaTeX-v0.2.0-macos-arm64.zip` and `dist/CVLaTeX-v0.2.0-windows-x64.zip`. The raw `dist/CVLaTeX_Linux`, `dist/CVLaTeX.app` and `dist/CVLaTeX.exe` stay available for local runs.

Setup for all platforms, architecture, testing strategy and the guides for adding templates or data fields are in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for setup.

## License

MIT — see [LICENSE](LICENSE).
