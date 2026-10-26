#!/usr/bin/env python3
"""Stage the public runtime assets for a PyInstaller build.

Copies ``web/`` recursively, only ``templates/<dir>/*.tex`` and the optional
window-icon ``assets/CVLaTex.ico`` / ``assets/CVLaTex.png`` into a clean
staging directory (``build/stage`` by default), preserving the ``web/...``,
``templates/<dir>/...`` and ``assets/...`` layout that the frozen app expects
inside ``sys._MEIPASS``.

The real repository also contains personal material that must never ship in a
release: the author's reference CV (``templates/chinese/Elvis Chen CV.docx``)
and ``templates/picture samples/``. This script copies the twelve supported
template directories explicitly and only their ``.tex`` files, so those files
are excluded by construction rather than by a blacklist.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Every shipped template directory. Keep in sync with ``latex_gen.TEMPLATES``.
TEMPLATE_DIRS = (
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


class StagingError(RuntimeError):
    """A required source directory or template file is missing."""


#: Window icons read by ``main.ICON_PATH`` / the platform launchers at runtime.
ASSET_FILES = ("CVLaTex.ico", "CVLaTex.png")


def _is_ignored(name: str) -> bool:
    """Skip dotfiles, caches and build output while walking ``web/``."""
    return (
        name.startswith(".")
        or name in {"__pycache__", "cache", "build", "dist", "node_modules"}
        or name.endswith(".pyc")
    )


def _copy_web(source: str, destination: str) -> int:
    """Copy ``source`` recursively to ``destination``; return the file count."""
    if not os.path.isdir(source):
        raise StagingError("missing web directory: %s" % source)
    copied = 0
    for current, dirs, files in os.walk(source):
        dirs[:] = sorted(d for d in dirs if not _is_ignored(d))
        relative = os.path.relpath(current, source)
        target = destination if relative == "." else os.path.join(destination, relative)
        os.makedirs(target, exist_ok=True)
        for name in sorted(files):
            if _is_ignored(name):
                continue
            shutil.copy2(os.path.join(current, name), os.path.join(target, name))
            copied += 1
    if not copied:
        raise StagingError("web directory is empty: %s" % source)
    return copied


def _copy_templates(source: str, destination: str) -> int:
    """Copy only ``*.tex`` from each expected template directory."""
    copied = 0
    missing = []
    empty = []
    for name in TEMPLATE_DIRS:
        template_dir = os.path.join(source, name)
        if not os.path.isdir(template_dir):
            missing.append(name)
            continue
        tex_files = sorted(
            entry
            for entry in os.listdir(template_dir)
            if entry.lower().endswith(".tex")
            and os.path.isfile(os.path.join(template_dir, entry))
        )
        if not tex_files:
            empty.append(name)
            continue
        target_dir = os.path.join(destination, name)
        os.makedirs(target_dir, exist_ok=True)
        for filename in tex_files:
            shutil.copy2(
                os.path.join(template_dir, filename),
                os.path.join(target_dir, filename),
            )
            copied += 1

    if missing:
        raise StagingError(
            "missing template directories under %s: %s"
            % (source, ", ".join(missing))
        )
    if empty:
        raise StagingError(
            "template directories without a .tex file under %s: %s"
            % (source, ", ".join(empty))
        )
    return copied


def _copy_assets(source: str, destination: str) -> int:
    """Copy the window icons that are present; return the file count."""
    if not os.path.isdir(source):
        return 0
    copied = 0
    for name in ASSET_FILES:
        candidate = os.path.join(source, name)
        if not os.path.isfile(candidate):
            continue
        os.makedirs(destination, exist_ok=True)
        shutil.copy2(candidate, os.path.join(destination, name))
        copied += 1
    return copied


def stage(destination: str) -> tuple[int, int, int]:
    """Rebuild ``destination`` from the public repo assets.

    Returns ``(web_files, tex_files, asset_files)``. Raises
    :class:`StagingError` when a required directory or template is missing.
    """
    web_source = os.path.join(ROOT, "web")
    templates_source = os.path.join(ROOT, "templates")
    assets_source = os.path.join(ROOT, "assets")
    destination = os.path.abspath(destination)

    if os.path.isdir(destination):
        shutil.rmtree(destination)
    os.makedirs(destination)

    web_files = _copy_web(web_source, os.path.join(destination, "web"))
    tex_files = _copy_templates(templates_source, os.path.join(destination, "templates"))
    asset_files = _copy_assets(assets_source, os.path.join(destination, "assets"))
    return web_files, tex_files, asset_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        default=os.path.join(ROOT, "build", "stage"),
        help="staging directory to recreate (default: build/stage)",
    )
    args = parser.parse_args(argv)

    try:
        web_files, tex_files, asset_files = stage(args.dest)
    except StagingError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    print(
        "Staged %d web files, %d template files and %d asset files in %s"
        % (web_files, tex_files, asset_files, os.path.abspath(args.dest))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
