#!/usr/bin/env python3
"""Package a built CVLaTeX binary/bundle into a release archive.

Given a PyInstaller output and the repository docs, this script produces the
exact assets published for a release:

    dist/CVLaTeX-v<version>-windows-x64.zip
    dist/CVLaTeX-v<version>-linux-x86_64.tar.gz
    dist/CVLaTeX-v<version>-macos-<arch>.zip

Each archive contains the platform binary/bundle plus README.md, LICENSE,
THIRD_PARTY_NOTICES.md, CHANGELOG.md and SECURITY.md when it exists. Only the
standard library is used, timestamps/ownership are normalized as far as the
formats allow, and every archive is reopened and listed before the script
succeeds.
"""

from __future__ import annotations

import argparse
import gzip
import os
import platform as platform_module
import stat
import sys
import tarfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_DOCS = ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md")
OPTIONAL_DOCS = ("SECURITY.md",)
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

PLATFORMS = ("windows", "linux", "macos")


class PackagingError(RuntimeError):
    """The binary, docs or resulting archive are not release-ready."""


def _repo_version() -> str:
    sys.path.insert(0, ROOT)
    import version  # noqa: PLC0415 - local import keeps the script standalone

    return version.__version__


def normalize_arch(arch: str | None = None) -> str:
    """Map ``uname -m`` style values to the ``arm64``/``x86_64`` asset suffix."""
    raw = (arch or platform_module.machine() or "").strip().lower()
    if raw in {"arm64", "aarch64"}:
        return "arm64"
    if raw in {"x86_64", "amd64", "x64"}:
        return "x86_64"
    raise PackagingError("unsupported macOS architecture: %s" % (arch or raw))


def asset_name(platform: str, version: str, arch: str | None = None) -> str:
    if platform == "windows":
        return "CVLaTeX-v%s-windows-x64.zip" % version
    if platform == "linux":
        return "CVLaTeX-v%s-linux-x86_64.tar.gz" % version
    if platform == "macos":
        return "CVLaTeX-v%s-macos-%s.zip" % (version, normalize_arch(arch))
    raise PackagingError("unknown platform: %s" % platform)


def _docs(docs_dir: str) -> list[str]:
    """Return the doc basenames to include, preserving a stable order."""
    docs = []
    missing = []
    for name in REQUIRED_DOCS:
        path = os.path.join(docs_dir, name)
        if os.path.isfile(path):
            docs.append(name)
        else:
            missing.append(name)
    if missing:
        raise PackagingError(
            "missing release docs in %s: %s" % (docs_dir, ", ".join(missing))
        )
    for name in OPTIONAL_DOCS:
        if os.path.isfile(os.path.join(docs_dir, name)):
            docs.append(name)
    return docs


def _validate_binary(platform: str, binary: str) -> None:
    if platform == "macos":
        if not os.path.isdir(binary):
            raise PackagingError("macOS bundle is not a directory: %s" % binary)
    elif not os.path.isfile(binary):
        raise PackagingError("binary does not exist: %s" % binary)


def _zip_file(zf: zipfile.ZipFile, source: str, arcname: str, mode: int) -> None:
    info = zipfile.ZipInfo(arcname, date_time=FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (mode & 0xFFFF) << 16
    with open(source, "rb") as handle:
        zf.writestr(info, handle.read())


def _zip_dir(zf: zipfile.ZipFile, arcname: str) -> None:
    info = zipfile.ZipInfo(arcname.rstrip("/") + "/", date_time=FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = (0o40755 << 16) | 0x10
    zf.writestr(info, b"")


def _zip_tree(zf: zipfile.ZipFile, source: str, arcname: str) -> None:
    _zip_dir(zf, arcname)
    for current, dirs, files in os.walk(source):
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in {"__pycache__", "cache", "build", "dist"} and not d.startswith(".")
        )
        relative = os.path.relpath(current, source)
        base = arcname if relative == "." else os.path.join(arcname, relative)
        for name in dirs:
            _zip_dir(zf, os.path.join(base, name))
        for name in sorted(files):
            if name.startswith(".") or name.endswith(".pyc"):
                continue
            path = os.path.join(current, name)
            mode = stat.S_IMODE(os.stat(path).st_mode) or 0o644
            _zip_file(zf, path, os.path.join(base, name), mode)


def _write_zip(destination: str, platform: str, binary: str, docs_dir: str, docs: list[str]) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if platform == "macos":
            _zip_tree(zf, binary, os.path.basename(binary))
        else:
            _zip_file(zf, binary, "CVLaTeX.exe" if platform == "windows" else "CVLaTeX", 0o755)
        for name in docs:
            _zip_file(zf, os.path.join(docs_dir, name), name, 0o644)


def _tarinfo(name: str, mode: int, size: int = 0, is_dir: bool = False) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = mode
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.type = tarfile.DIRTYPE if is_dir else tarfile.REGTYPE
    return info


def _write_tar(destination: str, binary: str, docs_dir: str, docs: list[str]) -> None:
    with open(destination, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as tf:
                with open(binary, "rb") as handle:
                    tf.addfile(
                        _tarinfo("CVLaTeX", 0o755, os.path.getsize(binary)),
                        handle,
                    )
                for name in docs:
                    path = os.path.join(docs_dir, name)
                    with open(path, "rb") as handle:
                        tf.addfile(_tarinfo(name, 0o644, os.path.getsize(path)), handle)


def _verify(destination: str, platform: str, docs: list[str]) -> list[str]:
    if destination.endswith(".zip"):
        with zipfile.ZipFile(destination) as zf:
            names = zf.namelist()
    else:
        with tarfile.open(destination, "r:gz") as tf:
            names = tf.getnames()
            if platform == "linux":
                member = tf.getmember("CVLaTeX")
                if not member.mode & 0o111:
                    raise PackagingError("Linux executable is not executable in %s" % destination)

    missing = []
    if platform == "windows":
        if "CVLaTeX.exe" not in names:
            missing.append("CVLaTeX.exe")
    elif platform == "linux":
        if "CVLaTeX" not in names:
            missing.append("CVLaTeX")
    else:
        if not any(name == "CVLaTeX.app/" or name.startswith("CVLaTeX.app/") for name in names):
            missing.append("CVLaTeX.app/")
    missing.extend(name for name in docs if name not in names)
    if missing:
        raise PackagingError(
            "archive %s is missing: %s" % (destination, ", ".join(missing))
        )

    print("Verified %s (%d entries):" % (destination, len(names)))
    for name in names:
        print("  %s" % name)
    return names


def package(
    platform: str,
    binary: str,
    output_dir: str | None = None,
    docs_dir: str | None = None,
    version: str | None = None,
    arch: str | None = None,
) -> str:
    """Build and verify one release archive; return its path."""
    if platform not in PLATFORMS:
        raise PackagingError("unknown platform: %s" % platform)
    binary = os.path.abspath(binary)
    docs_dir = os.path.abspath(docs_dir or ROOT)
    output_dir = os.path.abspath(output_dir or os.path.join(ROOT, "dist"))
    version = version or _repo_version()

    _validate_binary(platform, binary)
    docs = _docs(docs_dir)
    os.makedirs(output_dir, exist_ok=True)
    destination = os.path.join(output_dir, asset_name(platform, version, arch))

    if platform == "linux":
        _write_tar(destination, binary, docs_dir, docs)
    else:
        _write_zip(destination, platform, binary, docs_dir, docs)

    _verify(destination, platform, docs)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=PLATFORMS)
    parser.add_argument("--binary", required=True, help="PyInstaller binary or .app bundle")
    parser.add_argument(
        "--output-dir",
        default=os.path.join(ROOT, "dist"),
        help="directory for the archive (default: dist)",
    )
    parser.add_argument(
        "--docs-dir",
        default=ROOT,
        help="directory holding README/LICENSE/THIRD_PARTY_NOTICES/CHANGELOG (default: repo root)",
    )
    parser.add_argument("--version", default=None, help="override version.py")
    parser.add_argument("--arch", default=None, help="macOS architecture (arm64/x86_64)")
    args = parser.parse_args(argv)

    try:
        destination = package(
            platform=args.platform,
            binary=args.binary,
            output_dir=args.output_dir,
            docs_dir=args.docs_dir,
            version=args.version,
            arch=args.arch,
        )
    except PackagingError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    print("Created %s" % destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
