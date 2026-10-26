# Changelog

All notable changes to CVLaTeX are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-26

Second release and the first public pre-release assembled by CI: v0.1.0 was a manual upload, while v0.2.0 is built and published from a `v0.2.0` tag. Every bundle carries all 12 templates, the web assets and the vendored PDF.js viewer.

### Added

- Sword template: a Chinese-style layout with a slanted navy name banner, a two-column contact grid with personal data on the left and profile links on the right (no row hairlines), and navy section plates over gray bars. The shipped template set is now 12: Classic, Harvard, Modern, Creative, Chinese (standard), Sidebar (left), Sidebar (right), Black tabs, Blue ribbon, Navy minimal, Playful and Sword.
- Release staging via `tools/stage_assets.py`: only `web/` and the twelve templates' `.tex` files enter the bundle, so personal reference files never ship.
- Release packaging via `tools/package_release.py`: versioned `.zip`/`.tar.gz` archives that include `README.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `CHANGELOG.md` and `SECURITY.md` next to the binary or `.app` bundle, with a printed entry listing for verification.
- `tools/windows_version.py` generates the PyInstaller Windows version resource from `version.py`.
- A tag-driven release workflow that tests, builds the three native archives, checks their contents and checksums, and publishes them as a GitHub pre-release.

### Changed

- CV headers now show the person's name instead of the redundant document title, and long names auto-fit their banner or column.
- The default body order is now education-first: Education, Profile, Work, Internships, Projects, Campus activities, Skills & certificates, Languages, References. Personal data comes before the job objective and the profile links in both PDF and Word, and the `university_projects` / `skills` labels are now Campus activities and Skills & certificates.
- The Word export now renders a per-template layout instead of one generic document: Classic, Harvard, Modern, Creative, Chinese, Sidebar (left), Sidebar (right), Black tabs, Blue ribbon, Navy minimal, Playful and Sword each get their matching header, section-heading shape, entry line, bullet marker, separators and palette, with preferences overriding the template colors.
- Word export honours the 1–3 columns of the five entry-list sections in the Latin templates; the Chinese-style templates keep their three-column entries and ignore that setting, as in the PDF.
- The built-in sample CVs are now clearly fictional in all three languages (Alejandro Ruiz Martín, `alex.ruiz@example.com`, `github.com/example`, Madrid), with the same career story, dates and entry counts as before.

### Fixed

- Release builds no longer bundle the author's reference CV (`templates/chinese/Elvis Chen CV.docx`) or `templates/picture samples/`; the staging step copies template `.tex` files explicitly.
- The Windows deployment is a `.zip` containing `CVLaTeX.exe`, the Linux one is a `.tar.gz` containing the executable with its mode preserved, and the macOS one is a `.zip` containing `CVLaTeX.app`.

### Known limitations

- The Windows and macOS bundles are **unsigned and not notarized**. Windows SmartScreen and macOS Gatekeeper may warn or block the first launch; verify the SHA-256 checksum before deciding to run them. Code signing and notarization are deferred to a later release.
- The Linux bundle needs WebKitGTK 4.1 and GObject introspection from the distribution (`python3-gi`, `gir1.2-webkit2-4.1` on Debian/Ubuntu; the `-dev` package is additionally required to build). Keep the executable bit.
- PDF compile tests skip, rather than fail, when no `pdflatex`/`xelatex` engine is installed; Word and `.tex` export and the schema/round-trip tests always run.
- Distribution is archive-based: a `.zip` containing `CVLaTeX.exe` on Windows, a `.tar.gz` containing a bare executable on Linux and a `.zip` containing `CVLaTeX.app` on macOS. There is no installer, package repository, auto-updater or universal macOS binary.
- Word export approximates the PDF instead of reproducing it pixel for pixel. Its shapes use no DrawingML or VML and nothing is rotated, so the Sword blade tip and the Blue ribbon wing are stair-stepped; the Sidebar bar starts at the top margin (not the paper edge) and continues on later pages, while the PDF draws it on page 1 only. Cambria, Calibri and Microsoft YaHei are requested explicitly and are substituted when the machine lacks them.

## [0.1.0] - 2026-10-22

First public pre-release. CVLaTeX is a cross-platform desktop CV editor for
Windows, Linux and macOS: a local form, LaTeX templates and a compiled preview,
with no account and no server.

### Added

- Desktop editor built on Python, pywebview and a local HTTP server, with a
  form on the left and a live PDF preview on the right.
- 11 LaTeX templates: Classic, Harvard, Modern, Creative, Chinese (standard),
  Sidebar (left), Sidebar (right), Black tabs, Blue ribbon, Navy minimal and
  Playful, grouped as ATS Friendly, Chinese styles and Normal CV.
- Localized sample CVs in Spanish, English and Chinese that tell the same
  career story, independent of the selected template.
- PDF preview through the native webview on Windows and macOS, and through the
  vendored PDF.js 3.11.174 viewer on Linux; a system-viewer fallback is offered
  when PDF.js cannot render.
- PDF export with `pdflatex`/`xelatex`; Word (`.docx`) export with python-docx
  and LaTeX (`.tex`) export with an embedded data block, both without a LaTeX
  engine.
- LaTeX import from CVLaTeX-generated `.tex` files; foreign files are rejected
  instead of parsed heuristically.
- `.cvjson` v3 project files with embedded photo and logos; v1/v2 files are
  migrated after writing a `.v2.bak` backup.
- Autosave with recovery on the next start, and a close guard with Save / Exit
  without saving / Cancel when the document has unsaved changes.
- First-run UI language picker (Spanish, English, Chinese, Russian) before the
  LaTeX setup wizard, and a separate per-CV document language.
- TinyTeX download and installation from the setup wizard, cancelable and
  checksum-verified when the release publishes a checksum.
- Free blocks (columns, period + description, separator line, color band,
  blank space, custom section) interleaved with the standard sections.
- Document color palette (primary, secondary, text, gray) affecting PDF, Word
  and `.tex` output.
- Photo and logo normalization, with a crop editor and re-editable crop.
- Debounced automatic compilation and a latest-only compile queue: a burst of
  edits produces one compile, and requests made while a compile is running
  collapse into a single follow-up instead of queueing in parallel.

### Changed

- Sidebar and Sidebar (right) draw the accent bar and reserve the 7 cm margin
  only on the first page; later pages use the configured margins and the full
  text width.

### Fixed

- Non-ASCII text in async bridge pushes no longer truncates or drops the
  script in the WebKitGTK backend (`ensure_ascii=True` is kept on every push).
- Linux PDF preview fallback when PDF.js fails to load or render.

### Known limitations

- The Windows and macOS bundles are **unsigned and not notarized**. Windows
  SmartScreen and macOS Gatekeeper may warn or block the first launch; verify
  the SHA-256 checksum before deciding to run them.
- The Linux bundle needs WebKitGTK 4.1 and GObject introspection from the
  distribution (`python3-gi`, `gir1.2-webkit2-4.1` on Debian/Ubuntu; the
  `-dev` package is additionally required to build). Keep the executable bit.
- PDF compile tests skip, rather than fail, when no `pdflatex`/`xelatex` engine
  is installed; Word and `.tex` export and the schema/round-trip tests always
  run.
- Distribution is archive-based: a `.exe` on Windows, a bare executable on
  Linux and a `.zip` containing `CVLaTeX.app` on macOS. There is no installer,
  package repository, auto-updater or universal macOS binary.

[0.2.0]: https://github.com/Echeq/CVLaTex/releases/tag/v0.2.0
[0.1.0]: https://github.com/Echeq/CVLaTex/releases/tag/v0.1.0
