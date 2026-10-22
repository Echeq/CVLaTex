# Contributing to CVLaTeX

Thanks for helping. Bug reports, documentation fixes, translations, templates and code changes are all welcome.

## Before you start

- Set up the project with [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). Linux needs the venv created with `--system-site-packages` so PyGObject/WebKitGTK is visible.
- Run the suite before and after your change: `.venv/bin/python -m pytest tests -q` (728 tests pass on the current tree; PDF compile tests skip when no LaTeX engine is installed).
- For anything larger than a small fix, open an issue first so the approach can be discussed.

## Scope

Keep a change focused on one problem. Refactors, formatting-only edits and unrelated fixes in the same pull request make review slower and are usually split out.

## Reporting an issue

Search the existing issues first. A useful report includes:

- Operating system and version (Windows 10/11, macOS version, Linux distribution and desktop).
- The CVLaTeX commit or CI build you used.
- Exact steps to reproduce, the expected result and the actual result.
- The error text shown in the app, and any relevant console or crash log.
- A minimal `.cvjson` or `.tex` when the problem depends on the document. Remove personal data before attaching it.
- Screenshots for layout or preview problems.

Never include passwords, tokens, API keys, private documents or other secrets in an issue, a log or an attachment.

## Branch, commit and pull request workflow

1. Fork the repository and create a branch from `main`; use a descriptive name such as `fix/linux-preview` or `feat/new-template`.
2. Make the change and run the relevant tests.
3. Commit with an imperative, English subject (`Fix Linux preview fallback`, not `fixed stuff`). Keep generated files, virtual environments and build output out of the commit.
4. Open a pull request against `main`. Describe what changed and why, link the issue when there is one, and list the commands you ran.
5. Keep the pull request up to date with `main` and respond to review comments. Small, reviewable pull requests are merged faster.

## Conventions

- **Python:** 3.12 is the CI target. Use the standard library and the dependencies already in `requirements.txt`; adding a dependency needs a clear reason.
- **Frontend:** plain JavaScript, HTML and CSS with no build step. Edit `web/index.html`, `web/app.js`, `web/i18n.js` and `web/style.css` directly; do not add npm, a bundler or a transpiler.
- **Language:** use English for new code identifiers, filenames, comments, commit messages, branch names and build artifacts.
- **User-visible text:** never hardcode it. Add the key to `web/i18n.js` (frontend) or `messages.py` (backend) in all four languages (`es`, `en`, `zh`, `ru`) and reference it. Key sets must stay identical across the four tables.
- **LaTeX safety:** every user-injected TeX value must pass through `latex_gen.esc()`.
- **Tests:** add or update tests for behavior changes. The suite runs without a GUI or browser, and frontend tests pin exact strings, DOM ids, `data-accion` values and bridge names; update them in the same change.
- **Frozen contracts:** do not rename the `main.Api` bridge methods or the response envelope keys (`ok`, `errores`, `ruta`, `cancelado`, `datos`, `colores`), and do not change the schema keys or the `.cvjson` v3 format without updating the tests and the migration path. `Api._push()` must keep `ensure_ascii=True` (pywebview GTK truncates non-ASCII scripts otherwise).
- **Repository hygiene:** do not commit `.venv/`, `build/`, `dist/`, caches, `__pycache__`, personal CVs (`.cvjson`, `.pdf`, `.docx`), photos, logs, secrets or large binaries. The `.gitignore` already covers most of these.
- **Docs:** public docs are English. Update [README.md](README.md) for user-facing behavior and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for developer-facing behavior in the same change.

## Adding a template or a data field

Both are multi-file changes with checks that keep them consistent. Follow the step-by-step guides in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#adding-a-template) and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#adding-a-data-field); they list every registration point, the required LaTeX placeholders and the test updates.

## Release maintainers

Releases are cut from `main` by a maintainer. Bump `version.py`, the literal version in the credits modal (`web/index.html`) and `CHANGELOG.md`, run the suite, then push the `vX.Y.Z` tag. The tag triggers `.github/workflows/release.yml`, which tests, builds the three native bundles, writes `SHA256SUMS.txt` and publishes the GitHub Release. The step-by-step checklist is in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#releasing); never tag a commit whose tests are failing.

## Pull request checklist

- [ ] The change is focused and described in the pull request.
- [ ] `.venv/bin/python -m pytest tests -q` passes (or the skipped LaTeX tests are explained).
- [ ] `node --check web/app.js` and `node --check web/i18n.js` pass when the frontend changed.
- [ ] New or changed user-visible strings exist in all four languages.
- [ ] New data fields, templates or bridge/schema changes update the corresponding tests.
- [ ] Public docs are updated when behavior or setup changed.
- [ ] No secrets, personal documents, build output or large files are included.

## License

CVLaTeX is distributed under the MIT license (see [LICENSE](LICENSE)). By submitting a contribution you agree that it is licensed under the same terms.
