# -*- coding: utf-8 -*-
"""Release readiness checks: version, dependency pins, workflows and docs.

These tests are static and need no GUI, LaTeX engine or pywebview window.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import version  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = version.__version__
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")
README = os.path.join(ROOT, "README.md")
INDEX = os.path.join(ROOT, "web", "index.html")
RELEASE_WORKFLOW = os.path.join(ROOT, ".github", "workflows", "release.yml")
BUILD_WORKFLOW = os.path.join(ROOT, ".github", "workflows", "build.yml")

# Semantic Versioning 2.0.0, including optional pre-release/build metadata.
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _requirement_lines(filename):
    text = _read(os.path.join(ROOT, filename))
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def test_version_is_semver():
    assert SEMVER_RE.match(VERSION), VERSION


def test_version_appears_in_credits_html():
    html = _read(INDEX)
    assert 'data-i18n="credits_version"' in html
    assert "v%s" % VERSION in html


def test_changelog_latest_version_matches_version_py():
    changelog = _read(CHANGELOG)
    headers = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.MULTILINE)
    assert headers, "CHANGELOG.md has no version section"
    assert headers[0] == VERSION, (headers[0], VERSION)
    assert re.search(
        r"^## \[%s\] - \d{4}-\d{2}-\d{2}$" % re.escape(VERSION),
        changelog,
        re.MULTILINE,
    ), "the latest CHANGELOG section is not dated"


def test_changelog_documents_known_limitations():
    changelog = _read(CHANGELOG)
    assert "### Known limitations" in changelog
    for phrase in (
        "unsigned",
        "WebKitGTK 4.1",
        "PDF compile tests skip",
        "archive-based",
    ):
        assert phrase in changelog, phrase


def test_requirements_use_exact_pins():
    expected = {
        "requirements.txt": ["pywebview", "pyinstaller", "python-docx"],
        "requirements-dev.txt": ["pytest"],
    }
    for filename, packages in expected.items():
        entries = _requirement_lines(filename)
        names = []
        for entry in entries:
            assert "==" in entry, (filename, entry)
            # Exact pins only: no ranges, compatible releases or environment markers.
            assert not re.search(r"[<>~!]=?|@", entry), (filename, entry)
            name, spec = entry.split("==", 1)
            assert re.fullmatch(r"[A-Za-z0-9_.-]+", name), (filename, entry)
            assert re.fullmatch(r"[0-9][0-9A-Za-z.*+!-]*", spec), (filename, entry)
            names.append(name.lower())
        assert names == packages, (filename, names)


def test_release_workflow_triggers_on_tags():
    workflow = _read(RELEASE_WORKFLOW)
    assert re.search(r"^on:\s*$", workflow, re.MULTILINE)
    assert re.search(
        r"^\s+tags:\s*\[\s*[\"']v\*[\"']\s*\]", workflow, re.MULTILINE
    )


def test_release_workflow_has_write_permission_and_publishes():
    workflow = _read(RELEASE_WORKFLOW)
    assert re.search(r"^permissions:\s*$", workflow, re.MULTILINE)
    assert "contents: write" in workflow
    assert "gh release create" in workflow
    assert "--generate-notes" in workflow
    assert "--prerelease" in workflow
    assert "GH_TOKEN: ${{ github.token }}" in workflow


def test_release_workflow_tests_and_builds_three_platforms():
    workflow = _read(RELEASE_WORKFLOW)
    assert 'python-version: "3.12"' in workflow
    assert "pytest tests -q" in workflow
    for os_name in ("windows-latest", "ubuntu-latest", "macos-latest"):
        assert "- os: %s" % os_name in workflow, os_name
    assert "pyinstaller --noconfirm --onefile --windowed" in workflow
    assert "PYTHON=/usr/bin/python3 ./build.sh" in workflow
    assert "./build.sh" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "actions/download-artifact@v4" in workflow
    # The release is only created after tests and all builds succeeded.
    assert re.search(r"^  build:\s*\n\s+needs:\s+test", workflow, re.MULTILINE)
    assert re.search(
        r"^  publish:\s*\n\s+needs:\s*\[test, build\]", workflow, re.MULTILINE
    )


def test_release_workflow_generates_checksums_and_versioned_assets():
    workflow = _read(RELEASE_WORKFLOW)
    assert "sha256sum" in workflow
    assert "SHA256SUMS.txt" in workflow
    for asset in (
        "CVLaTeX-v${VERSION}-windows-x64.exe",
        "CVLaTeX-v${VERSION}-linux-x86_64",
        "CVLaTeX-v${VERSION}-macos-${arch}.zip",
    ):
        assert asset in workflow, asset
    # The downloaded artifact layout may include a dist/ prefix; locate by name.
    for name in ("CVLaTeX_Windows.exe", "CVLaTeX_Linux", "CVLaTeX_macOS-*.zip"):
        assert "find release-assets -type f -name '%s' -print -quit" % name in workflow
    # The tag is compared with version.py before anything is published.
    assert "does not match version.py" in workflow


def test_build_workflow_runs_tests_and_ignores_tags():
    workflow = _read(BUILD_WORKFLOW)
    assert re.search(
        r"^on:\s*\n\s+push:\s*\n\s+branches:\s*\[\s*[\"']\*\*[\"']\s*\]",
        workflow,
        re.MULTILINE,
    )
    assert "pull_request:" in workflow
    assert "workflow_dispatch:" in workflow
    assert re.search(r"^  test:\s*$", workflow, re.MULTILINE)
    assert "pytest tests -q" in workflow
    assert re.search(r"^  build:\s*\n\s+needs:\s+test", workflow, re.MULTILINE)


def test_readme_documents_release_assets():
    readme = _read(README)
    assert "## Download" in readme
    assert "## Releases" in readme
    assert "## Installation" in readme
    assert "v%s is the first public pre-release" % VERSION in readme

    base = "https://github.com/Echeq/CVLaTex/releases/download/v%s/" % VERSION
    for asset in (
        "CVLaTeX-v%s-windows-x64.zip" % VERSION,
        "CVLaTeX-v%s-macos-arm64.zip" % VERSION,
        "CVLaTeX-v%s-linux-x86_64.tar.gz" % VERSION,
        "SHA256SUMS.txt",
    ):
        assert asset in readme, asset
        assert base + asset in readme, base + asset

    for heading in ("### Windows", "### macOS", "### Linux", "### From source"):
        assert heading in readme, heading
    for phrase in (
        "No Python or LaTeX installation is required",
        "More info",
        "Run anyway",
        "Apple Silicon (arm64) only",
        "Intel Macs are not supported",
        "sudo apt install python3-gi gir1.2-webkit2-4.1",
        "sudo pacman -S python-gobject webkit2gtk-4.1",
        "tar -xzf CVLaTeX-v%s-linux-x86_64.tar.gz" % VERSION,
        "chmod +x CVLaTeX-v%s-linux-x86_64" % VERSION,
        "libwebkit2gtk-4.1-dev",
    ):
        assert phrase in readme, phrase

    for link in (
        "[CHANGELOG.md](CHANGELOG.md)",
        "[SECURITY.md](SECURITY.md)",
        "[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)",
    ):
        assert link in readme, link
    assert "sha256sum -c SHA256SUMS.txt" in readme
    assert "Get-FileHash" in readme
    assert "unsigned" in readme.lower()
    assert "WebKitGTK 4.1" in readme
