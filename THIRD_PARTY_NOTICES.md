# Third-Party Notices

CVLaTeX is distributed under the MIT license (see [LICENSE](LICENSE)). It
bundles or depends on the third-party components below. Their licenses apply
to their respective code; this file summarizes provenance and does not replace
the upstream license texts. Where a license could not be verified locally, the
upstream project is linked instead of guessing.

## Bundled with the application

### PDF.js 3.11.174

- **License:** Apache License 2.0
- **Local license text:** [`web/pdfjs/LICENSE`](web/pdfjs/LICENSE)
- **Upstream:** <https://github.com/mozilla/pdf.js>
- **Release:** <https://github.com/mozilla/pdf.js/releases/tag/v3.11.174>

`web/pdfjs/pdf.min.js` and `web/pdfjs/pdf.worker.min.js` are unmodified build
artifacts of the `pdfjs-dist` 3.11.174 npm package. CVLaTeX's
`web/pdfjs/viewer.html` is its own minimal wrapper.

## Python dependencies

### pywebview 6.2.1

- **License:** BSD 3-Clause
- **Verified from:** installed package metadata (`pywebview 6.2.1`)
- **Upstream:** <https://github.com/r0x0r/pywebview>
- **License text:** <https://github.com/r0x0r/pywebview/blob/master/LICENSE>

### python-docx 1.2.0

- **License:** MIT
- **Verified from:** installed package metadata (`python-docx 1.2.0`)
- **Upstream:** <https://github.com/python-openxml/python-docx>
- **License text:** <https://github.com/python-openxml/python-docx/blob/master/LICENSE>

### PyInstaller 6.22.3

- **License:** GPL-2.0-or-later with a special exception that permits building
  and distributing non-free programs (including commercial ones)
- **Verified from:** installed package metadata (`pyinstaller 6.22.3`)
- **Upstream:** <https://pyinstaller.org>
- **License text:** <https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt>

PyInstaller is a build tool: it packages the application and embeds its
bootloader in the platform bundles. Its exception covers distribution of the
resulting executables.

### pytest 9.1.1 (development only)

- **License:** MIT
- **Verified from:** installed package metadata (`pytest 9.1.1`, `License-Expression: MIT`)
- **Upstream:** <https://github.com/pytest-dev/pytest>
- **License text:** <https://github.com/pytest-dev/pytest/blob/main/LICENSE>

pytest is installed from `requirements-dev.txt` for the test suite and is not
shipped in the application bundles.

## System libraries (not bundled)

### PyGObject 3.56.3

- **License:** LGPL-2.1-or-later
- **Verified from:** system package metadata (`python-gobject 3.56.3-1`) and
  installed Python metadata (`PyGObject 3.56.3`)
- **Upstream:** <https://pygobject.gnome.org>
- **License text:** <https://gitlab.gnome.org/GNOME/pygobject/-/blob/main/COPYING>

PyGObject is provided by the operating system on Linux (for example
`python3-gi` on Debian/Ubuntu) and is not bundled in the release assets.

### WebKitGTK 4.1

- **License:** a composite of several free-software licenses; the local Arch
  package metadata for `webkit2gtk-4.1 2.52.6-1` lists multiple SPDX
  identifiers including LGPL-2.1-only, LGPL-2.1-or-later, BSD, MIT, Apache-2.0,
  MPL and others. The exact set depends on the distribution package.
- **Upstream:** <https://webkitgtk.org/> (license terms are also recorded in
  the metadata of the distribution package that provides WebKitGTK)

WebKitGTK is a system runtime library on Linux and is not bundled in the
release assets. Windows uses the WebView2 runtime and macOS uses the built-in
WKWebView (both supplied by the operating system).

## Downloaded at runtime

### TinyTeX

- **Shipped with CVLaTeX:** No. The app downloads and installs TinyTeX into the
  user's application data directory only when the user accepts the setup
  wizard.
- **Licensing:** TinyTeX is a distribution of TeX Live; its components carry
  their own licenses (for example GPL, LPPL and per-package terms). Those terms
  are not reproduced or verified here.
- **Upstream:** <https://yihui.org/tinytex/>
- **TeX Live licensing:** <https://www.tug.org/texlive/copying.html>
- **TinyTeX releases:** <https://github.com/rstudio/tinytex-releases>

Because TinyTeX is not part of this repository or its release assets, users are
responsible for reviewing its license terms and those of any LaTeX packages
they install.
