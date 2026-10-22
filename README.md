# CVLaTeX

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> Cross-platform desktop editor (Windows, Linux, macOS) for building a CV in a form, rendering it with LaTeX templates and compiling it to PDF with a live preview. It also exports Word (.docx) and LaTeX (.tex), and saves or loads projects as `.cvjson`.

## Requirements

- Windows 10/11 with the WebView2 runtime (preinstalled on current Windows), macOS with the built-in WKWebView, or Linux with WebKitGTK 4.1 plus GObject introspection (`python3-gi`, `gir1.2-webkit2-4.1`; the WebKitGTK 4.1 runtime library is pulled in by these packages on Debian/Ubuntu). Building a bundle additionally needs the `libwebkit2gtk-4.1-dev` package, because PyInstaller must import `gi` and the GTK backend; running from source or from the bundle does not require `-dev`.
- To run from source: Python 3.12 with pip, plus the packages in `requirements.txt`. The standalone bundles need no Python installation.
- A LaTeX engine is optional. Preview and PDF export need one, but the app can download and install TinyTeX itself on all three platforms; Word (.docx) and LaTeX (.tex) export never need a LaTeX installation.

## Installation

Two ways to get CVLaTeX: a standalone bundle or a source checkout.

### Standalone bundle

CI builds one PyInstaller bundle per platform and uploads them as artifacts of the `build` workflow (`Actions → build`); tagged versions are published with checksums by the `release` workflow (see [Releases](#releases)). No Python installation is needed on the target machine.

| Platform | Bundle |
| --- | --- |
| Windows | `dist/CVLaTeX_Windows.exe` |
| Linux | `dist/CVLaTeX_Linux` |
| macOS | `dist/CVLaTeX_macOS.zip` (unzip to `CVLaTeX.app`) |

On Linux, install the runtime packages from [Requirements](#requirements) first and keep the executable bit. To build a bundle locally, see [Build](docs/DEVELOPMENT.md#build).

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

The first pre-release is **v0.1.0**. Versions in the `0.*` series are published
as GitHub pre-releases. Each release contains the three native bundles built by
[`.github/workflows/release.yml`](.github/workflows/release.yml) and a
`SHA256SUMS.txt` manifest with the SHA-256 checksum of every asset.

| Platform | Architecture | Asset |
| --- | --- | --- |
| Windows | x64 | `CVLaTeX-v0.1.0-windows-x64.exe` |
| Linux | x86_64 | `CVLaTeX-v0.1.0-linux-x86_64` |
| macOS | Apple Silicon (arm64) | `CVLaTeX-v0.1.0-macos-arm64.zip` |

GitHub's `macos-latest` runner currently builds natively on Apple Silicon, so
the v0.1.0 macOS asset is named `CVLaTeX-v0.1.0-macos-arm64.zip`. The workflow
takes the suffix from `runner.arch`; if the runner label moves to Intel it will
publish `CVLaTeX-v0.1.0-macos-x86_64.zip` without a workflow change. No
universal macOS binary is produced.

Verify a download with the checksum manifest:

```bash
sha256sum -c SHA256SUMS.txt
```

On Windows, compare `Get-FileHash -Algorithm SHA256 <file>` with the matching
line in `SHA256SUMS.txt`.

**Unsigned builds:** the Windows and macOS bundles are not code-signed or
notarized. Windows SmartScreen may warn about the `.exe`, and macOS Gatekeeper
may block the `.app` on first launch (open it from Finder with right-click →
Open, or allow it in System Settings → Privacy & Security). Verify the SHA-256
checksum and build provenance before running a bundle.

**Linux runtime:** the bundle needs WebKitGTK 4.1 and GObject introspection from
your distribution — on Debian/Ubuntu `python3-gi` and
`gir1.2-webkit2-4.1` (the build-only `libwebkit2gtk-4.1-dev` is needed only
when building), on Arch `python-gobject` and `webkit2gtk-4.1`. Keep the executable bit
(`chmod +x CVLaTeX-v0.1.0-linux-x86_64`).

Release notes live in [CHANGELOG.md](CHANGELOG.md), the security policy in
[SECURITY.md](SECURITY.md) and the third-party licenses in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Usage

The form is on the left and the compiled preview on the right; changes are recompiled automatically while typing (configurable in Settings). On Windows and macOS the preview is the webview's native PDF viewer. On Linux, where WebKitGTK cannot render PDFs inline, it is drawn by the PDF.js build vendored in `web/pdfjs/` and served locally at `/pdfjs/`. If PDF.js fails to load or render, the notice above the preview offers **Open PDF with the system viewer**, which opens the last compiled PDF with the desktop's default viewer.

### Templates

`Edit → CV template` groups the 11 templates into ATS Friendly (Classic, Harvard (academic)), Chinese styles (Chinese (standard), Black tabs, Blue ribbon, Navy minimal, Playful) and Normal CV (Modern, Creative, Sidebar (left), Sidebar (right)).

The Sidebar layout paints a full-height accent bar on the left of every page holding the photo, school logo, contacts, social networks and extra details, while the main column keeps the name/profession header and the professional sections; its left margin is fixed (about 7 cm) and ignores the left margin setting so the bar keeps its width. Sidebar (right) mirrors the same layout with the bar on the right of every page, with the right margin fixed (about 7 cm) and ignoring the right margin setting.

Chinese (standard) renders with a per-OS CJK font fallback (Microsoft YaHei, PingFang SC, Noto Sans CJK SC, WenQuanYi Zen Hei, Source Han Sans SC) and switches compilation to XeLaTeX automatically. Black tabs wraps every page in a heavy frame with black section tabs, Blue ribbon uses a slanted blue header band and a gold accent, Navy minimal keeps navy rules and dense three-column academic entries, and Playful combines a large name, badge-style headings, diamond bullets and purple links.

### Form and sections

- Personal details plus a Social networks card: pick a network (GitHub, LinkedIn, X, Instagram, Facebook, YouTube, TikTok, Telegram, WeChat, Website or Other, which also takes a custom name), type the URL/username, and remove entries you no longer need.
- Extra details holds custom label/value pairs shown in the CV header; the old birth date and nationality fields now live here.
- Body sections: Profile, Education, Projects, University projects, Internships, Work, Skills, Languages, References. Each section header lets you rename it inline, hide/show it and move it up or down; the five entry-list sections support 1–3 columns.

### Sample CV

`Edit → Load sample CV` fills the form in the current `CV label language` (Spanish, English or Chinese), independent of the selected template. The same career story is translated for the three languages and the active template is kept, so you can see how to complete every field.

### Blocks

The `Add` menu inserts free blocks interleaved with the standard sections:

- `Columns` (1–3) and `Period + description` list templates.
- `Separator line`, `Color band` and `Blank space`.
- `Custom section` with a title and multi-line content.

Each block is anchored to the start, after a section, or to the end, and can be moved. `Add → Manage blocks…` edits, moves and deletes existing blocks. A block anchored to a hidden section keeps its position. In the Word export, block columns degrade to a single column.

### Document colors

`File → Settings` includes the Document colors fieldset (Primary, Secondary, Text, Gray). Each color can be typed as `#RRGGBB`, picked with the color wheel, or reset with `Auto`; an empty field uses the template's own color. The palette affects the exported document (PDF, Word, .tex), not the UI theme.

### UI language and document language

- **UI language** applies to the interface. On first launch CVLaTeX asks for it (English preselected) before the LaTeX setup wizard; the choice is stored in the preferences and applied instantly, including the window title. `File → Settings → Interface language` offers English (default), Español, 中文 and Русский and can change it later.
- **Document language** is the per-CV `CV label language` field (Spanish, English or Chinese; no Russian option). It selects the labels, fonts and engine used to render the CV. A new CV defaults to the UI language (English when the UI is Russian); the value is then saved with the document, so saved CVs keep their language and do not follow later UI changes.

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

On first run, after the interface-language picker, the setup wizard offers to download and install TinyTeX automatically on Windows, Linux and macOS. The release asset is used exactly as published: when the release provides a SHA-256 checksum it is verified and a mismatch aborts the install; when no checksum asset is available (as in the pinned tinytex-releases version) the install proceeds after a warning that integrity could not be verified. The installation can be cancelled while in progress. Chinese text or a `fontspec` preamble switches to `xelatex` automatically. Word export requires no engine.

## Troubleshooting

- **"No LaTeX engine found" or the "No LaTeX engine is configured" warning**: install TinyTeX from the setup wizard, or set the `pdflatex` path in `Settings → LaTeX engine`. Preview and PDF export stay disabled until an engine is found.
- **Linux: the integrated preview is empty**: the preview is rendered with the bundled PDF.js, so a blank preview usually means `web/pdfjs/` was not bundled (the build includes it via `--add-data`) or PDF.js failed to load. The notice then offers **Open PDF with the system viewer**, which opens the last compiled PDF with the desktop's default viewer as a fallback.
- **Linux: the app does not start / no webview**: install the WebKitGTK/gir runtime packages from [Requirements](#requirements) (`python3-gi`, `gir1.2-webkit2-4.1`; add the build-only `libwebkit2gtk-4.1-dev` package only if you are building a bundle).
- **Linux bundle exits with `You must have either QT or GTK...` or `No module named 'gi'`**: the build machine's venv could not see the distro PyGObject, so the bundle shipped without the GTK backend. Install the system packages from [Requirements](#requirements) and rebuild with `./build.sh`; it recreates the venv with `--system-site-packages` so PyInstaller can import `gi`.
- **Missing LaTeX package**: the errors shown under the preview name the problem; install the package with your TeX distribution's manager or re-run the TinyTeX installer.
- **A `.tex` file is rejected on import**: only files generated or exported by CVLaTeX can be imported, because they carry the embedded data block. Foreign LaTeX files are not parsed heuristically.
- **Saving from the embedded PDF viewer does nothing**: downloads are enabled in the WebView so the viewer's save button opens the native dialog; if it still fails, use `File → Export → PDF…`.
- **The PyInstaller build cannot replace `dist\CVLaTeX_Windows.exe`**: close the running app first; Windows locks the executable while it runs.
- **A bundle built on one OS does not run on another**: bundles are per-platform; build natively or use the CI artifacts.

## Development

Install the test dependencies and run the suite (726 tests pass on the current tree):

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests -q      # 726 passed
```

The PDF compile tests are skipped, not failed, when `pdflatex`/`xelatex` are not installed. Validate the frontend syntax without a browser (optional, needs Node):

```bash
node --check web/app.js
node --check web/i18n.js
```

Build the platform bundle with `./build.sh` on Linux/macOS or `build.bat` on Windows. The outputs are `dist/CVLaTeX_Linux`, `dist/CVLaTeX_macOS.zip` (with the unzipped `dist/CVLaTeX.app`) and `dist/CVLaTeX_Windows.exe`.

Setup for all platforms, architecture, testing strategy and the guides for adding templates or data fields are in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for setup.

## License

MIT — see [LICENSE](LICENSE).
