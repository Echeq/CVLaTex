"""Embedding and extraction of the base64 data block in the CVLaTeX .tex file.

The block is written as LaTeX comments (lines starting with "%"), so the
document still compiles the same way, and it allows rebuilding the original
data dict (round-trip) from the generated .tex.
"""

import base64
import json
import re

MARK_START = "% CVLaTeX-DATA-BEGIN"
MARK_END = "% CVLaTeX-DATA-END"
LINE_WIDTH = 76  # leaves 78-character lines: below the TeX limit

_RE_BLOCK = re.compile(
    re.escape(MARK_START) + r".*?" + re.escape(MARK_END) + r"[^\n]*\n?",
    re.DOTALL,
)
_RE_CONTENT = re.compile(
    re.escape(MARK_START) + r"(.*?)" + re.escape(MARK_END),
    re.DOTALL,
)
_RE_DOCUMENT = re.compile(r"^[ \t]*\\begin\{document\}", re.MULTILINE)


class MissingDataBlock(Exception):
    """The .tex does not contain the data block markers."""


class InvalidDataBlock(Exception):
    """The block exists but its base64, its JSON or its shape is not valid."""


def data_block(data):
    """Return the LaTeX comment block with the encoded data."""
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(raw).decode("ascii")
    parts = [MARK_START + "\n"]
    for i in range(0, len(encoded), LINE_WIDTH):
        parts.append("% " + encoded[i:i + LINE_WIDTH] + "\n")
    parts.append(MARK_END + "\n")
    return "".join(parts)


def embed(tex, data):
    """Replace every existing block with the new one or insert it.

    If there is no block, it is placed just before the first
    \\begin{document} line; if that line does not exist, at the start of the
    file.
    """
    new_block = data_block(data)
    if _RE_BLOCK.search(tex):
        tex = _RE_BLOCK.sub(lambda _m: new_block, tex)
        # If there were several copies, keep only the first to avoid
        # duplicating data.
        first = tex.find(new_block)
        return tex[:first + len(new_block)] + tex[first + len(new_block):].replace(new_block, "")
    m = _RE_DOCUMENT.search(tex)
    if m:
        return tex[:m.start()] + new_block + tex[m.start():]
    return new_block + tex


def extract(tex):
    """Rebuild the data dict embedded in the .tex."""
    m = _RE_CONTENT.search(tex or "")
    if not m:
        raise MissingDataBlock("No data block found in the .tex.")
    parts = []
    for line in m.group(1).splitlines():
        clean = line.strip()
        if clean.startswith("%"):
            clean = clean[1:].strip()
        parts.append(clean)
    try:
        raw = base64.b64decode("".join(parts))
        data = json.loads(raw.decode("utf-8"))
    except ValueError as e:
        raise InvalidDataBlock("The data block is not valid base64/JSON.") from e
    if not isinstance(data, dict):
        raise InvalidDataBlock("The data block does not contain a JSON object.")
    return data
