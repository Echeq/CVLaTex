#!/usr/bin/env python3
"""Write a PyInstaller Windows version resource for CVLaTeX.

PyInstaller's ``--version-file`` expects a Python literal using
``VSVersionInfo``/``FixedFileInfo``/``StringFileInfo``/``VarFileInfo``. This
script reads ``version.py`` (the single source of truth) and emits the file on
demand, so the Windows executable's ProductVersion and FileVersion are never
hand-maintained.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_OUTPUT = os.path.join(ROOT, "build", "windows_version.txt")


def numeric_version(version: str) -> tuple[int, int, int, int]:
    """Convert ``X.Y.Z`` (optionally with a suffix) to a four-integer tuple."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError("version is not X.Y.Z: %s" % version)
    parts = [int(part) for part in match.groups()]
    parts.append(0)
    return tuple(parts)  # type: ignore[return-value]


def render(version: str) -> str:
    file_version = "%d.%d.%d.%d" % numeric_version(version)
    return """# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=%(tuple)s,
    prodvers=%(tuple)s,
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', 'Echeq'),
            StringStruct('FileDescription', 'CVLaTeX'),
            StringStruct('FileVersion', '%(file_version)s'),
            StringStruct('InternalName', 'CVLaTeX'),
            StringStruct('LegalCopyright', 'MIT License'),
            StringStruct('OriginalFilename', 'CVLaTeX.exe'),
            StringStruct('ProductName', 'CVLaTeX'),
            StringStruct('ProductVersion', '%(file_version)s')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""" % {"tuple": numeric_version(version), "file_version": file_version}


def write(version: str, destination: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render(version))
    return destination


def _repo_version() -> str:
    sys.path.insert(0, ROOT)
    import version  # noqa: PLC0415 - local import keeps the script standalone

    return version.__version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=None, help="override version.py")
    parser.add_argument("--out", default=DEFAULT_OUTPUT, help="output path")
    args = parser.parse_args(argv)

    version = args.version or _repo_version()
    try:
        destination = write(version, args.out)
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("Wrote %s for CVLaTeX %s" % (destination, version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
