# Security Policy

## Supported versions

CVLaTeX is a pre-1.0 project. Only the latest `0.1.x` release receives
security fixes.

| Version | Supported |
| --- | --- |
| 0.1.x | :white_check_mark: |
| < 0.1 | :x: |

## Reporting a vulnerability

Please report vulnerabilities privately through
[GitHub Security Advisories](https://github.com/Echeq/CVLaTex/security/advisories/new)
for this repository. If that form is unavailable, open a regular
[issue](https://github.com/Echeq/CVLaTex/issues) that asks for a private
channel without describing the vulnerability itself.

Include the affected version, operating system, reproduction steps and the
impact you observed. **Never include passwords, tokens, private keys, personal
documents, CVs, photos or other secrets** in an advisory, an issue, a log or an
attachment. If a proof of concept needs a document, use synthetic data.

There is no bug bounty and no guaranteed response time: this is a
maintainer-run project and reports are handled on a best-effort basis.

## Scope and guarantees

CVLaTeX runs locally, stores preferences and autosaves in the per-user
application data directory, and talks only to `127.0.0.1` for its UI. It may
download TinyTeX at the user's request. Release bundles are built by GitHub
Actions from the tagged source, and `SHA256SUMS.txt` lets you verify the
downloaded archive.

The project provides **no security guarantees**. In particular:

- Windows and macOS builds are unsigned and not notarized; your operating
  system may warn about them. Verify the checksum and build provenance before
  running a bundle.
- Users are responsible for the LaTeX engine they install or that the TinyTeX
  installer downloads, and for the documents and personal data they load.
- No audit of this codebase or its dependencies has been performed.
