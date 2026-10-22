# PDF.js (vendored)

`pdf.min.js` and `pdf.worker.min.js` are the unmodified build artifacts of
[PDF.js](https://github.com/mozilla/pdf.js) **3.11.174** (the `pdfjs-dist` npm
package, `build/` directory), distributed under the Apache License 2.0; the
full license text is in `LICENSE`.

- Upstream package: <https://registry.npmjs.org/pdfjs-dist/-/pdfjs-dist-3.11.174.tgz>
- Upstream release: <https://github.com/mozilla/pdf.js/releases/tag/v3.11.174>

## Why it is vendored

On Linux pywebview uses WebKitGTK, which has no native inline PDF viewer, so
an `<iframe src="/preview/main.pdf">` stays blank. `viewer.html` loads the
vendored PDF.js build and renders the compiled PDF to canvases inside that
same iframe. The app is served from a `127.0.0.1` port and must work offline,
so PDF.js cannot be loaded from a CDN: both files are shipped in this folder.

`viewer.html` is CVLaTeX's own minimal wrapper (no PDF.js web viewer assets
are used). It expects the worker next to it as `pdf.worker.min.js`.

## Updating

1. Pick a PDF.js version whose build still targets the WebKitGTK version
   shipped with the supported distros (3.11.x is the tested line; 4.x needs
   newer browser APIs and a `.mjs` worker).
2. Download and unpack the npm tarball, then copy the three files:

   ```sh
   version=3.11.174
   curl -L --fail -o /tmp/pdfjs-dist-$version.tgz \
     https://registry.npmjs.org/pdfjs-dist/-/pdfjs-dist-$version.tgz
   rm -rf /tmp/pdfjs-dist-$version && mkdir -p /tmp/pdfjs-dist-$version
   tar -xzf /tmp/pdfjs-dist-$version.tgz -C /tmp/pdfjs-dist-$version
   cp /tmp/pdfjs-dist-$version/package/build/pdf.min.js web/pdfjs/
   cp /tmp/pdfjs-dist-$version/package/build/pdf.worker.min.js web/pdfjs/
   cp /tmp/pdfjs-dist-$version/package/LICENSE web/pdfjs/
   ```

3. Check that both scripts start with the Mozilla/Apache `@licstart` comment
   (not an HTML error page) and are larger than 100 KB. `node --check` cannot
   parse the minified build, so rely on the frontend tests and on opening a
   compiled PDF through `viewer.html` on Linux.
4. Update the version in this file and in the command above.
