# -*- coding: utf-8 -*-
"""Release readiness checks: version, dependency pins, workflows, tooling and docs.

These tests are static (plus staging/packaging into temporary directories) and
need no GUI, LaTeX engine or pywebview window.
"""

import importlib.util
import os
import re
import stat
import subprocess
import sys
import tarfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import version  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = version.__version__
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")
README = os.path.join(ROOT, "README.md")
INDEX = os.path.join(ROOT, "web", "index.html")
RELEASE_WORKFLOW = os.path.join(ROOT, ".github", "workflows", "release.yml")
BUILD_WORKFLOW = os.path.join(ROOT, ".github", "workflows", "build.yml")
TOOLS = os.path.join(ROOT, "tools")
STAGE_TOOL = os.path.join(TOOLS, "stage_assets.py")
PACKAGE_TOOL = os.path.join(TOOLS, "package_release.py")
WINDOWS_VERSION_TOOL = os.path.join(TOOLS, "windows_version.py")

EXPECTED_TEMPLATES = (
    "classic",
    "harvard",
    "modern",
    "creative",
    "chinese",
    "sidebar",
    "sidebar-right",
    "tabbed",
    "ribbon",
    "navy",
    "playful",
    "sword",
)

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


def _load_tool(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_docs(directory):
    os.makedirs(directory, exist_ok=True)
    for name in (
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "CHANGELOG.md",
        "SECURITY.md",
    ):
        with open(os.path.join(directory, name), "w", encoding="utf-8") as handle:
            handle.write("%s placeholder\n" % name)


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


def _latest_changelog_section():
    changelog = _read(CHANGELOG)
    match = re.search(
        r"^## \[%s\].*?(?=^## \[|\Z)" % re.escape(VERSION),
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    assert match, "missing CHANGELOG section for %s" % VERSION
    return match.group(0)


def test_changelog_documents_known_limitations():
    section = _latest_changelog_section()
    for heading in ("### Added", "### Changed", "### Fixed", "### Known limitations"):
        assert heading in section, heading
    for phrase in (
        "unsigned",
        "WebKitGTK 4.1",
        "PDF compile tests skip",
        "archive-based",
    ):
        assert phrase in section, phrase


def test_requirements_use_exact_pins():
    expected = {
        "requirements.txt": ["pywebview", "pyinstaller", "python-docx"],
        "requirements-dev.txt": ["pytest", "pytest-xdist"],
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


def test_release_workflow_has_read_default_and_write_only_on_publish():
    workflow = _read(RELEASE_WORKFLOW)
    assert re.search(r"^permissions:\s*\n\s+contents:\s*read", workflow, re.MULTILINE)
    publish_index = workflow.index("  publish:")
    assert not re.search(
        r"^\s+contents:\s*write\s*$", workflow[:publish_index], re.MULTILINE
    )
    assert re.search(
        r"^\s+contents:\s*write\s*$", workflow[publish_index:], re.MULTILINE
    )
    assert "GH_TOKEN: ${{ github.token }}" in workflow


def test_release_workflow_publishes_idempotently():
    workflow = _read(RELEASE_WORKFLOW)
    assert "gh release create" in workflow
    assert "gh release upload" in workflow
    assert "--clobber" in workflow
    assert "gh release edit" in workflow
    assert "--generate-notes" in workflow
    assert "--prerelease" in workflow


def test_release_workflow_tests_and_builds_three_platforms():
    workflow = _read(RELEASE_WORKFLOW)
    assert 'python-version: "3.12"' in workflow
    assert "pytest tests -q" in workflow
    for os_name in ("windows-latest", "ubuntu-latest", "macos-latest"):
        assert "- os: %s" % os_name in workflow, os_name
    assert "build.bat" in workflow
    assert "PYTHON=/usr/bin/python3 ./build.sh" in workflow
    assert "./build.sh" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "actions/download-artifact@v4" in workflow
    assert "Verify macOS architecture" in workflow
    # The release is only created after tests and all builds succeeded.
    assert re.search(r"^  build:\s*\n\s+needs:\s+test", workflow, re.MULTILINE)
    assert re.search(
        r"^  publish:\s*\n\s+needs:\s*\[test, build\]", workflow, re.MULTILINE
    )


def test_release_workflow_generates_checksums_and_versioned_archives():
    workflow = _read(RELEASE_WORKFLOW)
    assert "sha256sum" in workflow
    assert "SHA256SUMS.txt" in workflow
    for asset in (
        "CVLaTeX-v${VERSION}-windows-x64.zip",
        "CVLaTeX-v${VERSION}-linux-x86_64.tar.gz",
        "CVLaTeX-v${VERSION}-macos-arm64.zip",
    ):
        assert asset in workflow, asset
    # Every published archive is inspected before the release is created.
    for entry in (
        "CVLaTeX.exe",
        "CVLaTeX.app/",
        "README.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "zipfile.ZipFile",
        "tarfile.open",
    ):
        assert entry in workflow, entry
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


def test_build_workflow_builds_and_uploads_versioned_archives():
    workflow = _read(BUILD_WORKFLOW)
    assert re.search(r"^permissions:\s*\n\s+contents:\s*read", workflow, re.MULTILINE)
    assert 'python-version: "3.12"' in workflow
    for script in ("build.bat", "PYTHON=/usr/bin/python3 ./build.sh", "./build.sh"):
        assert script in workflow, script
    for path in (
        "dist/CVLaTeX-v*-windows-x64.zip",
        "dist/CVLaTeX-v*-linux-x86_64.tar.gz",
        "dist/CVLaTeX-v*-macos-arm64.zip",
    ):
        assert path in workflow, path
    assert "actions/upload-artifact@v4" in workflow
    assert "if-no-files-found: error" in workflow


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
        "chmod +x CVLaTeX",
        "./CVLaTeX",
        "libwebkit2gtk-4.1-dev",
        "language picker",
        "blank CV",
        "12 templates",
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


def test_release_tooling_exists():
    for path in (STAGE_TOOL, PACKAGE_TOOL, WINDOWS_VERSION_TOOL):
        assert os.path.isfile(path), path


def test_build_scripts_stage_public_assets_and_package_archives():
    build_sh = _read(os.path.join(ROOT, "build.sh"))
    for snippet in (
        "tools/stage_assets.py",
        "build/stage",
        "--onefile",
        "--windowed",
        "tools/package_release.py",
        "--osx-bundle-identifier com.echeq.cvlatex",
        "PlistBuddy",
        "CFBundleShortVersionString",
        "CFBundleVersion",
    ):
        assert snippet in build_sh, snippet

    build_bat = _read(os.path.join(ROOT, "build.bat"))
    for snippet in (
        "tools\\stage_assets.py",
        "tools\\windows_version.py",
        "--version-file",
        "tools\\package_release.py",
        'if /I not "%CI%"=="true" pause',
        "exit /b 1",
    ):
        assert snippet in build_bat, snippet


def test_stage_assets_copies_public_assets_only(tmp_path):
    destination = tmp_path / "stage"
    result = subprocess.run(
        [sys.executable, STAGE_TOOL, "--dest", str(destination)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    template_root = destination / "templates"
    template_dirs = sorted(
        entry.name for entry in template_root.iterdir() if entry.is_dir()
    )
    assert template_dirs == sorted(EXPECTED_TEMPLATES)

    tex_files = sorted(template_root.rglob("*.tex"))
    assert len(tex_files) >= 12
    assert all(path.is_file() for path in tex_files)

    files = sorted(str(path.relative_to(destination)) for path in destination.rglob("*") if path.is_file())
    assert files, "staging directory is empty"
    assert not any(path.lower().endswith(".docx") for path in files)
    assert not any("picture samples" in path for path in files)
    assert not any("Elvis" in path for path in files)
    assert not any(
        part.startswith(".") for path in files for part in path.split(os.sep)
    )
    assert not any(
        part in {"cache", "dist", ".venv"} for path in files for part in path.split(os.sep)
    )
    assert (destination / "web" / "index.html").is_file()
    assert (destination / "web" / "pdfjs" / "viewer.html").is_file()

    # The window icon is read from BASE_DIR/assets at runtime, so the frozen
    # bundle needs it staged next to web/ and templates/.
    assert (destination / "assets" / "CVLaTex.ico").is_file()
    assert (destination / "assets" / "CVLaTex.png").is_file()


def test_package_release_windows_archive(tmp_path):
    package_release = _load_tool("package_release", PACKAGE_TOOL)
    docs = tmp_path / "docs"
    _write_docs(str(docs))
    binary = tmp_path / "CVLaTeX.exe"
    binary.write_bytes(b"dummy windows binary")
    output = tmp_path / "dist"

    archive = package_release.package(
        "windows", str(binary), str(output), str(docs), version=VERSION
    )
    assert os.path.basename(archive) == "CVLaTeX-v%s-windows-x64.zip" % VERSION
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert "CVLaTeX.exe" in names
    for doc in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md", "SECURITY.md"):
        assert doc in names, doc


def test_package_release_linux_archive_preserves_executable_bit(tmp_path):
    package_release = _load_tool("package_release", PACKAGE_TOOL)
    docs = tmp_path / "docs"
    _write_docs(str(docs))
    binary = tmp_path / "CVLaTeX"
    binary.write_bytes(b"#!/bin/sh\necho CVLaTeX\n")
    binary.chmod(0o755)
    output = tmp_path / "dist"

    archive = package_release.package(
        "linux", str(binary), str(output), str(docs), version=VERSION
    )
    assert os.path.basename(archive) == "CVLaTeX-v%s-linux-x86_64.tar.gz" % VERSION
    with tarfile.open(archive, "r:gz") as tf:
        names = set(tf.getnames())
        member = tf.getmember("CVLaTeX")
        assert member.mode & stat.S_IXUSR
    for doc in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md", "SECURITY.md"):
        assert doc in names, doc


def test_package_release_macos_archive_keeps_app_bundle(tmp_path):
    package_release = _load_tool("package_release", PACKAGE_TOOL)
    docs = tmp_path / "docs"
    _write_docs(str(docs))
    app = tmp_path / "CVLaTeX.app" / "Contents" / "MacOS"
    app.mkdir(parents=True)
    executable = app / "CVLaTeX"
    executable.write_bytes(b"dummy macos binary")
    executable.chmod(0o755)
    output = tmp_path / "dist"

    archive = package_release.package(
        "macos",
        str(tmp_path / "CVLaTeX.app"),
        str(output),
        str(docs),
        version=VERSION,
        arch="arm64",
    )
    assert os.path.basename(archive) == "CVLaTeX-v%s-macos-arm64.zip" % VERSION
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert any(name == "CVLaTeX.app/" or name.startswith("CVLaTeX.app/") for name in names)
    assert "CVLaTeX.app/Contents/MacOS/CVLaTeX" in names
    for doc in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md", "SECURITY.md"):
        assert doc in names, doc


def test_windows_version_resource_uses_version_py():
    windows_version = _load_tool("windows_version", WINDOWS_VERSION_TOOL)
    text = windows_version.render(VERSION)
    numeric = ".".join(str(part) for part in windows_version.numeric_version(VERSION))
    assert "ProductName', 'CVLaTeX'" in text
    assert "FileDescription', 'CVLaTeX'" in text
    assert "CompanyName" in text
    assert "FileVersion', '%s'" % numeric in text
    assert "ProductVersion', '%s'" % numeric in text
