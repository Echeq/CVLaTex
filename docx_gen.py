# -*- coding: utf-8 -*-
"""Word (.docx) CV generation with python-docx.

It does not depend on LaTeX or pywebview: only on python-docx and on the
latex_gen helpers (LANG translation table, section order/visibility/titles).
The selected LaTeX template is read for its palette so the Word export keeps
the visual identity of the PDF: a colored nameplate or accent name header, the
template's own section heading shape (accent rule, plate + tail, black tab,
ribbon bar, badge or stair blade), its entry line family (date/title or the
Chinese three-column line), its bullet marker and palette-aware separators.
"""

import os

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import docx_profiles
import docx_shapes
import latex_gen
from latex_gen import BLOCK_ANCHORS, LANG, LIST_MODES, SEPARATOR_STYLES, option_label

# Page size in centimetres: (width, height).
PAPER_SIZES = {
    "a4": (21.0, 29.7),
    "letter": (21.59, 27.94),
    "legal": (21.59, 35.56),
}

# Image extensions accepted for the photo and the school logo.
PHOTO_EXTS = {".jpg", ".jpeg", ".png"}
LOGO_EXTS = PHOTO_EXTS

DEFAULT_MARGIN = 2.0
DEFAULT_FONT_SIZE = 11.0
NAME_FONT_SIZE = 20.0
DEFAULT_PHOTO_WIDTH = 4.0
DEFAULT_PHOTO_HEIGHT = 5.0
DEFAULT_LOGO_WIDTH = 2.4
DEFAULT_LOGO_HEIGHT = 0.85

# Hard ceilings for the header images (the data width/height only lowers them).
MAX_PHOTO_WIDTH_CM = 12.0
MAX_PHOTO_HEIGHT_CM = 15.0
MAX_LOGO_WIDTH_CM = 6.0
MAX_LOGO_HEIGHT_CM = 4.0

# The sidebar family renders the whole CV inside the body cell of one page-wide
# table row. Its at-least height is computed from the paper and margins (the
# full text block) so the accent bar reaches the bottom margin on a one-page
# CV; a longer CV splits the row and the cell shading continues on pages 2+.
# The LaTeX bar is a page-1-only shipout overlay as tall as the paper, which
# normal flow cannot express (documented divergence in ``_header_sidebar``).

# Word fonts: a serif family for the classic academic designs and a sans one
# for the playful template; Microsoft YaHei keeps CJK text readable.
SERIF_FONT = "Cambria"
SANS_FONT = "Calibri"
EAST_ASIA_FONT = "Microsoft YaHei"
# Mono-ish face for the playful phone/e-mail values (the LaTeX template wraps
# them in \texttt); Word and LibreOffice substitute their default mono face.
MONO_FONT = "Consolas"

# Accent blue of the classic template (default CV color).
COLOR_ACCENT = "233A5E"
COLOR_GRAY = "6E7684"

#: Templates that use the Chinese-style layout (three-column entry lines,
#: plate/tab/badge section headings, square or diamond bullets).
CN_STYLE_TEMPLATES = frozenset(getattr(latex_gen, "CHINESE_STYLE_TEMPLATES", ()))

#: Vertical rhythm of a text-only section heading (LaTeX \vspace 1.2-1.3em
#: before the title and 0.5em after the rule, at the 11pt body size).
LATIN_HEADING_BEFORE_PT = 9.5
LATIN_HEADING_AFTER_PT = 5.0
#: Gap paragraphs around a table-based heading (the plate cannot carry
#: paragraph spacing: its row height is exact). The paragraph-shaped Chinese
#: headings (navy, playful) use the same "before" gap, matching the 0.8-0.95em
#: of LaTeX \cvsection without pushing the body past the page.
CN_HEADING_BEFORE_PT = 8.0
CN_HEADING_AFTER_PT = 4.5
#: Bullet geometry in centimetres (LaTeX \leftmargini 1.2em at 11pt).
BULLET_INDENT_CM = 0.52
BULLET_INDENT_L2_CM = 0.98
BULLET_AFTER_PT = 0.8
#: Space between entries of a Chinese-style three-column section (LaTeX
#: \vspace 0.1em after \cvcnline, ~3pt at the 11pt body size).
CN_ENTRY_GAP_PT = 3.0

# Kept as raw strings: they are compared to qn() names, not parsed here.
_PBDR_SUCCESSORS = (
    "w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
    "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
    "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
    "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
    "w:textDirection", "w:textAlignment", "w:textboxTightWrap",
    "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr",
    "w:pPrChange",
)
_SHADING_SUCCESSORS = _PBDR_SUCCESSORS[1:]
_TBL_BORDERS_SUCCESSORS = (
    "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption",
    "w:tblDescription", "w:tblPrChange",
)
_TC_MAR_SUCCESSORS = (
    "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark", "w:headers",
    "w:cellIns", "w:cellDel", "w:cellMerge", "w:tcPrChange",
)
_TC_SHADING_SUCCESSORS = ("w:noWrap", "w:tcMar") + _TC_MAR_SUCCESSORS


def _text(value):
    """Return the value as text without surrounding spaces (never raises)."""
    if value is None:
        return ""
    try:
        return str(value).strip()
    except Exception:
        return ""


def _value(mapping, key, default=None):
    """mapping.get(key) that tolerates hostile mappings; never raises."""
    try:
        return mapping.get(key, default)
    except Exception:
        return default


def _number(value, default):
    """Cast to float and fall back to the default when not numeric."""
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp_number(value, default, low, high):
    """Numeric value clamped to [low, high], with a safe default."""
    return min(max(_number(value, default), float(low)), float(high))


def _rgb_from_hex(value):
    """Normalize "#RGB" or "#RRGGBB" to RGBColor.

    It accepts upper and lower case, trims outer spaces and expands the short
    form by doubling every digit (#ABC -> #AABBCC). Any other value (including
    non-str) falls back to None; it never raises.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text.startswith("#"):
        return None
    hex_digits = text[1:]
    if len(hex_digits) == 3 and all(c in "0123456789abcdefABCDEF" for c in hex_digits):
        hex_digits = "".join(c * 2 for c in hex_digits)
    if len(hex_digits) != 6 or any(c not in "0123456789abcdefABCDEF" for c in hex_digits):
        return None
    try:
        return RGBColor(int(hex_digits[0:2], 16), int(hex_digits[2:4], 16), int(hex_digits[4:6], 16))
    except (TypeError, ValueError):
        return None


def _pref_color(prefs_dict, key):
    """RGBColor from prefs["colors"][key]; empty or invalid -> None."""
    try:
        colors = prefs_dict.get("colors") if isinstance(prefs_dict, dict) else None
        if not isinstance(colors, dict):
            return None
        return _rgb_from_hex(colors.get(key))
    except Exception:
        return None


def _hex_from_color(color):
    """RGBColor or "#RRGGBB" -> "RRGGBB"; None or invalid -> None."""
    if isinstance(color, RGBColor):
        return str(color)
    rgb = _rgb_from_hex(color)
    return str(rgb) if rgb is not None else None


def _to_rgb(color):
    """Normalize the color parameter to RGBColor; None or invalid -> None."""
    if isinstance(color, RGBColor):
        return color
    return _rgb_from_hex(color)


def _relative_luminance(color):
    """WCAG relative luminance of an RGBColor (0.0 dark - 1.0 light)."""
    channels = []
    for value in (color[0], color[1], color[2]):
        channel = min(max(int(value), 0), 255) / 255.0
        if channel <= 0.03928:
            channels.append(channel / 12.92)
        else:
            channels.append(((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_color(color):
    """White or black, whichever reads best on ``color``.

    0.179 is the luminance where the contrast ratio against black and white is
    the same, so dark accents get white text and light accents get black.
    """
    try:
        return RGBColor(0, 0, 0) if _relative_luminance(color) > 0.179 else RGBColor(0xFF, 0xFF, 0xFF)
    except Exception:
        return RGBColor(0xFF, 0xFF, 0xFF)


def _ink_color(color):
    """Accent as text on white; very light accents fall back to black."""
    try:
        if _relative_luminance(color) > 0.45:
            return RGBColor(0, 0, 0)
    except Exception:
        return color
    return color


def _template_id(data):
    """Selected template id, falling back to classic for anything unknown."""
    try:
        raw = _value(data, "template")
        template_id = str(raw or "classic").strip().lower()
    except Exception:
        template_id = "classic"
    return template_id if template_id in latex_gen.TEMPLATE_FILES else "classic"


def _template_palette(data):
    """Colors parsed from the selected template .tex; {} on any failure."""
    filename = latex_gen.TEMPLATE_FILES.get(_template_id(data))
    if not filename:
        return {}
    path = os.path.join(latex_gen.BASE_DIR, "templates", filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            tex = f.read()
    except (OSError, UnicodeError, TypeError, ValueError):
        return {}
    try:
        return latex_gen.template_colors(tex) or {}
    except Exception:
        return {}


def _template_color(colors, key):
    """colors[key] tolerating hostile dicts; never raises."""
    try:
        return colors.get(key)
    except Exception:
        return None


class _Palette(object):
    """Resolved export colors: prefs override the template palette.

    ``accent3`` is the third template accent (the creative yellow). It is read
    from the template only: the prefs palette has no key for it, so it can
    never be overridden by the user. ``template_gray`` is the raw ``gris`` of
    the template (the light bar gray of the chinese family), kept apart from
    ``gray`` because that one is darkened when it would be unreadable as text.
    ``role``/``role_hex`` resolve the colour role names stored by
    :mod:`docx_profiles`; unknown roles fall back to the accent instead of
    raising.
    """

    __slots__ = (
        "accent", "secondary", "accent3", "gray", "text", "template_gray",
        "accent_hex", "secondary_hex", "accent3_hex", "gray_hex",
        "template_gray_hex", "contrast",
    )

    def __init__(self, accent, secondary, gray, text, accent3=None,
                 template_gray=None):
        self.accent = accent
        self.secondary = secondary or accent
        self.accent3 = accent3
        self.gray = gray or accent
        self.template_gray = template_gray if template_gray is not None else self.gray
        self.text = text
        self.accent_hex = str(accent)
        self.secondary_hex = str(self.secondary)
        self.accent3_hex = str(accent3) if accent3 is not None else str(self.secondary)
        self.gray_hex = str(self.gray)
        self.template_gray_hex = str(self.template_gray)
        self.contrast = _contrast_color(accent)

    def role(self, name):
        """RGBColor for a profile colour role; unknown roles -> accent."""
        key = _text(name).lower()
        if key in ("accent", ""):
            return self.accent
        if key in ("accent2", "secondary"):
            return self.secondary
        if key == "accent3":
            return self.accent3 if self.accent3 is not None else self.secondary
        if key == "gray":
            return self.gray
        if key in ("gris", "template_gray", "tail"):
            return self.template_gray
        if key == "text":
            return self.text if self.text is not None else RGBColor(0, 0, 0)
        if key == "white":
            return RGBColor(0xFF, 0xFF, 0xFF)
        if key == "black":
            return RGBColor(0, 0, 0)
        if key == "navy":
            return self.secondary
        if key == "purple":
            return self.accent
        return self.accent

    def role_hex(self, name):
        """``RRGGBB`` string for a profile colour role."""
        return str(self.role(name))



def _readable_template_gray(color):
    """Template gray usable as text; near-white grays fall back to COLOR_GRAY.

    The Chinese template uses a very light ``gris`` (#C4C8D4) for section-bar
    backgrounds. Dates, organizations and links need a readable text gray, so
    a template gray above the luminance threshold is replaced by the default
    one. Section-bar colors are not touched: they come from the accent.
    """
    if color is None:
        return None
    try:
        if _relative_luminance(color) > 0.5:
            return _rgb_from_hex("#" + COLOR_GRAY)
    except Exception:
        return color
    return color


def _build_palette(data, prefs_dict):
    """Prefs palette first, then the template palette, then the defaults."""
    template = _template_palette(data)
    accent = (
        _pref_color(prefs_dict, "primary")
        or _rgb_from_hex(_template_color(template, "accent"))
        or _rgb_from_hex("#" + COLOR_ACCENT)
    )
    secondary = (
        _pref_color(prefs_dict, "secondary")
        or _rgb_from_hex(_template_color(template, "acento2"))
        or accent
    )
    gray = (
        _pref_color(prefs_dict, "gray")
        or _readable_template_gray(_rgb_from_hex(_template_color(template, "gris")))
        or _rgb_from_hex("#" + COLOR_GRAY)
    )
    # Third template accent (creative yellow): template only, prefs cannot set it.
    accent3 = _rgb_from_hex(_template_color(template, "acento3"))
    # Raw gris: the light bar gray of the Chinese templates (never darkened).
    template_gray = _rgb_from_hex(_template_color(template, "gris"))
    return _Palette(
        accent, secondary, gray, _pref_color(prefs_dict, "text"), accent3,
        template_gray,
    )



def _entries_with_content(entries):
    """Filter empty entries, just like latex_gen does with sections."""
    if not isinstance(entries, (list, tuple)):
        return []
    return [entry for entry in entries if _has_content(entry)]


def _has_content(entry):
    if not isinstance(entry, dict):
        return bool(_text(entry))
    try:
        values = list(entry.values())
    except Exception:
        return False
    return any(_text(value) for value in values)


def _date_range(start, end):
    start = _text(start)
    end = _text(end)
    if start and end:
        return f"{start} – {end}"
    return start or end


def _add_paragraphs(doc, text):
    """Add one paragraph per non-empty line (descriptions and profile)."""
    for line in _text(text).splitlines():
        line = line.strip()
        if line:
            doc.add_paragraph(line)


#: Bullet marker per profile ``bullet_kind``: ``(glyph, colour role, size
#: factor, second level glyph, second level role)``. The LaTeX templates draw
#: the markers with ``\rule``/``\rotatebox``; Word uses the closest geometric
#: glyph so no DrawingML or rotation is needed.
_BULLET_STYLES = {
    "dot": ("\u2022", "text", 1.0, "\u2013", "text"),
    "square_navy": ("\u25aa", "accent", 0.95, "\u25aa", "accent2"),
    "square_black": ("\u25a0", "text", 0.62, "\u25aa", "accent2"),
    "diamond_coral": ("\u25c6", "accent2", 0.72, "\u25c6", "accent"),
}


def _add_bullet(container, text, palette=None, profile=None, level=1):
    """Profile bullet with ``text``; returns the paragraph (or None)."""
    paragraph = _bullet_slot(container, palette, profile, level)
    if paragraph is None:
        return None
    try:
        paragraph.add_run(_text(text))
    except Exception:
        return paragraph
    return paragraph


def _bullet_slot(container, palette=None, profile=None, level=1):
    """Paragraph carrying the profile marker, a tab and a hanging indent.

    The marker is a geometric glyph in the template accent (square markers for
    the Chinese school, a coral diamond for playful, the classic dot
    elsewhere). The hanging indent puts the wrapped lines under the text, at
    ``BULLET_INDENT_CM`` (or ``BULLET_INDENT_L2_CM`` at the second level), and
    the vertical rhythm stays tight: no extra space before, a fraction of a
    point after and a 1.0 line spacing.
    """
    profile = _profile_or_default(profile)
    try:
        paragraph = container.add_paragraph()
    except Exception:
        return None
    level = 2 if int(_clamp_number(level, 1, 1, 2)) == 2 else 1
    indent = BULLET_INDENT_L2_CM if level == 2 else BULLET_INDENT_CM
    try:
        fmt = paragraph.paragraph_format
        fmt.left_indent = Cm(indent)
        fmt.first_line_indent = Cm(-indent)
        fmt.space_before = Pt(0)
        fmt.space_after = Pt(BULLET_AFTER_PT)
        fmt.line_spacing = 1.0
    except Exception:
        pass
    style = _BULLET_STYLES.get(_text(profile.bullet_kind)) or _BULLET_STYLES["dot"]
    glyph = style[0] if level == 1 else style[3]
    role = style[1] if level == 1 else style[4]
    factor = _number(style[2], 1.0) * (0.82 if level == 2 else 1.0)
    base = _normal_font_size(container)
    # Explicit tab stop at the hanging indent: without it Word and LibreOffice
    # fall back to the next default tab stop (1.25cm) and the text drifts.
    _tab_stop(paragraph, indent, WD_TAB_ALIGNMENT.LEFT)
    try:
        marker = paragraph.add_run(glyph + "\t")
        marker.font.size = Pt(max(base * factor, 5.0))
        if palette is not None:
            marker.font.color.rgb = palette.role(role)
        _run_font(marker, _family_for(profile))
    except Exception:
        pass
    return paragraph


# ---------------------------------------------------------------------------
# Low-level XML helpers (borders, shading, table chrome)
# ---------------------------------------------------------------------------

def _insert_ordered(parent, element, successors):
    """Insert element respecting the OOXML child order; never raises."""
    try:
        parent.insert_element_before(element, *successors)
    except Exception:
        try:
            parent.append(element)
        except Exception:
            pass


def _bottom_border(paragraph, color, thickness=6, space=1):
    """Add the lower border XML (w:pBdr) to the given paragraph."""
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = p_pr.find(qn("w:pBdr"))
    if p_bdr is None:
        p_bdr = OxmlElement("w:pBdr")
        _insert_ordered(p_pr, p_bdr, _PBDR_SUCCESSORS)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(thickness))
    bottom.set(qn("w:space"), str(space))
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)


def _add_shading(paragraph, color):
    """Add (or update) the paragraph shading XML (w:shd)."""
    p_pr = paragraph._p.get_or_add_pPr()
    shd = p_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        _insert_ordered(p_pr, shd, _SHADING_SUCCESSORS)
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)


def _shade_cell(cell, color):
    """Fill a table cell with ``color`` (w:shd in tcPr)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        _insert_ordered(tc_pr, shd, _TC_SHADING_SUCCESSORS)
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)


def _set_cell_margins(cell, top=40, right=80, bottom=40, left=80):
    """Per-cell padding in twentieths of a point (dxa)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for tag, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        element = OxmlElement("w:" + tag)
        element.set(qn("w:w"), str(int(value)))
        element.set(qn("w:type"), "dxa")
        mar.append(element)
    _insert_ordered(tc_pr, mar, _TC_MAR_SUCCESSORS)


def _remove_table_borders(table):
    """Borderless table: every edge is explicitly ``nil``."""
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement("w:" + edge)
        element.set(qn("w:val"), "nil")
        element.set(qn("w:sz"), "0")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "auto")
        borders.append(element)
    _insert_ordered(tbl_pr, borders, _TBL_BORDERS_SUCCESSORS)


def _text_width_cm(doc):
    """Width of the text block in centimetres.

    A table cell is a valid container for the body of a template that renders
    the whole CV inside a page-wide table (the sidebar family). In that case the
    measure is the cell's own ``w:tcW`` minus its horizontal padding, not the
    page text block.
    """
    try:
        section = doc.sections[0]
        width = section.page_width.cm - section.left_margin.cm - section.right_margin.cm
        if width > 2.0:
            return width
    except Exception:
        pass
    try:
        tc_pr = doc._tc.tcPr
        width = None
        if tc_pr is not None:
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is not None and tc_w.get(qn("w:type")) == "dxa":
                width = _number(tc_w.get(qn("w:w")), 0) * 2.54 / 1440.0
        if width is not None:
            padding = 0.0
            if tc_pr is not None:
                mar = tc_pr.find(qn("w:tcMar"))
                if mar is not None:
                    for tag in ("left", "right"):
                        node = mar.find(qn("w:" + tag))
                        if node is not None:
                            padding += _number(node.get(qn("w:w")), 0) * 2.54 / 1440.0
            return max(width - padding, 1.0)
    except Exception:
        pass
    return PAPER_SIZES["a4"][0] - 2 * DEFAULT_MARGIN


def _set_column_widths(table, widths_cm):
    """Fixed column widths so the header table fills the text block."""
    try:
        table.autofit = False
    except Exception:
        pass
    for index, width in enumerate(widths_cm):
        if index >= len(table.columns):
            break
        try:
            table.columns[index].width = Cm(width)
        except Exception:
            pass
        for cell in table.columns[index].cells:
            try:
                cell.width = Cm(width)
            except Exception:
                pass


def _valid_image(value, exts):
    """Absolute-ish path of a readable image with an accepted extension."""
    path = _text(value)
    if not path:
        return ""
    try:
        if os.path.splitext(path)[1].lower() not in exts:
            return ""
        return path if os.path.isfile(path) else ""
    except Exception:
        return ""


def _fit_width_cm(path, max_width, max_height=None):
    """Width that fits the image inside max_width x max_height, keeping ratio."""
    try:
        from docx.image.image import Image as DocxImage

        image = DocxImage.from_file(path)
        ratio = float(image.height) / float(image.width)
        width = float(max_width)
        if max_height and ratio > 0 and width * ratio > float(max_height):
            width = float(max_height) / ratio
        return min(max(min(width, float(max_width)), 0.2), float(max_width))
    except Exception:
        return float(max_width)


def _insert_picture(paragraph, path, width_cm):
    """Add a picture to a run; any failure leaves the paragraph untouched.

    The inline drawing distances (``wp:inline/@distT|distB|distL|distR``) are
    written as zero: Word treats a missing value as zero but LibreOffice falls
    back to its own 0.32 cm spacing, which shifts the picture inside its
    paragraph and would break the white photo frame of the sidebar bar (the
    frame is a paragraph border that must hug the image).
    """
    try:
        run = paragraph.add_run()
        run.add_picture(path, width=Cm(width_cm))
        for inline in run._element.iter(qn("wp:inline")):
            for attribute in ("distT", "distB", "distL", "distR"):
                inline.set(attribute, "0")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def _profile_or_default(profile):
    """A real TemplateProfile; anything else falls back to classic."""
    if isinstance(profile, docx_profiles.TemplateProfile):
        return profile
    return docx_profiles.PROFILES["classic"]


def _normal_font_size(container):
    """Base font size of the document that owns ``container`` (never raises)."""
    try:
        if hasattr(container, "styles"):
            size = container.styles["Normal"].font.size
        else:
            doc = getattr(getattr(container, "part", None), "document", None)
            size = doc.styles["Normal"].font.size if doc is not None else None
        if size is not None:
            return float(size.pt)
    except Exception:
        pass
    return DEFAULT_FONT_SIZE


def _name_font_size(name, base=None, max_width_cm=None, floor_pt=9.0):
    """Shrink the name for long text; CJK characters count double.

    ``base`` is the template name size (``profile.name_pt``) and
    ``max_width_cm`` the usable measure (header cell, coloured band or sidebar
    body column). The name is the visual anchor of every template and the LaTeX
    ``\\cvfitname`` always keeps it on one line, so the size steps down in 0.5pt
    increments until the estimated width (per-character metrics, CJK counted
    double, bold factor and a 4% substitution safety margin) fits. The old
    character-count tiers survive only for callers without a measure.
    """
    base = _clamp_number(base, NAME_FONT_SIZE, 6.0, 72.0)
    units = 0
    for char in name:
        units += 2 if ord(char) > 0x2E7F else 1
    if max_width_cm is None:
        if units <= 26:
            size = base
        elif units <= 34:
            size = base * 0.9
        else:
            size = base * 0.7
        return max(round(size, 1), 6.0)
    limit = max(float(max_width_cm), 1.0)
    floor = _clamp_number(floor_pt, 9.0, 6.0, base)
    size = base
    # 1.12 covers the Cambria -> Caladea / Liberation substitution. Measured on
    # the LibreOffice render: an all-caps name is ~10% wider than the per-char
    # estimate, and a name that only "just" fits still wraps to a second line.
    while size > floor and _estimate_width_cm(name, size, bold=True) * 1.12 > limit:
        size = round(size - 0.5, 1)
    return max(round(size, 1), floor)


def _reset_line_height(paragraph):
    """Restore automatic line height (undo a decorative exact 1pt height)."""
    try:
        paragraph.paragraph_format.line_spacing = None
    except Exception:
        pass
    try:
        paragraph.paragraph_format.line_spacing_rule = None
    except Exception:
        pass
    return paragraph


def _next_paragraph(container):
    """Reuse a trailing empty paragraph or add a new one (Document or cell).

    A paragraph that already carries a border is a drawn rule, never a text
    slot: reusing it would move the rule under the next block, so it is left
    alone and a fresh paragraph is appended.
    """
    try:
        paragraphs = container.paragraphs
        if paragraphs and not paragraphs[-1].text and not paragraphs[-1].runs:
            paragraph = paragraphs[-1]
            p_pr = paragraph._p.pPr
            if p_pr is None or p_pr.find(qn("w:pBdr")) is None:
                _reset_line_height(paragraph)
                return paragraph
    except Exception:
        pass
    try:
        return container.add_paragraph()
    except Exception:
        return None


def _zero_spacing(paragraph, before=0.0, after=0.0):
    """Remove the vertical spacing of a header paragraph (never raises)."""
    try:
        paragraph.paragraph_format.space_before = Pt(before)
        paragraph.paragraph_format.space_after = Pt(after)
    except Exception:
        pass
    return paragraph


def _shrink_paragraph(paragraph, pt=1.0):
    """Collapse an empty helper paragraph so it does not add header height."""
    if paragraph is None:
        return
    _zero_spacing(paragraph)
    docx_shapes.set_exact_line_height(paragraph, pt)
    try:
        paragraph.paragraph_format.first_line_indent = Cm(0)
    except Exception:
        pass


def _shrink_empty_paragraphs(container):
    """Collapse every empty paragraph of a header cell."""
    try:
        paragraphs = list(container.paragraphs)
    except Exception:
        return
    for paragraph in paragraphs:
        try:
            if not paragraph.text and not paragraph.runs:
                _shrink_paragraph(paragraph)
        except Exception:
            continue


def _write_name(paragraph, name, palette, profile, color=None,
                base_pt=None, max_width_cm=None):
    """Render the CV name with the profile size/caps/weight and its colour."""
    if paragraph is None:
        return None
    try:
        run = paragraph.add_run(name)
        run.bold = bool(profile.name_bold)
        if profile.name_caps:
            run.font.small_caps = True
        size = _name_font_size(
            name, base_pt if base_pt is not None else profile.name_pt,
            max_width_cm,
        )
        run.font.size = Pt(size)
        run.font.color.rgb = color if color is not None else palette.role(profile.name_role)
        _run_font(run, _family_for(profile))
        return run
    except Exception:
        try:
            return paragraph.add_run(name)
        except Exception:
            return None


def _add_contacts(container, d, L, palette, profile=None, align=None, before_pt=1.0):
    """Personal data, then the job objective, then the social links.

    Every contact is a separate rendered line, like the LaTeX templates: the
    personal block (phone, email, address, school and every extra field) plus
    the objective share one paragraph whose lines are separated by ``w:br``,
    and the social links go in a second, smaller and gray paragraph (also one
    line each). Keeping the personal/objective lines inside one paragraph is
    deliberate: the public Word bridge and the tests read that block as one
    ``paragraph.text`` value while the PDF stacks it one item per line.
    The contact block carries no divider rule. ``container`` is a Document or
    a table cell; ``align`` centers it for the Harvard header and
    ``before_pt`` is the gap above the first line (the LaTeX ``\\vspace``
    between a band and its contacts).
    """
    personal, objective, socials = _contact_groups(d, L)
    pairs = list(personal) + list(objective)
    if not pairs and not socials:
        return None

    base = _normal_font_size(container)
    family = _family_for(_profile_or_default(profile))
    paragraph = None
    if pairs:
        paragraph = _next_paragraph(container)
        if paragraph is None:
            return None
        if align is not None:
            paragraph.alignment = align
        paragraph.paragraph_format.space_before = Pt(max(_number(before_pt, 1.0), 0.0))
        paragraph.paragraph_format.space_after = Pt(1 if socials else 2)
        try:
            paragraph.paragraph_format.line_spacing = 1.0
        except Exception:
            pass
        for i, pair in enumerate(pairs):
            if i:
                paragraph.add_run().add_break()
            _contact_pair(paragraph, pair, palette, base, family)

    if socials:
        social_paragraph = _next_paragraph(container)
        if social_paragraph is None:
            return paragraph
        if align is not None:
            social_paragraph.alignment = align
        social_paragraph.paragraph_format.space_before = Pt(1 if paragraph is None else 0)
        social_paragraph.paragraph_format.space_after = Pt(2)
        try:
            social_paragraph.paragraph_format.line_spacing = 1.0
        except Exception:
            pass
        # A plain point value, not a Length: _contact_pair wraps it in Pt()
        # itself, and nesting one Length inside Pt() would write an out-of-range
        # w:sz (228600 instead of 18 half-points) that Word silently ignores.
        size = max(float(base) - 2.0, 7.0)
        for i, pair in enumerate(socials):
            if i:
                social_paragraph.add_run().add_break()
            _contact_pair(
                social_paragraph, pair, palette, size, family,
                value_color=palette.gray,
            )
            # Labels of the social block are gray too (LaTeX dims the whole
            # secondary block, not only its values).
            try:
                label_run = social_paragraph.runs[-2]
                label_run.font.color.rgb = palette.gray
            except Exception:
                pass
    return paragraph


def _header_images(d):
    """(logo path, photo path) of the data; empty strings when unusable."""
    return (
        _valid_image(_value(d, "school_logo"), LOGO_EXTS),
        _valid_image(_value(d, "photo"), PHOTO_EXTS),
    )


def _photo_box_cm(d, profile, total_cm):
    """Photo box from the data size capped by the profile ratio and 12x15cm."""
    width = _clamp_number(
        _value(d, "photo_width_cm"), DEFAULT_PHOTO_WIDTH, 1.0, MAX_PHOTO_WIDTH_CM,
    )
    height = _clamp_number(
        _value(d, "photo_height_cm"), DEFAULT_PHOTO_HEIGHT, 1.0, MAX_PHOTO_HEIGHT_CM,
    )
    ratio_width = max(float(profile.photo_ratio) * float(total_cm), 1.0)
    return min(width, ratio_width, MAX_PHOTO_WIDTH_CM), height


def _logo_box_cm(d, profile, photo_width_cm):
    """Logo box: the profile ratio of the photo, never above 6x4cm."""
    width = _clamp_number(
        _value(d, "school_logo_width_cm"), DEFAULT_LOGO_WIDTH, 0.5, MAX_LOGO_WIDTH_CM,
    )
    height = _clamp_number(
        _value(d, "school_logo_height_cm"), DEFAULT_LOGO_HEIGHT, 0.3, MAX_LOGO_HEIGHT_CM,
    )
    ratio_width = max(float(profile.logo_ratio) * float(photo_width_cm), 0.5)
    return min(width, ratio_width, MAX_LOGO_WIDTH_CM), height


def _new_header_table(doc, widths_cm, align=None):
    """One-row borderless header table with fixed column widths."""
    table = doc.add_table(rows=1, cols=len(widths_cm))
    try:
        table.alignment = align if align is not None else WD_TABLE_ALIGNMENT.LEFT
    except Exception:
        pass
    _remove_table_borders(table)
    _set_column_widths(table, widths_cm)
    return table


def _cell_top(cell):
    try:
        cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
    except Exception:
        pass


def _add_logo(container, path, width_cm, height_cm, align, before_pt=0.0):
    """Logo paragraph aligned like the photo below it."""
    paragraph = _next_paragraph(container)
    if paragraph is None:
        return False
    try:
        paragraph.alignment = align
    except Exception:
        pass
    _zero_spacing(paragraph, max(_number(before_pt, 0.0), 0.0), 2)
    return _insert_picture(paragraph, path, _fit_width_cm(path, width_cm, height_cm))


def _add_framed_photo(container, path, width_cm, height_cm, palette, align):
    """Photo inside a thin gray frame (LaTeX's ``\\fcolorbox``).

    The frame is a nested 1x1 borderless table whose only cell carries the
    picture and the four ``w:tcBorders``; nesting stays at depth 2 (header
    table + this table). When the table cannot be created the picture is still
    inserted without a frame.
    """
    frame_width = width_cm + 0.14
    table = docx_shapes.fixed_table(container, (frame_width,))
    if table is not None:
        cell = table.cell(0, 0)
        _set_cell_margins(cell, top=20, right=20, bottom=20, left=20)
        docx_shapes.image_frame(cell, palette.gray_hex, 0.5)
        paragraph = cell.paragraphs[0]
        try:
            paragraph.alignment = align
        except Exception:
            pass
        _zero_spacing(paragraph)
        inserted = _insert_picture(paragraph, path, width_cm)
        try:
            table.alignment = align
        except Exception:
            pass
        _shrink_empty_paragraphs(container)
        return inserted
    paragraph = _next_paragraph(container)
    if paragraph is None:
        return False
    try:
        paragraph.alignment = align
    except Exception:
        pass
    _zero_spacing(paragraph)
    return _insert_picture(paragraph, path, width_cm)


def _header_rule(doc, color_hex, size_pt, space_pt=1.0, gap_before_pt=0.0):
    """Full-width hairline under the header (a body paragraph border)."""
    paragraph = doc.add_paragraph()
    _zero_spacing(paragraph, gap_before_pt, 0)
    docx_shapes.set_exact_line_height(paragraph, 0.8)
    docx_shapes.set_rule(paragraph, "bottom", color_hex, size_pt, space_pt)
    return paragraph


def _header_classic(doc, d, L, palette, profile):
    """Name + contacts left, logo above the framed photo right, accent rule."""
    total = _text_width_cm(doc)
    logo, photo = _header_images(d)
    has_right = bool(logo or photo)
    widths = (total * 0.70, total * 0.30) if has_right else (total,)
    table = _new_header_table(doc, widths)

    left = table.cell(0, 0)
    _cell_top(left)
    _set_cell_margins(left, top=0, right=120, bottom=0, left=0)
    name = _text(_value(d, "name")) or L["title_short"]
    name_paragraph = left.paragraphs[0]
    _zero_spacing(name_paragraph, 0, 2)
    _write_name(
        name_paragraph, name, palette, profile,
        color=palette.role("text"),
        max_width_cm=max(widths[0] - 0.45, 1.0),
    )
    _add_contacts(left, d, L, palette, profile)

    if has_right:
        right = table.cell(0, 1)
        _cell_top(right)
        _set_cell_margins(right, top=0, right=0, bottom=0, left=0)
        photo_width, photo_height = _photo_box_cm(d, profile, total)
        if logo:
            logo_width, logo_height = _logo_box_cm(d, profile, photo_width)
            _add_logo(
                right, logo, logo_width, logo_height, WD_ALIGN_PARAGRAPH.RIGHT,
            )
        if photo:
            _add_framed_photo(
                right, photo, photo_width, photo_height, palette,
                WD_ALIGN_PARAGRAPH.RIGHT,
            )

    _header_rule(doc, palette.role_hex("accent"), 0.8, 1)


def _header_harvard(doc, d, L, palette, profile):
    """Centred small-caps name, contacts, logo/photo and a gray double hairline."""
    total = _text_width_cm(doc)
    logo, photo = _header_images(d)
    table = _new_header_table(doc, (total,), WD_TABLE_ALIGNMENT.CENTER)
    cell = table.cell(0, 0)
    _cell_top(cell)
    _set_cell_margins(cell, top=0, right=60, bottom=0, left=60)

    name = _text(_value(d, "name")) or L["title_short"]
    name_paragraph = cell.paragraphs[0]
    _zero_spacing(name_paragraph, 0, 2)
    try:
        name_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    except Exception:
        pass
    _write_name(
        name_paragraph, name, palette, profile,
        color=palette.role("accent"),
        max_width_cm=max(total - 0.6, 1.0),
    )
    _add_contacts(
        cell, d, L, palette, profile, align=WD_ALIGN_PARAGRAPH.CENTER,
    )

    photo_width, photo_height = _photo_box_cm(d, profile, total)
    # PDF order: the framed photo first, then the school logo centred under it
    # with a 0.15em gap (1.65pt at the 11pt body size).
    if photo:
        _add_framed_photo(
            cell, photo, photo_width, photo_height, palette,
            WD_ALIGN_PARAGRAPH.CENTER,
        )
    if logo:
        logo_width, logo_height = _logo_box_cm(d, profile, photo_width)
        _add_logo(
            cell, logo, logo_width, logo_height, WD_ALIGN_PARAGRAPH.CENTER,
            before_pt=1.65,
        )

    _header_rule(doc, palette.role_hex("gray"), 0.5, 1)
    _header_rule(doc, palette.role_hex("gray"), 0.25, 0, gap_before_pt=1.6)


def _header_modern(doc, d, L, palette, profile):
    """24pt accent name left, photo right and a heavy 2.5pt accent rule."""
    total = _text_width_cm(doc)
    logo, photo = _header_images(d)
    has_right = bool(logo or photo)
    photo_width, photo_height = _photo_box_cm(d, profile, total)
    if has_right:
        right_width = min(max(photo_width + 0.3, total * profile.photo_ratio), total * 0.40)
        widths = (total - right_width, right_width)
    else:
        right_width = 0.0
        widths = (total,)
    table = _new_header_table(doc, widths)

    left = table.cell(0, 0)
    _cell_top(left)
    _set_cell_margins(left, top=0, right=120, bottom=0, left=0)
    name = _text(_value(d, "name")) or L["title_short"]
    name_paragraph = left.paragraphs[0]
    _zero_spacing(name_paragraph, 0, 2)
    _write_name(
        name_paragraph, name, palette, profile,
        color=palette.role("accent"),
        max_width_cm=max(total - right_width - 0.45, 1.0),
    )
    _add_contacts(left, d, L, palette, profile)

    if has_right:
        right = table.cell(0, 1)
        _cell_top(right)
        _set_cell_margins(right, top=0, right=0, bottom=0, left=0)
        if logo:
            logo_width, logo_height = _logo_box_cm(d, profile, photo_width)
            _add_logo(
                right, logo, logo_width, logo_height, WD_ALIGN_PARAGRAPH.RIGHT,
            )
        if photo:
            _add_framed_photo(
                right, photo, photo_width, photo_height, palette,
                WD_ALIGN_PARAGRAPH.RIGHT,
            )

    _header_rule(doc, palette.role_hex("accent"), 2.5, 1)


def _header_creative(doc, d, L, palette, profile):
    """Full-width accent band with the white name, contacts/photo below it."""
    total = _text_width_cm(doc)
    logo, photo = _header_images(d)
    table = _new_header_table(doc, (total,))
    cell = table.cell(0, 0)
    _cell_top(cell)
    _set_cell_margins(cell, top=0, right=0, bottom=0, left=0)

    name = _text(_value(d, "name")) or L["title_short"]
    band_color = palette.role_hex(profile.band_role or "accent")
    band = docx_shapes.fixed_table(cell, (total,))
    if band is not None:
        band_cell = band.cell(0, 0)
        docx_shapes.shade_cell(band_cell, band_color)
        _set_cell_margins(band_cell, top=40, right=240, bottom=40, left=240)
        docx_shapes.exact_row_height(band.rows[0], 1.3, "atLeast")
        try:
            band_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        except Exception:
            pass
        band_paragraph = band_cell.paragraphs[0]
        _zero_spacing(band_paragraph)
        _write_name(
            band_paragraph, name, palette, profile,
            color=palette.role("white"),
            max_width_cm=max(total - 0.8, 1.0),
        )
        _shrink_empty_paragraphs(cell)
    else:
        band_paragraph = cell.paragraphs[0]
        _zero_spacing(band_paragraph)
        docx_shapes.shade_paragraph(band_paragraph, band_color)
        docx_shapes.set_exact_line_height(band_paragraph, 36.85)
        _write_name(
            band_paragraph, name, palette, profile,
            color=palette.role("white"),
            max_width_cm=max(total - 0.8, 1.0),
        )

    photo_width, photo_height = _photo_box_cm(d, profile, total)
    if logo:
        logo_width, logo_height = _logo_box_cm(d, profile, photo_width)
        _add_logo(
            cell, logo, logo_width, logo_height, WD_ALIGN_PARAGRAPH.RIGHT,
        )

    if photo:
        right_width = total * 0.32
        left_width = total * 0.68
        content = docx_shapes.fixed_table(cell, (left_width, right_width))
        if content is not None:
            contacts_cell = content.cell(0, 0)
            _set_cell_margins(contacts_cell, top=40, right=120, bottom=0, left=0)
            _add_contacts(contacts_cell, d, L, palette, profile)
            photo_cell = content.cell(0, 1)
            _set_cell_margins(photo_cell, top=40, right=20, bottom=0, left=20)
            docx_shapes.image_frame(photo_cell, palette.gray_hex, 0.5)
            paragraph = photo_cell.paragraphs[0]
            try:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            except Exception:
                pass
            _zero_spacing(paragraph)
            _insert_picture(paragraph, photo, photo_width)
            _shrink_empty_paragraphs(cell)
    else:
        _add_contacts(cell, d, L, palette, profile)
        _shrink_empty_paragraphs(cell)

    _header_rule(doc, palette.role_hex("accent"), 1.2, 1)
    _header_rule(doc, palette.role_hex("gray"), 0.4, 0, gap_before_pt=1.6)


# ---------------------------------------------------------------------------
# Shared helpers for the plate, band, badge and grid headers
# ---------------------------------------------------------------------------

def _dxa(cm):
    """Centimetres -> twips (``dxa``) for the ``w:tcMar`` values."""
    try:
        return int(round(float(cm) * 1440.0 / 2.54))
    except Exception:
        return 0


def _em_cm(em, pt):
    """Width of ``em`` ems of ``pt`` points, in centimetres."""
    return docx_shapes.pt_to_cm(_number(em, 0.4) * _number(pt, NAME_FONT_SIZE))


def _family_for(profile):
    """Explicit Word font family of the profile (serif or sans)."""
    return SANS_FONT if _text(profile.font_family).lower() == "sans" else SERIF_FONT


def _run_font(run, family):
    """Write the explicit ascii/hAnsi/eastAsia fonts on an existing run."""
    if run is None:
        return None
    try:
        run.font.name = family
        _set_rpr_fonts(run._element.get_or_add_rPr(), family)
    except Exception:
        pass
    return run


def _contact_groups(d, L):
    """``(personal, objective, socials)`` contact pairs in LaTeX order.

    Every item is ``(label, value, mono)``: the phone and the e-mail carry
    ``mono=True`` because the playful header sets their values in a monospace
    face, exactly like the ``\\texttt`` of the LaTeX contact lines.
    """
    personal = []

    def add(label, value, mono=False):
        value = _text(value)
        if value:
            personal.append((label, value, mono))

    add(L["phone"], _value(d, "phone"), True)
    add(L["email"], _value(d, "email"), True)
    add(L["address"], _value(d, "address"))
    add(L["school_name"], _value(d, "school_name"))
    extra_fields = _value(d, "extra_fields")
    if isinstance(extra_fields, (list, tuple)):
        for x in extra_fields:
            if not isinstance(x, dict):
                continue
            label = _text(_value(x, "label"))
            value = _text(_value(x, "value"))
            if label and value:
                personal.append((label + ":", value, False))

    objective = []
    profession = _text(_value(d, "profession"))
    if profession:
        objective.append((L["profession"], profession, False))

    socials = []
    raw_socials = _value(d, "socials")
    if isinstance(raw_socials, (list, tuple)):
        for x in raw_socials:
            try:
                if not isinstance(x, dict):
                    continue
                value = _text(_value(x, "value"))
                if not value:
                    continue
                label = latex_gen.social_label(_value(x, "network"), _value(x, "label"), L)
            except Exception:
                continue
            socials.append((label + ":", value, False))
    return personal, objective, socials


def _split_contacts(personal, objective, socials):
    """Left/right contact split: personal data + objective | social links.

    Without social links the left column is balanced across both columns
    (every other line), which is what ``latex_gen._contact_columns`` does.
    """
    left = list(personal or ()) + list(objective or ())
    right = list(socials or ())
    if not right:
        right = left[1::2]
        left = left[0::2]
    return left, right


def _contact_pair(paragraph, pair, palette, size_pt, family, mono_color=None,
                  value_color=None):
    """One ``label value`` line; phone/e-mail values may go monospace."""
    try:
        label, value, mono = pair
    except Exception:
        return None
    try:
        size = Pt(max(_number(size_pt, 10.0), 1.0))
        label_run = paragraph.add_run(_text(label) + " ")
        label_run.bold = True
        label_run.font.size = size
        _run_font(label_run, family)
        value_run = paragraph.add_run(_text(value))
        value_run.font.size = size
        if mono:
            _run_font(value_run, MONO_FONT)
            if mono_color is not None:
                value_run.font.color.rgb = mono_color
        else:
            _run_font(value_run, family)
            if value_color is not None:
                value_run.font.color.rgb = value_color
        return value_run
    except Exception:
        return None


def _contact_cell(cell, pairs, palette, family, size_pt, gap_pt, value_color,
                  mono_color):
    """Fill one column cell with one paragraph per contact pair."""
    _set_cell_margins(cell, top=0, right=0, bottom=0, left=0)
    for index, pair in enumerate(pairs):
        try:
            paragraph = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
        except Exception:
            return cell
        _zero_spacing(paragraph, 0, gap_pt if index < len(pairs) - 1 else 0)
        _contact_pair(paragraph, pair, palette, size_pt, family, mono_color, value_color)
    return cell


def _contact_columns(container, width_cm, left, right, palette, family,
                     size_pt=10.0, gap_pt=1.8, right_color=None,
                     mono_color=None, ratio=0.47):
    """Nested two-column contact grid with a narrow gutter and no rules.

    The grid is a 3-column table (column, gutter, column) so the two contact
    blocks keep a fixed axis without depending on tab stops. A single group
    takes the full width. It stays at nesting depth 2 (header table + grid).
    """
    left = list(left or ())
    right = list(right or ())
    if not left and not right:
        return None
    width = max(_number(width_cm, docx_shapes.DEFAULT_TEXT_WIDTH_CM), 1.0)
    if not left or not right:
        column = left or right
        table = docx_shapes.fixed_table(container, (width,))
        if table is None:
            return None
        _contact_cell(
            table.cell(0, 0), column, palette, family, size_pt, gap_pt,
            None if left else right_color, mono_color,
        )
        return table
    ratio = min(max(_number(ratio, 0.47), 0.2), 0.49)
    side = width * ratio
    gutter = max(width - 2.0 * side, 0.0)
    table = docx_shapes.fixed_table(container, (side, gutter, side))
    if table is None:
        return None
    _contact_cell(
        table.cell(0, 0), left, palette, family, size_pt, gap_pt, None, mono_color,
    )
    _contact_cell(
        table.cell(0, 2), right, palette, family, size_pt, gap_pt, right_color,
        mono_color,
    )
    return table


def _drop_leading_empty(container):
    """Remove the placeholder paragraph that precedes a nested header table.

    python-docx gives every cell one empty paragraph; when a nested table is
    appended first, that paragraph would add a full empty line above the
    shape. It is only removed when the cell keeps another block element.
    ``w:tcPr`` is the first child of a cell, so the paragraph is searched
    after it instead of assuming children[0] is the paragraph.
    """
    try:
        children = list(container._tc)
    except Exception:
        return
    if len(children) < 3:
        return
    first = children[1]
    if first.tag != qn("w:p"):
        return
    if list(first.iterchildren()):
        return
    try:
        container._tc.remove(first)
    except Exception:
        pass


def _cell_rule(container, color_hex, size_pt, space_pt=1.0, gap_pt=0.0):
    """Hairline between two blocks of the same header cell."""
    paragraph = _next_paragraph(container)
    if paragraph is None:
        return None
    _zero_spacing(paragraph, gap_pt, 0)
    docx_shapes.set_exact_line_height(paragraph, 0.8)
    docx_shapes.set_rule(paragraph, "bottom", color_hex, size_pt, space_pt)
    return paragraph


def _add_plain_picture(container, path, width_cm, align, top=0, bottom=0):
    """Picture without a frame (the ribbon keeps its photo inside the band)."""
    paragraph = _next_paragraph(container)
    if paragraph is None:
        return False
    try:
        paragraph.alignment = align
    except Exception:
        pass
    _zero_spacing(paragraph, top, bottom)
    return _insert_picture(paragraph, path, width_cm)


def _ribbon_wing(container, total_cm, palette, steps=14):
    """Stair-stepped accent + gold ribbon at the top of the ribbon header.

    Documented approximation: the LaTeX template paints a full-width ribbon
    rotated -1.6 degrees in the top margin, and Word cannot rotate a shape
    without DrawingML. The export draws the same ribbon as a stack of shaded
    bars whose right end steps inward (the diagonal cut of the wing) with a
    parallel gold trim bar under it, so the block reads as a slanted wing and
    never as a plain rectangle.
    """
    total = max(_number(total_cm, docx_shapes.DEFAULT_TEXT_WIDTH_CM), 2.0)
    if total < 4.0:
        steps = 6
    accent = palette.role_hex("accent")
    gold = palette.role_hex("accent2")
    cut = min(max(total * 0.20, 1.8), 4.0)
    step = cut / float(steps + 2)
    for index in range(steps):
        docx_shapes.shaded_bar(
            container, accent, width_cm=None, thickness_pt=1.25,
            left_cm=0.0, right_cm=index * step,
        )
    for index in range(2):
        docx_shapes.shaded_bar(
            container, gold, width_cm=None, thickness_pt=1.3,
            left_cm=0.0, right_cm=(steps + index) * step,
        )
    gap = None
    try:
        gap = container.add_paragraph()
    except Exception:
        gap = None
    if gap is not None:
        _zero_spacing(gap, 0, 0)
        docx_shapes.set_exact_line_height(gap, 3.0)
    return container


def _shade_run(run, color_hex):
    """Fill the run box with ``color_hex`` (``w:shd`` in the run ``rPr``).

    Word-safe primitive: a shaded run is a small solid rectangle around the
    glyph, which is how the playful square badges are approximated without
    DrawingML, VML, rotation or a shaded table cell spanning the whole row.
    """
    if run is None:
        return None
    try:
        r_pr = run._element.get_or_add_rPr()
        shd = r_pr.find(qn("w:shd"))
        if shd is None:
            shd = OxmlElement("w:shd")
            _insert_ordered(
                r_pr, shd,
                ("w:fitText", "w:vertAlign", "w:rtl", "w:cs", "w:em",
                 "w:lang", "w:eastAsianLayout", "w:specVanish", "w:oMath"),
            )
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), _text(color_hex) or "FFFFFF")
    except Exception:
        pass
    return run


def _badge_contacts(container, pairs, palette, family, width_cm, size_pt=10.0):
    """One separate purple square badge with a white glyph per contact line.

    The LaTeX playful header draws a small filled square with a white glyph
    before every contact. The old export shaded a whole table cell per row,
    which merged into a continuous purple rail with a coral diamond. A shaded
    run (``w:shd`` on the glyph run) gives each badge its own compact square,
    separated by the ordinary line spacing, and stays inside the Word-safe
    subset. Returns the last paragraph (or ``None``).
    """
    pairs = list(pairs or ())
    if not pairs:
        return None
    accent = palette.role_hex("accent")
    white = RGBColor(0xFF, 0xFF, 0xFF)
    size = max(_number(size_pt, 10.0), 7.0)
    width = max(_number(width_cm, docx_shapes.DEFAULT_TEXT_WIDTH_CM), 1.5)
    last = None
    for pair in pairs:
        try:
            paragraph = _next_paragraph(container)
        except Exception:
            return last
        if paragraph is None:
            return last
        _zero_spacing(paragraph, 1.4, 1.4)
        try:
            paragraph.paragraph_format.line_spacing = 1.0
            paragraph.paragraph_format.left_indent = Cm(0)
        except Exception:
            pass
        # Two normal spaces on each side make the shaded box as wide as a line
        # box, i.e. a square badge instead of a tall rectangle.
        badge = paragraph.add_run("  \u2713  ")
        badge.font.size = Pt(max(size - 2.0, 6.0))
        badge.font.color.rgb = white
        _run_font(badge, SANS_FONT)
        _shade_run(badge, accent)
        _contact_pair(paragraph, pair, palette, size, family, mono_color=palette.accent)
        last = paragraph
    return last


def _header_chinese(doc, d, L, palette, profile):
    """1.6cm accent plate behind a white 22pt name, contacts below the plate."""
    total = _text_width_cm(doc)
    logo, photo = _header_images(d)
    has_right = bool(logo or photo)
    widths = (total * 0.70, total * 0.30) if has_right else (total,)
    table = _new_header_table(doc, widths)

    left = table.cell(0, 0)
    _cell_top(left)
    _set_cell_margins(left, top=0, right=0, bottom=0, left=0)

    name = _text(_value(d, "name")) or L["title_short"]
    name_pt = _clamp_number(profile.name_pt, 22.0, 10.0, 40.0)
    pad_cm = _em_cm(0.4, name_pt)
    band_width = widths[0]
    band_height = max(docx_shapes.pt_to_cm(_number(profile.band_height_pt, 45.35)), 1.0)
    band = docx_shapes.fixed_table(left, (band_width,))
    if band is not None:
        band_cell = band.cell(0, 0)
        docx_shapes.shade_cell(band_cell, palette.role_hex("accent"))
        _set_cell_margins(band_cell, top=0, right=0, bottom=0, left=_dxa(pad_cm))
        docx_shapes.exact_row_height(band.rows[0], band_height, "atLeast")
        try:
            band_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        except Exception:
            pass
        paragraph = band_cell.paragraphs[0]
        _zero_spacing(paragraph)
        _write_name(
            paragraph, name, palette, profile, color=palette.role("white"),
            base_pt=name_pt,
            max_width_cm=max(band_width - pad_cm - 0.2, 1.0),
        )
        _drop_leading_empty(left)
    else:
        paragraph = left.paragraphs[0]
        _zero_spacing(paragraph)
        docx_shapes.shade_paragraph(paragraph, palette.role_hex("accent"))
        docx_shapes.set_exact_line_height(
            paragraph, max(_number(profile.band_height_pt, 45.35), 12.0),
        )
        try:
            paragraph.paragraph_format.left_indent = Cm(pad_cm)
        except Exception:
            pass
        _write_name(
            paragraph, name, palette, profile, color=palette.role("white"),
            base_pt=name_pt, max_width_cm=max(total - pad_cm - 0.3, 1.0),
        )

    _add_contacts(left, d, L, palette, profile, before_pt=6.0)

    if has_right:
        right = table.cell(0, 1)
        _cell_top(right)
        _set_cell_margins(right, top=0, right=0, bottom=0, left=0)
        photo_width, photo_height = _photo_box_cm(d, profile, total)
        if logo:
            logo_width, logo_height = _logo_box_cm(d, profile, photo_width)
            _add_logo(right, logo, logo_width, logo_height, WD_ALIGN_PARAGRAPH.RIGHT)
        if photo:
            _add_framed_photo(
                right, photo, photo_width, photo_height, palette,
                WD_ALIGN_PARAGRAPH.RIGHT,
            )

    _header_rule(doc, palette.role_hex("accent"), 1.0, 1, gap_before_pt=4.0)


def _page_margins_cm(doc):
    """``(left, right, top, bottom, page width)`` of the first section in cm."""
    try:
        section = doc.sections[0]
        return (
            float(section.left_margin.cm),
            float(section.right_margin.cm),
            float(section.top_margin.cm),
            float(section.bottom_margin.cm),
            float(section.page_width.cm),
        )
    except Exception:
        page = PAPER_SIZES["a4"][0]
        return (DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, DEFAULT_MARGIN, page)


def _paragraph_indents(paragraph, left_cm=0.0, right_cm=0.0):
    """Set literal left/right indents in centimetres (never raises)."""
    if paragraph is None:
        return None
    try:
        paragraph.paragraph_format.left_indent = Cm(max(_number(left_cm, 0.0), 0.0))
        paragraph.paragraph_format.right_indent = Cm(max(_number(right_cm, 0.0), 0.0))
    except Exception:
        pass
    return paragraph


def _add_bar_photo(container, path, width_cm, inner_cm, pad_cm, align):
    """Photo with the 3pt white frame of the sidebar bar.

    LaTeX wraps the picture in ``\\fcolorbox{white}{white}`` with
    ``\\fboxsep=3pt``: a white ring around the picture. The ring is a white
    paragraph border rather than a nested table: LibreOffice misplaces nested
    tables when the parent header table has a negative ``w:tblInd`` (it anchors
    them to the page's left margin), and a paragraph border is a Word-safe
    primitive that renders in both engines. The paragraph indents shrink the
    border box to the picture width, so the 3pt stroke hugs the image and the
    picture stays an inline shape of the document.
    """
    paragraph = _next_paragraph(container)
    if paragraph is None:
        return False
    pad = max(_number(pad_cm, 0.8), 0.0)
    pad += max((_number(inner_cm, 4.6) - _number(width_cm, 1.0)) / 2.0, 0.0)
    _paragraph_indents(paragraph, pad, pad)
    _zero_spacing(paragraph)
    try:
        paragraph.alignment = align
    except Exception:
        pass
    inserted = _insert_picture(paragraph, path, width_cm)
    if inserted:
        docx_shapes.set_rule(
            paragraph, ("top", "left", "bottom", "right"), "FFFFFF", 3.0, 0,
        )
    return inserted


def _sidebar_contacts(container, d, L, size_pt=8.0, before_pt=0.0, pad_cm=0.8):
    """White contact lines of the sidebar bar, one pair per line.

    The order matches every other header: phone, e-mail, address, school,
    extra fields, profession, then the social links. Labels stay bold and the
    whole block is white so it reads over the accent fill; the social links
    are not dimmed because the LaTeX bar uses a single ``\\color{white}``
    block for all of them. ``pad_cm`` is applied as a paragraph indent (the
    bar cell keeps zero cell margins so LibreOffice and Word agree on the
    geometry under the negative table indent).
    """
    personal, objective, socials = _contact_groups(d, L)
    pairs = list(personal) + list(objective) + list(socials)
    if not pairs:
        return None
    white = RGBColor(0xFF, 0xFF, 0xFF)
    size = Pt(max(_number(size_pt, 8.0), 6.0))
    for index, pair in enumerate(pairs):
        paragraph = _next_paragraph(container)
        if paragraph is None:
            break
        _zero_spacing(paragraph, before_pt if index == 0 else 0.0, 0.6)
        _paragraph_indents(paragraph, pad_cm, pad_cm)
        try:
            paragraph.paragraph_format.line_spacing = 1.0
        except Exception:
            pass
        try:
            label, value, _mono = pair
        except Exception:
            continue
        label_run = paragraph.add_run(_text(label) + " ")
        label_run.bold = True
        value_run = paragraph.add_run(_text(value))
        for run in (label_run, value_run):
            run.font.size = size
            run.font.color.rgb = white
            _run_font(run, SERIF_FONT)
    return pairs


def _header_sidebar(doc, d, L, palette, profile):
    """Full-bleed accent side bar, with the whole CV in the body cell.

    Mirrors ``templates/sidebar/sidebar.tex`` and ``sidebar-right``: a 6.2 cm
    accent bar on the page edge (left or right), white content inset by 0.8 cm
    on both sides (4.6 cm inner column), a white-framed photo below the school
    logo, white contacts, and a body column with the 24pt accent name, the gray
    small-caps profession, the 1.2pt accent rule and then every section.

    Unlike the old header-card rendering, the name and the **whole body** live
    in the body cell of the same page-wide table, so the page reads like the
    PDF: the bar runs from the top margin to the bottom margin, the text column
    sits beside it and there is no empty right-hand band under the header. The
    row is allowed to split across pages; LibreOffice and Word repeat the cell
    shading on every page fragment, so the accent bar continues on pages 2+.

    Documented divergence: the PDF paints a *page-1 only* bar as tall as the
    paper (a shipout overlay that cannot be expressed in normal flow). Here the
    bar starts at the top margin (not the paper edge) and continues on every
    page that the single table row occupies. On the last page it ends with the
    content instead of the paper bottom.

    Geometry: the table is page-wide and ``w:tblInd`` is the negative left page
    margin, so its left edge lands on the paper edge. A negative *right* indent
    does not exist in WordprocessingML, so the mirrored variant keeps the bar
    as the trailing column and adds an empty leading cell as wide as the left
    margin. Body cell widths are exact: 12.0 cm on the left variant (from the
    7 cm body axis to the right margin) and 11.4 cm on the mirrored one (from
    the left margin to the bar gutter).
    """
    left_margin, right_margin, top_margin, bottom_margin, page_width = _page_margins_cm(doc)
    try:
        page_height = float(doc.sections[0].page_height.cm)
    except Exception:
        page_height = PAPER_SIZES["a4"][1]
    mirrored = _text(profile.template).lower().endswith("-right")

    bar_cm = _clamp_number(profile.sidebar_bar_cm, 6.2, 2.5, 10.0)
    body_left = _clamp_number(profile.body_left_cm, 7.0, 1.0, page_width - 5.0)
    inner_cm = _clamp_number(profile.sidebar_inner_cm, 4.6, 1.0, bar_cm - 0.4)
    pad_cm = max((bar_cm - inner_cm) / 2.0, 0.2)

    if mirrored:
        # Body from the left margin to the bar gutter; a 1.4 cm gutter matches
        # the LaTeX sidebar-right geometry (body 2.0-13.3, bar 14.7-20.9).
        gutter = max(_number(profile.body_left_cm, 7.0) - bar_cm, 1.2)
        body_width = max(page_width - left_margin - bar_cm - gutter, 3.0)
        widths = (left_margin, body_width, gutter, bar_cm)
        body_index = 1
    else:
        gutter = max(body_left - bar_cm, 0.4)
        body_width = max(page_width - body_left - right_margin, 3.0)
        widths = (bar_cm, gutter, body_width, right_margin)
        body_index = 2
    # Absorb rounding so the table really spans the paper.
    total = sum(widths)
    if abs(total - page_width) > 0.005:
        adjust = page_width - total
        widths = list(widths)
        widths[body_index] = max(widths[body_index] + adjust, 3.0)
        widths = tuple(widths)

    table = docx_shapes.fixed_table(doc, widths)
    if table is None:
        _header_generic(doc, d, L, palette, profile)
        return None
    # Page-wide table pulled to the paper edge by the negative page margin.
    docx_shapes.set_cell_indent(table, -_dxa(left_margin))
    # The row at least fills the text block on short CVs (bar full height); it
    # can still split when the CV is longer than one page.
    row_height = max(page_height - top_margin - bottom_margin - 0.35, 5.0)
    docx_shapes.exact_row_height(table.rows[0], row_height, "atLeast")

    bar = table.cell(0, 3 if mirrored else 0)
    body = table.cell(0, body_index)
    gutter_cell = table.cell(
        0, (body_index + 1) if mirrored else (body_index - 1),
    )

    # --- accent bar -------------------------------------------------------
    _cell_top(bar)
    docx_shapes.shade_cell(bar, palette.role_hex("accent"))
    logo, photo = _header_images(d)
    total_width = max(page_width - left_margin - right_margin, 3.0)
    photo_width, _photo_height = _photo_box_cm(d, profile, total_width)
    if logo:
        logo_width, logo_height = _logo_box_cm(
            d, profile, min(photo_width, inner_cm),
        )
        _add_logo(
            bar, logo, min(logo_width, inner_cm), logo_height,
            WD_ALIGN_PARAGRAPH.CENTER,
        )
    if photo:
        width = _fit_width_cm(photo, min(photo_width, inner_cm), 5.0)
        _add_bar_photo(
            bar, photo, width, inner_cm, pad_cm, WD_ALIGN_PARAGRAPH.CENTER,
        )
    _drop_leading_empty(bar)
    has_images = bool(logo or photo)
    _sidebar_contacts(
        bar, d, L, size_pt=max(_normal_font_size(bar) - 3.0, 7.0),
        before_pt=6.0 if has_images else 0.0, pad_cm=pad_cm,
    )
    _shrink_empty_paragraphs(bar)

    # --- body column: name, profession, rule, then the whole CV ----------
    _shrink_empty_paragraphs(gutter_cell)

    _cell_top(body)
    usable = max(body_width - 0.2, 1.0)

    name = _text(_value(d, "name"))
    profession = _text(_value(d, "profession"))
    if name:
        paragraph = body.paragraphs[0]
        _zero_spacing(paragraph, 0, 2.0)
        try:
            paragraph.paragraph_format.line_spacing = 0.95
        except Exception:
            pass
        _write_name(
            paragraph, name, palette, profile,
            color=palette.role("accent"), max_width_cm=usable,
        )
    if profession:
        paragraph = _next_paragraph(body)
        if paragraph is not None:
            _zero_spacing(paragraph, 3.0 if name else 0.0, 0)
            run = paragraph.add_run(profession)
            run.font.size = Pt(13.0)
            run.font.small_caps = True
            run.font.color.rgb = palette.gray
            _run_font(run, _family_for(profile))
    if name or profession:
        rule = _cell_rule(
            body, palette.role_hex("accent"), 1.2, space_pt=4.0, gap_pt=6.0,
        )
        return body
    _shrink_empty_paragraphs(body)
    return body


def _header_tabbed(doc, d, L, palette, profile):
    """26pt black name on white, two contact columns, photo and heavy rules."""
    total = _text_width_cm(doc)
    logo, photo = _header_images(d)
    has_right = bool(logo or photo)
    photo_width, photo_height = _photo_box_cm(d, profile, total)
    right_width = 0.0
    if has_right:
        right_width = min(
            max(photo_width + 0.30, total * float(profile.photo_ratio)), total * 0.40,
        )
    widths = (total - right_width, right_width) if has_right else (total,)
    table = _new_header_table(doc, widths)

    left = table.cell(0, 0)
    _cell_top(left)
    _set_cell_margins(left, top=0, right=0, bottom=0, left=0)
    family = _family_for(profile)

    name = _text(_value(d, "name")) or L["title_short"]
    paragraph = left.paragraphs[0]
    _zero_spacing(paragraph, 0, 8.0)
    _write_name(
        paragraph, name, palette, profile, color=palette.role("text"),
        max_width_cm=max(widths[0] - 0.3, 1.0),
    )

    personal, objective, socials = _contact_groups(d, L)
    left_pairs, right_pairs = _split_contacts(personal, objective, socials)
    base = _normal_font_size(left)
    contact_width = max(widths[0] - 0.2, 1.5)
    half = contact_width * 0.48
    every_line_fits = all(
        _estimate_width_cm(_text(pair[0]) + " " + _text(pair[1]), base - 1.0)
        <= half - 0.15
        for pair in list(left_pairs) + list(right_pairs)
    )
    if every_line_fits:
        _contact_columns(
            left, contact_width, left_pairs, right_pairs, palette, family,
            size_pt=max(base - 1.0, 7.0), gap_pt=2.0, right_color=palette.gray,
            ratio=0.48,
        )
    else:
        # A two-column grid with a wrapped line would break the vertical
        # rhythm; the PDF falls back to one stacked line per contact, and so do
        # we (the same paragraph-with-breaks block as the other templates).
        _add_contacts(left, d, L, palette, profile)

    if has_right:
        right = table.cell(0, 1)
        _cell_top(right)
        _set_cell_margins(right, top=0, right=0, bottom=0, left=0)
        if logo:
            logo_width, logo_height = _logo_box_cm(d, profile, photo_width)
            _add_logo(right, logo, logo_width, logo_height, WD_ALIGN_PARAGRAPH.RIGHT)
        if photo:
            _add_framed_photo(
                right, photo, photo_width, photo_height, palette,
                WD_ALIGN_PARAGRAPH.RIGHT,
            )

    _header_rule(doc, palette.accent_hex, 2.2, 1, gap_before_pt=7.0)
    _header_rule(doc, palette.secondary_hex, 0.6, 0)


def _header_ribbon(doc, d, L, palette, profile):
    """Blue band with the name and the photo inside it, gold rule, contacts."""
    total = _text_width_cm(doc)
    logo, photo = _header_images(d)
    table = _new_header_table(doc, (total,))
    cell = table.cell(0, 0)
    _cell_top(cell)
    _set_cell_margins(cell, top=0, right=0, bottom=0, left=0)

    _ribbon_wing(cell, total, palette)
    _drop_leading_empty(cell)

    name = _text(_value(d, "name")) or L["title_short"]
    name_pt = _clamp_number(profile.name_pt, 24.0, 10.0, 40.0)
    pad_cm = _em_cm(0.45, name_pt)
    photo_width, photo_height = _photo_box_cm(d, profile, total)
    right_width = max(min(photo_width + 0.30, total * 0.40), total * 0.26)
    left_width = max(total - right_width, 1.0)
    band_color = palette.role_hex("accent")
    band = docx_shapes.fixed_table(cell, (left_width, right_width))
    if band is not None:
        name_cell = band.cell(0, 0)
        photo_cell = band.cell(0, 1)
        for band_cell in (name_cell, photo_cell):
            docx_shapes.shade_cell(band_cell, band_color)
        _set_cell_margins(name_cell, top=60, right=80, bottom=60, left=_dxa(pad_cm))
        _set_cell_margins(photo_cell, top=60, right=80, bottom=60, left=40)
        docx_shapes.exact_row_height(band.rows[0], 1.2, "atLeast")
        for band_cell in (name_cell, photo_cell):
            try:
                band_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            except Exception:
                pass
        paragraph = name_cell.paragraphs[0]
        _zero_spacing(paragraph)
        _write_name(
            paragraph, name, palette, profile, color=palette.role("white"),
            base_pt=name_pt,
            max_width_cm=max(left_width - pad_cm - 0.2, 1.0),
        )
        if logo:
            logo_width, logo_height = _logo_box_cm(d, profile, photo_width)
            _add_logo(photo_cell, logo, logo_width, logo_height, WD_ALIGN_PARAGRAPH.RIGHT)
        if photo:
            _add_plain_picture(
                photo_cell, photo, photo_width, WD_ALIGN_PARAGRAPH.RIGHT,
            )
    else:
        paragraph = cell.paragraphs[0]
        _zero_spacing(paragraph)
        docx_shapes.shade_paragraph(paragraph, band_color)
        docx_shapes.set_exact_line_height(paragraph, 40.0)
        _write_name(
            paragraph, name, palette, profile, color=palette.role("white"),
            base_pt=name_pt, max_width_cm=max(total - pad_cm - 0.3, 1.0),
        )

    _cell_rule(cell, palette.role_hex("accent2"), 2.4, 1, gap_pt=3.0)
    _add_contacts(cell, d, L, palette, profile, before_pt=6.0)


def _blade_tip(cell, width_cm, height_cm, color_hex, steps=12):
    """Stair-stepped right end of the sword banner (``\\cvblade``).

    Twelve navy bars, each ``1/steps`` of the banner height, shrink from the
    full tip width to ``1/steps`` of it: the right end reads as one slanted
    blade instead of a square rectangle. Bars use paragraph shading because a
    table cell cannot change width from row to row.
    """
    steps = int(_clamp_number(steps, 12, 6, 24))
    width = max(_number(width_cm, 1.4), 0.3)
    height = max(_number(height_cm, 1.3), 0.3)
    row_pt = height * (72.0 / 2.54) / steps
    for index in range(steps):
        try:
            paragraph = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
        except Exception:
            return cell
        _zero_spacing(paragraph)
        bar_width = max(width * (steps - index) / float(steps), width / float(steps))
        try:
            paragraph.paragraph_format.left_indent = Cm(0)
            paragraph.paragraph_format.right_indent = Cm(max(width - bar_width, 0.0))
        except Exception:
            pass
        docx_shapes.shade_paragraph(paragraph, color_hex)
        docx_shapes.set_exact_line_height(paragraph, row_pt)
        docx_shapes.set_paragraph_mark_size(paragraph, row_pt)
    return cell


def _header_sword(doc, d, L, palette, profile):
    """Navy banner with a stair-stepped blade tip, contacts under it."""
    total = _text_width_cm(doc)
    logo, photo = _header_images(d)
    has_right = bool(logo or photo)
    photo_width, photo_height = _photo_box_cm(d, profile, total)
    right_width = 0.0
    if has_right:
        right_width = min(
            max(photo_width + 0.30, total * float(profile.photo_ratio)), total * 0.40,
        )
    widths = (total - right_width, right_width) if has_right else (total,)
    table = _new_header_table(doc, widths)

    left = table.cell(0, 0)
    _cell_top(left)
    _set_cell_margins(left, top=0, right=0, bottom=0, left=0)
    family = _family_for(profile)

    name = _text(_value(d, "name")) or L["title_short"]
    name_pt = _clamp_number(profile.name_pt, 20.0, 10.0, 36.0)
    pad_cm = _em_cm(0.45, name_pt)
    extra = max(_number(profile.band_extra_cm, 1.4), 0.6)
    body_ratio = _number(profile.band_width_ratio, 0.64) or 0.64
    banner_body = max(
        min(total * body_ratio, widths[0] - extra - 0.1), 2.0,
    )
    banner_height = max(
        docx_shapes.pt_to_cm(_number(profile.band_height_pt, 36.85)), 0.8,
    )
    navy = palette.role_hex("accent")
    banner = docx_shapes.fixed_table(left, (banner_body, extra))
    if banner is not None:
        body_cell = banner.cell(0, 0)
        tip_cell = banner.cell(0, 1)
        docx_shapes.shade_cell(body_cell, navy)
        _set_cell_margins(body_cell, top=0, right=40, bottom=0, left=_dxa(pad_cm))
        _set_cell_margins(tip_cell, top=0, right=0, bottom=0, left=0)
        docx_shapes.exact_row_height(banner.rows[0], banner_height, "atLeast")
        try:
            body_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        except Exception:
            pass
        paragraph = body_cell.paragraphs[0]
        _zero_spacing(paragraph)
        _write_name(
            paragraph, name, palette, profile, color=palette.role("white"),
            base_pt=name_pt,
            max_width_cm=max(banner_body - pad_cm - 0.2, 1.0),
        )
        _blade_tip(tip_cell, extra, banner_height, navy)
        _drop_leading_empty(left)
    else:
        paragraph = left.paragraphs[0]
        _zero_spacing(paragraph)
        docx_shapes.shade_paragraph(paragraph, navy)
        docx_shapes.set_exact_line_height(paragraph, 37.0)
        try:
            paragraph.paragraph_format.left_indent = Cm(pad_cm)
        except Exception:
            pass
        _write_name(
            paragraph, name, palette, profile, color=palette.role("white"),
            base_pt=name_pt, max_width_cm=max(widths[0] - pad_cm - 0.3, 1.0),
        )

    personal, objective, socials = _contact_groups(d, L)
    left_pairs, right_pairs = _split_contacts(personal, objective, socials)
    base = _normal_font_size(left)
    if left_pairs or right_pairs:
        grid = _contact_columns(
            left, min(banner_body + extra, widths[0]), left_pairs, right_pairs,
            palette, family, size_pt=max(base - 1.0, 7.0), gap_pt=2.0,
            ratio=0.47,
        )
        if grid is not None:
            try:
                grid.rows[0].cells[0].paragraphs[0].paragraph_format.space_before = Pt(5.0)
            except Exception:
                pass

    if has_right:
        right = table.cell(0, 1)
        _cell_top(right)
        _set_cell_margins(right, top=0, right=0, bottom=0, left=0)
        if logo:
            logo_width, logo_height = _logo_box_cm(d, profile, photo_width)
            _add_logo(right, logo, logo_width, logo_height, WD_ALIGN_PARAGRAPH.RIGHT)
        if photo:
            _add_framed_photo(
                right, photo, photo_width, photo_height, palette,
                WD_ALIGN_PARAGRAPH.RIGHT,
            )

    _header_rule(doc, palette.role_hex("accent"), 0.7, 1, gap_before_pt=5.0)


def _header_navy(doc, d, L, palette, profile):
    """24pt accent name, contacts and a two-tone hairline double rule."""
    total = _text_width_cm(doc)
    logo, photo = _header_images(d)
    has_right = bool(logo or photo)
    photo_width, photo_height = _photo_box_cm(d, profile, total)
    right_width = 0.0
    if has_right:
        right_width = min(
            max(photo_width + 0.30, total * float(profile.photo_ratio)), total * 0.40,
        )
    widths = (total - right_width, right_width) if has_right else (total,)
    table = _new_header_table(doc, widths)

    left = table.cell(0, 0)
    _cell_top(left)
    _set_cell_margins(left, top=0, right=0, bottom=0, left=0)

    name = _text(_value(d, "name")) or L["title_short"]
    paragraph = left.paragraphs[0]
    _zero_spacing(paragraph, 0, 4.0)
    _write_name(
        paragraph, name, palette, profile, color=palette.role("accent"),
        max_width_cm=max(widths[0] - 0.3, 1.0),
    )
    _add_contacts(left, d, L, palette, profile, before_pt=3.0)

    if has_right:
        right = table.cell(0, 1)
        _cell_top(right)
        _set_cell_margins(right, top=0, right=0, bottom=0, left=0)
        if logo:
            logo_width, logo_height = _logo_box_cm(d, profile, photo_width)
            _add_logo(right, logo, logo_width, logo_height, WD_ALIGN_PARAGRAPH.RIGHT)
        if photo:
            _add_framed_photo(
                right, photo, photo_width, photo_height, palette,
                WD_ALIGN_PARAGRAPH.RIGHT,
            )

    _header_rule(doc, palette.role_hex("accent"), 0.6, 1, gap_before_pt=5.0)
    _header_rule(doc, palette.role_hex("accent2"), 0.3, 0)


def _header_playful(doc, d, L, palette, profile):
    """26pt purple name, badge contacts and a purple/coral double rule."""
    total = _text_width_cm(doc)
    logo, photo = _header_images(d)
    has_right = bool(logo or photo)
    photo_width, photo_height = _photo_box_cm(d, profile, total)
    right_width = 0.0
    if has_right:
        right_width = min(
            max(photo_width + 0.30, total * float(profile.photo_ratio)), total * 0.40,
        )
    widths = (total - right_width, right_width) if has_right else (total,)
    table = _new_header_table(doc, widths)

    left = table.cell(0, 0)
    _cell_top(left)
    _set_cell_margins(left, top=0, right=0, bottom=0, left=0)
    family = _family_for(profile)

    name = _text(_value(d, "name")) or L["title_short"]
    paragraph = left.paragraphs[0]
    _zero_spacing(paragraph, 0, 8.0)
    _write_name(
        paragraph, name, palette, profile, color=palette.role("accent"),
        max_width_cm=max(widths[0] - 0.3, 1.0),
    )

    personal, objective, socials = _contact_groups(d, L)
    pairs = list(personal) + list(objective) + list(socials)
    base = _normal_font_size(left)
    _badge_contacts(
        left, pairs, palette, family, max(widths[0] - 0.2, 1.5),
        size_pt=max(base - 0.5, 7.0),
    )

    if has_right:
        right = table.cell(0, 1)
        _cell_top(right)
        _set_cell_margins(right, top=0, right=0, bottom=0, left=0)
        if logo:
            logo_width, logo_height = _logo_box_cm(d, profile, photo_width)
            _add_logo(right, logo, logo_width, logo_height, WD_ALIGN_PARAGRAPH.RIGHT)
        if photo:
            _add_framed_photo(
                right, photo, photo_width, photo_height, palette,
                WD_ALIGN_PARAGRAPH.RIGHT,
            )

    _header_rule(doc, palette.role_hex("accent"), 1.2, 1, gap_before_pt=7.0)
    _header_rule(doc, palette.role_hex("accent2"), 0.5, 0)


def _header_generic(doc, d, L, palette, profile):
    """Temporary generic header for the templates not covered by t3.

    It keeps the old nameplate behaviour (band cell when the profile says so,
    logo/photo column, contacts after the table) while using the profile name
    role/size and the new image framing. Later header subtasks replace it.
    """
    name = _text(_value(d, "name")) or L["title_short"]
    logo, photo = _header_images(d)
    has_right = bool(logo or photo)
    total = _text_width_cm(doc)

    table = _new_header_table(
        doc,
        (total * 0.68, total * 0.32) if has_right else (total,),
    )
    left = table.cell(0, 0)
    try:
        left.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    except Exception:
        pass
    _set_cell_margins(
        left, top=40, right=160 if profile.band else 40, bottom=40,
        left=160 if profile.band else 40,
    )
    band = bool(profile.band)
    if band:
        _shade_cell(left, palette.role_hex(profile.band_role or "accent"))

    name_paragraph = left.paragraphs[0]
    _zero_spacing(name_paragraph, 2, 1)
    color = palette.contrast if band else palette.role(profile.name_role)
    _write_name(
        name_paragraph, name, palette, profile, color=color,
        max_width_cm=max((total * 0.68 if has_right else total) - 0.5, 1.0),
    )
    if not band:
        _bottom_border(name_paragraph, palette.accent_hex, thickness=18, space=4)

    if has_right:
        right = table.cell(0, 1)
        try:
            right.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        except Exception:
            pass
        _set_cell_margins(right, top=40, right=40, bottom=40, left=40)
        photo_width, photo_height = _photo_box_cm(d, profile, total)
        if logo:
            logo_width, logo_height = _logo_box_cm(d, profile, photo_width)
            _add_logo(
                right, logo, logo_width, logo_height, WD_ALIGN_PARAGRAPH.RIGHT,
            )
        if photo:
            _add_framed_photo(
                right, photo, photo_width, photo_height, palette,
                WD_ALIGN_PARAGRAPH.RIGHT,
            )

    _add_contacts(doc, d, L, palette, profile)


#: Per-template header builders. Later header subtasks add their template
#: here; everything else falls back to ``_header_generic``.
_HEADER_BUILDERS = {
    "classic": _header_classic,
    "harvard": _header_harvard,
    "modern": _header_modern,
    "creative": _header_creative,
    "chinese": _header_chinese,
    "sidebar": _header_sidebar,
    "sidebar-right": _header_sidebar,
    "tabbed": _header_tabbed,
    "ribbon": _header_ribbon,
    "sword": _header_sword,
    "navy": _header_navy,
    "playful": _header_playful,
}


def _apply_page_frame(doc, palette, profile):
    """Page border of the templates that frame every page (tabbed).

    The frame lives in ``sectPr`` (``w:pgBorders``) so Word and LibreOffice
    repeat it on every page. ``offsetFrom="page"`` measures the inset from the
    paper edge: the profile's 0.62cm when the margins leave room, otherwise
    half of the narrowest margin so the frame never touches the text block.
    """
    if not bool(getattr(profile, "page_frame", False)):
        return None
    spec = tuple(getattr(profile, "page_frame_role_size", ()) or ())
    role = spec[0] if len(spec) > 0 else "text"
    size = _number(spec[1], 1.8) if len(spec) > 1 else 1.8
    inset = _number(spec[2], 0.62) if len(spec) > 2 else 0.62
    try:
        section = doc.sections[0]
    except Exception:
        return None
    margins = []
    for name in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        try:
            margins.append(float(getattr(section, name).cm))
        except Exception:
            continue
    narrowest = min(margins) if margins else DEFAULT_MARGIN
    offset = inset if narrowest >= 2.0 * inset else max(narrowest / 2.0, 0.2)
    return docx_shapes.page_frame(section, palette.role_hex(role), size, offset)


def _add_header(doc, d, L, palette, profile=None):
    """Borderless header table dispatcher (document.tables[0]).

    Returns the body container of templates that draw the whole CV inside the
    header table (the sidebar family); every other builder returns ``None`` and
    the body is appended to the document as usual.
    """
    profile = _profile_or_default(profile)
    _apply_page_frame(doc, palette, profile)
    builder = _HEADER_BUILDERS.get(profile.template)
    if builder is None:
        _header_generic(doc, d, L, palette, profile)
        return None
    return builder(doc, d, L, palette, profile)



# ---------------------------------------------------------------------------
# Sections and body
# ---------------------------------------------------------------------------

def _mm_to_pt(mm):
    """Millimetres -> points (heading plate heights)."""
    return max(_number(mm, 0.0), 0.0) * 72.0 / 25.4


def _em_pt(em, pt):
    """``em`` ems of ``pt`` points, in points."""
    return max(_number(em, 0.0) * _clamp_number(pt, DEFAULT_FONT_SIZE, 1.0, 200.0), 0.0)


def _estimate_width_cm(text, pt, bold=False):
    """Approximate rendered width of ``text`` at ``pt`` points.

    ``docx_shapes.text_width_cm`` averages 0.5em per Latin character, which
    over-estimates mixed lower-case prose by ~30% and would make the entry
    lines wrap needlessly. This local estimator classifies narrow, wide, upper
    case, digit, punctuation, space and CJK characters separately; it is used
    only for fit decisions (tab layout vs stacked lines), never to lay out.
    """
    value = _text(text)
    if not value:
        return 0.0
    size = _clamp_number(pt, DEFAULT_FONT_SIZE, 1.0, 200.0)
    units = 0.0
    for char in value:
        code = ord(char)
        if code >= 0x2E80:
            units += 1.0
        elif char == " ":
            units += 0.25
        elif char in "iljtfrI.,:;'!|()[]-":
            units += 0.28
        elif char in "mwMW@&#%":
            units += 0.85
        elif char.isdigit():
            units += 0.5
        elif char.isupper():
            units += 0.62
        else:
            units += 0.45
    factor = 1.03 if bold else 1.0
    return units * size * factor / docx_shapes.PT_PER_CM


def _container_width_cm(container, override=None):
    """Usable width of a Document or a table cell, in centimetres.

    ``override`` wins when the caller already knows the measure (the column
    cells of a section table). A cell subtracts its own left/right padding, so
    a right tab stop lands on the cell edge instead of the page margin.
    """
    if override is not None:
        return max(_number(override, docx_shapes.DEFAULT_TEXT_WIDTH_CM), 1.0)
    try:
        if hasattr(container, "sections"):
            return _text_width_cm(container)
    except Exception:
        pass
    try:
        tc_pr = container._tc.tcPr
        width = None
        if tc_pr is not None:
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is not None and tc_w.get(qn("w:type")) == "dxa":
                width = _number(tc_w.get(qn("w:w")), 0) * 2.54 / 1440.0
        if width is None:
            width = float(container.width.cm)
        padding = 0.0
        if tc_pr is not None:
            mar = tc_pr.find(qn("w:tcMar"))
            if mar is not None:
                for tag in ("left", "right"):
                    node = mar.find(qn("w:" + tag))
                    if node is not None:
                        padding += _number(node.get(qn("w:w")), 0) * 2.54 / 1440.0
        return max(width - padding, 1.0)
    except Exception:
        return docx_shapes.DEFAULT_TEXT_WIDTH_CM


def _cell_padding(cell, top=0.0, right=0.0, bottom=0.0, left=0.0):
    """Per-cell padding in centimetres, replacing any previous ``w:tcMar``."""
    try:
        tc_pr = cell._tc.get_or_add_tcPr()
    except Exception:
        return None
    mar = tc_pr.find(qn("w:tcMar"))
    if mar is None:
        mar = OxmlElement("w:tcMar")
        _insert_ordered(tc_pr, mar, _TC_MAR_SUCCESSORS)
    for tag, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        node = mar.find(qn("w:" + tag))
        if node is None:
            node = OxmlElement("w:" + tag)
            mar.append(node)
        node.set(qn("w:w"), str(_dxa(value)))
        node.set(qn("w:type"), "dxa")
    return mar


def _heading_gap(doc, pt):
    """Tiny empty paragraph that carries the gap around a table-based heading."""
    height = max(_number(pt, 0.0), 0.4)
    paragraph = doc.add_paragraph()
    _zero_spacing(paragraph)
    docx_shapes.set_exact_line_height(paragraph, height)
    docx_shapes.set_paragraph_mark_size(paragraph, min(height, 2.0))
    try:
        paragraph.paragraph_format.keep_with_next = True
    except Exception:
        pass
    return paragraph


def _keep_table_with_next(table):
    """Keep a heading table on the same page as the block that follows it.

    Word stores keep-with-next per paragraph; in a table the paragraphs of the
    last row decide whether the row travels with the next paragraph, which is
    how a plate/tab/bar heading avoids being orphaned at the bottom of a page.
    """
    try:
        rows = list(table.rows)
    except Exception:
        return
    for row in rows:
        try:
            cells = list(row.cells)
        except Exception:
            continue
        for cell in cells:
            for paragraph in cell.paragraphs:
                try:
                    paragraph.paragraph_format.keep_with_next = True
                except Exception:
                    pass


def _heading_title(paragraph, title, palette, profile, role="accent", pt=None,
                   color=None):
    """Bold template title run of a section heading (never raises)."""
    if paragraph is None:
        return None
    try:
        run = paragraph.add_run(_text(title))
        run.bold = True
        size = _clamp_number(
            pt if pt is not None else profile.heading_title_pt, 13.0, 4.0, 60.0,
        )
        run.font.size = Pt(size)
        if color is not None:
            run.font.color.rgb = color
        elif palette is not None:
            run.font.color.rgb = palette.role(role)
        _run_font(run, _family_for(profile))
        return run
    except Exception:
        return None


def _heading_rules(paragraph, specs, palette, space_pt=2):
    """Bottom rule(s) of a heading paragraph; returns the ``w:pBdr`` element."""
    if paragraph is None:
        return None
    spec = specs[0]
    role, size = spec[0], _clamp_number(spec[1], 0.7, 0.25, 12.0)
    color = palette.role_hex(role) if palette is not None else COLOR_ACCENT
    return docx_shapes.set_rule(paragraph, "bottom", color, size, space_pt)


def _heading_stacked_rule(doc, spec, palette, before_pt=0.5, after_pt=LATIN_HEADING_AFTER_PT):
    """Second (and last) rule of a two-tone heading, on its own tiny paragraph.

    Word stores a single border per paragraph edge, so the creative and
    playful two-colour double rules stack two paragraphs: the title carries the
    thin first colour and this paragraph the thick second one.
    """
    paragraph = doc.add_paragraph()
    _zero_spacing(paragraph, before_pt, after_pt)
    docx_shapes.set_exact_line_height(paragraph, 2.6)
    docx_shapes.set_paragraph_mark_size(paragraph, 2.6)
    try:
        paragraph.paragraph_format.keep_with_next = True
    except Exception:
        pass
    role, size = spec[0], _clamp_number(spec[1], 1.0, 0.25, 12.0)
    color = palette.role_hex(role) if palette is not None else COLOR_ACCENT
    docx_shapes.set_rule(paragraph, "bottom", color, size, 0)
    return paragraph


def _heading_rule(doc, title, palette, profile):
    """Latin heading: coloured bold title over its profile rule(s).

    ``classic``/``sidebar*``: accent title over a 0.7pt accent rule;
    ``harvard``: accent title over a 0.4pt gray hairline; ``modern``: accent
    title over a 1.6pt accent rule; ``creative``: accent title over the teal
    0.9pt + yellow 1.8pt stacked double rule. No shaded plate: the title is a
    body paragraph, exactly like ``\\cvsection`` in the LaTeX templates.
    """
    paragraph = doc.add_paragraph()
    _zero_spacing(paragraph, LATIN_HEADING_BEFORE_PT, 0.0)
    try:
        paragraph.paragraph_format.keep_with_next = True
    except Exception:
        pass
    _heading_title(paragraph, title, palette, profile, role="accent")
    specs = [tuple(spec) for spec in (profile.heading_rule_specs or ()) if len(spec) >= 2]
    if not specs:
        specs = [("accent", 0.7)]
    _heading_rules(paragraph, specs, palette)
    if len(specs) > 1:
        paragraph.paragraph_format.space_after = Pt(1.0)
        _heading_stacked_rule(doc, specs[1], palette)
    else:
        paragraph.paragraph_format.space_after = Pt(LATIN_HEADING_AFTER_PT)
    return paragraph


def _heading_plate_tail(doc, title, palette, profile):
    """``chinese``: accent plate sized to the title plus a gray tail bar.

    ``docx_shapes.plate_with_tail`` builds the 1x2 fixed table (plate + tail)
    and falls back to a full-width plate for a title that leaves no room for
    the tail, so a 45+ character heading still wraps inside the text block.
    """
    total = _text_width_cm(doc)
    title_pt = _clamp_number(profile.heading_title_pt, 17.0, 6.0, 48.0)
    height_pt = _mm_to_pt(profile.heading_plate_mm) or 21.26
    # Keep the plate + light-gray tail design even for a long title: step the
    # title size down until it fits one line and still leaves a visible tail.
    # A 78-character title used to wrap inside a full-width plate and lose the
    # tail (and, in the PDF, clip); only a title that is still too wide at the
    # floor falls back to the full-width plate, where the tail is hidden and
    # the text wraps without clipping.
    tail_min = 0.7
    floor_pt = 8.5
    while title_pt > floor_pt:
        pad = _em_cm(0.65, title_pt)
        need = docx_shapes.text_width_cm(title, title_pt, bold=True) + 2.0 * pad
        if need <= total - tail_min:
            break
        title_pt = round(title_pt - 0.5, 1)
    # plate_with_tail reserves 1.2em of padding before it declares a title too
    # long for the tail, so the plate is sized with that slack (the LaTeX
    # colorbox pads 0.35em on each side inside the same 0.9em box).
    pad = _em_cm(0.65, title_pt)
    plate = docx_shapes.text_width_cm(title, title_pt, bold=True) + 2.0 * pad
    # The LaTeX template paints the tail with ``gris`` (#C4C8D4), the light bar
    # gray; ``accent2`` does not exist in that palette and would fall back to
    # the accent, drawing one solid blue bar instead of plate + tail.
    tail = palette.role_hex("gris") if palette is not None else COLOR_GRAY
    table = docx_shapes.plate_with_tail(
        doc, plate, height_pt,
        palette.role_hex("accent") if palette is not None else COLOR_ACCENT,
        title, "FFFFFF", title_pt,
        tail,
        total,
    )
    return _plate_finish(table, pad, profile)


def _plate_finish(table, pad_cm, profile):
    """Inner padding + explicit fonts of a plate table created by docx_shapes."""
    if table is None or not getattr(table, "rows", None):
        return table
    try:
        cells = list(table.rows[0].cells)
    except Exception:
        return table
    for index, cell in enumerate(cells):
        _cell_padding(cell, top=0, right=pad_cm if index == 0 else 0, bottom=0,
                      left=pad_cm if index == 0 else 0)
        try:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        except Exception:
            pass
        for paragraph in cell.paragraphs:
            _zero_spacing(paragraph)
            for run in paragraph.runs:
                _run_font(run, _family_for(profile))
    return table


def _heading_tab(doc, title, palette, profile):
    """``tabbed``: black tab sized to the title + dark-gray rule to the margin.

    The rule leaves the tab at its vertical middle: the trailing cell keeps a
    1pt paragraph with a 0.8pt bottom border, vertically centered inside the
    7.2mm tab row. A title too wide for the tab falls back to a full-width
    black plate with the rule underneath.
    """
    total = _text_width_cm(doc)
    title_pt = _clamp_number(profile.heading_title_pt, 13.0, 6.0, 48.0)
    height_pt = _mm_to_pt(profile.heading_plate_mm) or 20.41
    pad = _em_cm(0.58, title_pt)
    gap = _em_cm(0.35, title_pt)
    tab = docx_shapes.text_width_cm(title, title_pt, bold=True) + 2.0 * pad
    rest = total - tab - gap
    black = palette.role_hex("accent") if palette is not None else "000000"
    dark = palette.role_hex("accent2") if palette is not None else "3C3C3C"
    if rest < max(_em_cm(1.2, title_pt), 0.6) or tab >= total - 0.3:
        table = docx_shapes.plate_with_tail(
            doc, total, height_pt, black, title, "FFFFFF", title_pt, black, total,
        )
        _plate_finish(table, pad, profile)
        # Role name, not a hex: _heading_stacked_rule resolves roles through the
        # palette, and a hex would fall back to the accent.
        _heading_stacked_rule(doc, ("accent2", 0.8), palette, before_pt=0.6)
        return table
    table = docx_shapes.fixed_table(doc, (tab, gap, total - tab - gap))
    if table is None:
        return _heading_rule(doc, title, palette, profile)
    docx_shapes.exact_row_height(table.rows[0], docx_shapes.pt_to_cm(height_pt))
    tab_cell, rest_cell = table.cell(0, 0), table.cell(0, 2)
    docx_shapes.shade_cell(tab_cell, black)
    _cell_padding(tab_cell, left=pad, right=pad)
    for cell in (tab_cell, rest_cell):
        try:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        except Exception:
            pass
    paragraph = tab_cell.paragraphs[0]
    _zero_spacing(paragraph)
    _heading_title(paragraph, title, palette, profile, pt=title_pt,
                   color=RGBColor(0xFF, 0xFF, 0xFF))
    rule = rest_cell.paragraphs[0]
    _zero_spacing(rule)
    docx_shapes.set_exact_line_height(rule, 1.0)
    docx_shapes.set_paragraph_mark_size(rule, 1.0)
    docx_shapes.set_rule(rule, "bottom", dark, 0.8, 0)
    _cell_padding(rest_cell)
    return table


def _heading_bar_tick(doc, title, palette, profile):
    """``ribbon``: full-width accent bar, white title, gold tick and gold rule.

    The gold tick is the left paragraph border of the title line (1.8pt wide,
    as tall as the 0.92em line) and sits 0.5em in from the bar edge; the 1.2pt
    gold rule runs under the bar.
    """
    total = _text_width_cm(doc)
    title_pt = _clamp_number(profile.heading_title_pt, 13.0, 6.0, 48.0)
    height_pt = _em_pt(0.34, title_pt) + title_pt * 1.2
    accent = palette.role_hex("accent") if palette is not None else COLOR_ACCENT
    gold = palette.role_hex("accent2") if palette is not None else COLOR_ACCENT
    table = docx_shapes.fixed_table(doc, (total,))
    if table is None:
        return _heading_rule(doc, title, palette, profile)
    cell = table.cell(0, 0)
    docx_shapes.shade_cell(cell, accent)
    _cell_padding(cell)
    docx_shapes.exact_row_height(table.rows[0], docx_shapes.pt_to_cm(height_pt), "atLeast")
    try:
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    except Exception:
        pass
    paragraph = cell.paragraphs[0]
    _zero_spacing(paragraph)
    side = _em_cm(0.5, title_pt)
    _paragraph_indents(paragraph, side, side)
    tick_pt = max(title_pt * 1.04, 10.0)
    docx_shapes.set_exact_line_height(paragraph, tick_pt)
    docx_shapes.set_paragraph_mark_size(paragraph, tick_pt)
    docx_shapes.set_rule(paragraph, "left", gold, _em_pt(0.14, title_pt), 3)
    _heading_title(paragraph, title, palette, profile, pt=title_pt,
                   color=RGBColor(0xFF, 0xFF, 0xFF))
    _heading_stacked_rule(doc, ("accent2", 1.2), palette, before_pt=0.6)
    return table


def _heading_double_rule(doc, title, palette, profile):
    """``navy`` (and any rule template): title over two stacked hairlines."""
    paragraph = doc.add_paragraph()
    _zero_spacing(paragraph, CN_HEADING_BEFORE_PT, 0.5)
    try:
        paragraph.paragraph_format.keep_with_next = True
    except Exception:
        pass
    _heading_title(paragraph, title, palette, profile, role="accent")
    specs = [tuple(spec) for spec in (profile.heading_rule_specs or ()) if len(spec) >= 2]
    if not specs:
        specs = [("accent", 0.6), ("accent2", 0.3)]
    _heading_rules(paragraph, specs, palette, space_pt=1)
    for index, spec in enumerate(specs[1:]):
        last = index == len(specs[1:]) - 1
        _heading_stacked_rule(
            doc, spec, palette, before_pt=0.6,
            after_pt=CN_HEADING_AFTER_PT if last else 0.4,
        )
    return paragraph


def _heading_badge(doc, title, palette, profile):
    """``playful``: round accent badge + coral diamond, hanging title, two rules."""
    title_pt = _clamp_number(profile.heading_title_pt, 13.5, 6.0, 48.0)
    indent = _em_cm(1.8, title_pt)
    paragraph = doc.add_paragraph()
    _zero_spacing(paragraph, CN_HEADING_BEFORE_PT, 1.0)
    try:
        fmt = paragraph.paragraph_format
        fmt.left_indent = Cm(indent)
        fmt.first_line_indent = Cm(-indent)
        fmt.keep_with_next = True
    except Exception:
        pass
    # One round badge before the title, as in the PDF. The old coral diamond is
    # gone: the section marker reads as a circle, not as a diamond on a bar.
    try:
        run = paragraph.add_run("\u25cf ")
        run.font.size = Pt(max(title_pt * 1.05, 4.0))
        run.font.color.rgb = palette.role("accent") if palette is not None else _to_rgb("#" + COLOR_ACCENT)
        _run_font(run, _family_for(profile))
    except Exception:
        pass
    _heading_title(paragraph, title, palette, profile, role="accent", pt=title_pt)
    specs = [tuple(spec) for spec in (profile.heading_rule_specs or ()) if len(spec) >= 2]
    if not specs:
        specs = [("accent", 1.2), ("accent2", 0.5)]
    _heading_rules(paragraph, specs, palette, space_pt=2)
    if len(specs) > 1:
        _heading_stacked_rule(doc, specs[1], palette, before_pt=0.6,
                              after_pt=CN_HEADING_AFTER_PT)
    return paragraph


def _blade_steps(cell, width_cm, height_pt, color_hex, steps=12):
    """Stair blade of ``sword``: ``steps`` shaded rows shrinking from the left.

    Each row is ``height_pt / steps`` tall and one ``width_cm / steps``
    narrower than the row above, all anchored on the plate edge. Written with
    literal indents (no ``shaded_bar`` clamping) so the last step stays a
    hairline instead of collapsing to the 0.05cm floor.
    """
    if cell is None:
        return []
    steps = int(_clamp_number(steps, 12, 6, 32))
    width = max(_number(width_cm, 0.22), 0.02)
    row_pt = max(_number(height_pt, 20.41), 1.0) / steps
    paragraphs = []
    for index in range(steps):
        try:
            paragraph = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
        except Exception:
            break
        _zero_spacing(paragraph)
        _paragraph_indents(
            paragraph, 0.0, width * index / float(steps),
        )
        docx_shapes.shade_paragraph(paragraph, color_hex)
        docx_shapes.set_exact_line_height(paragraph, row_pt)
        docx_shapes.set_paragraph_mark_size(paragraph, 1.0)
        paragraphs.append(paragraph)
    return paragraphs


def _heading_stair_blade(doc, title, palette, profile):
    """``sword``: gray bar + accent plate sized to the title + stair blade tip.

    The heading is a 1x3 fixed table: the accent plate, the 0.22cm blade tip
    (twelve shaded rows that shrink from the plate edge, so the cut reads as a
    slanted blade) and the gray bar that fills the rest of the line. A title
    too wide for the blade falls back to a full-width accent plate.
    """
    total = _text_width_cm(doc)
    title_pt = _clamp_number(profile.heading_title_pt, 13.0, 6.0, 48.0)
    height_pt = _mm_to_pt(profile.heading_plate_mm) or 20.41
    pad = _em_cm(0.6, title_pt)
    tip = max(docx_shapes.pt_to_cm(_em_pt(0.6, title_pt)), 0.22)
    plate = docx_shapes.text_width_cm(title, title_pt, bold=True) + 2.0 * pad
    accent = palette.role_hex("accent") if palette is not None else COLOR_ACCENT
    bar = palette.role_hex("accent2") if palette is not None else COLOR_ACCENT
    if plate + tip >= total - max(_em_cm(0.6, title_pt), 0.3):
        table = docx_shapes.plate_with_tail(
            doc, total, height_pt, accent, title, "FFFFFF", title_pt, bar, total,
        )
        return _plate_finish(table, pad, profile)
    rest = max(total - plate - tip, 0.3)
    table = docx_shapes.fixed_table(doc, (plate, tip, rest))
    if table is None:
        return _heading_rule(doc, title, palette, profile)
    docx_shapes.exact_row_height(table.rows[0], docx_shapes.pt_to_cm(height_pt))
    plate_cell, tip_cell, bar_cell = table.cell(0, 0), table.cell(0, 1), table.cell(0, 2)
    docx_shapes.shade_cell(plate_cell, accent)
    docx_shapes.shade_cell(tip_cell, bar)
    docx_shapes.shade_cell(bar_cell, bar)
    _cell_padding(plate_cell, left=pad, right=pad)
    _cell_padding(tip_cell)
    _cell_padding(bar_cell)
    try:
        plate_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        tip_cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
    except Exception:
        pass
    paragraph = plate_cell.paragraphs[0]
    _zero_spacing(paragraph)
    _heading_title(paragraph, title, palette, profile, pt=title_pt,
                   color=RGBColor(0xFF, 0xFF, 0xFF))
    _drop_leading_empty(tip_cell)
    _blade_steps(tip_cell, tip, height_pt, accent)
    return table


#: Table-based heading builders of the Chinese-style templates.
_CN_HEADING_BUILDERS = {
    "plate_tail": _heading_plate_tail,
    "tab": _heading_tab,
    "bar_tick": _heading_bar_tick,
    "double_rule": _heading_double_rule,
    "badge": _heading_badge,
    "stair_blade": _heading_stair_blade,
}

#: Heading kinds that are a table: their row height is exact (or at least the
#: plate height), so the LaTeX \vspace around them needs real gap paragraphs.
_CN_TABLE_HEADINGS = frozenset(("plate_tail", "tab", "bar_tick", "stair_blade"))


def _add_heading(doc, title, palette=None, profile=None):
    """Section title in the selected template's heading shape.

    The Latin templates draw a coloured bold title as a body paragraph over
    the rule of their profile (0.7pt accent for classic/sidebar, 0.4pt gray for
    harvard, 1.6pt accent for modern, the teal+yellow stacked double rule for
    creative). The Chinese-style templates draw their plate, tab, bar, badge
    or stair blade; the plate-like ones need a table, so a pair of tiny gap
    paragraphs carries the LaTeX ``\\vspace`` around them while the paragraph
    shaped ones keep their own spacing. An empty title adds nothing.
    """
    profile = _profile_or_default(profile)
    title = _text(title)
    if not title:
        return None
    kind = _text(profile.heading_kind)
    try:
        builder = None
        if _text(profile.template) in CN_STYLE_TEMPLATES:
            builder = _CN_HEADING_BUILDERS.get(kind)
        if builder is None:
            return _heading_rule(doc, title, palette, profile)
        if kind in _CN_TABLE_HEADINGS:
            _heading_gap(doc, CN_HEADING_BEFORE_PT)
        result = builder(doc, title, palette, profile)
        if getattr(result, "rows", None) is not None:
            _keep_table_with_next(result)
        if kind in _CN_TABLE_HEADINGS or getattr(result, "rows", None) is not None:
            _heading_gap(doc, CN_HEADING_AFTER_PT)
        return result
    except Exception:
        try:
            return _heading_rule(doc, title, palette, profile)
        except Exception:
            return None


def _add_entry_title(container, start, end, title, palette=None, profile=None,
                     width_cm=None):
    """Latin entry line: italic date, then a right-aligned bold title.

    The date goes on the left in italic (the PDF never greys it) and the title
    is flushed right by a tab stop at the text width, which is the Word
    rendering of ``\\noindent{\\itshape date} \\hfill {\\bfseries title}``. An
    empty date leaves the title at the left margin with no stray tab, and an
    empty title keeps just the date.
    """
    profile = _profile_or_default(profile)
    date = _date_range(start, end)
    title = _text(title)
    if not date and not title:
        return None
    try:
        paragraph = container.add_paragraph()
    except Exception:
        return None
    _zero_spacing(paragraph, 0.0, 0.5)
    try:
        paragraph.paragraph_format.keep_with_next = True
    except Exception:
        pass
    base = _normal_font_size(container)
    width = _container_width_cm(container, width_cm)
    fits = True
    if date and title:
        need = (
            _estimate_width_cm(date, base)
            + _estimate_width_cm(title, base, bold=True)
            + 0.25
        )
        # 5% safety margin: the estimate is a heuristic and the renderer may
        # substitute the font (Cambria -> Caladea), so a title that only "just"
        # fits is flushed right anyway and wraps to the left margin, leaving an
        # orphan line. Slightly longer titles get their own line instead.
        fits = need * 1.05 <= width
    try:
        if date:
            date_run = paragraph.add_run(date)
            date_run.italic = True
            date_run.font.size = Pt(base)
            _run_font(date_run, _family_for(profile))
        if title:
            if date and fits:
                _tab_stop_right(paragraph, width)
                run = paragraph.add_run("\t" + title)
            elif date:
                # No room for the \hfill: TeX breaks at the glue, so the title
                # starts on the next line at the left margin instead of gluing
                # itself to the date or bleeding past the right margin.
                run = paragraph.add_run("\n" + title)
            else:
                run = paragraph.add_run(title)
            run.bold = True
            run.font.size = Pt(base)
            _run_font(run, _family_for(profile))
    except Exception:
        pass
    return paragraph


def _tab_stop_right(paragraph, position_cm):
    """Right-aligned tab stop at ``position_cm`` (never raises)."""
    try:
        return paragraph.paragraph_format.tab_stops.add_tab_stop(
            Cm(max(_number(position_cm, docx_shapes.DEFAULT_TEXT_WIDTH_CM), 0.0)),
            WD_TAB_ALIGNMENT.RIGHT,
        )
    except Exception:
        return None


def _tab_stop(paragraph, position_cm, alignment):
    """Tab stop with an explicit alignment (never raises)."""
    try:
        return paragraph.paragraph_format.tab_stops.add_tab_stop(
            Cm(max(_number(position_cm, 0.0), 0.0)), alignment,
        )
    except Exception:
        return None


def _add_cn_entry_line(container, date, title, org, palette=None, profile=None,
                       width_cm=None):
    """Chinese-style entry line: date / title / organization on one line.

    One paragraph with three bold runs and two tab stops at the fixed column
    ratios of the profile (chinese/tabbed/ribbon/sword 0.24/0.46/0.26, navy
    0.22/0.40/0.34, playful 0.20/0.40/0.37): the date is left, the title is
    centered on its column (left for playful) and the organization is flushed
    right. Without a date the line falls back to the 0.66/0.30 title/org
    layout, so the title starts at the left margin and no tab is emitted.
    """
    profile = _profile_or_default(profile)
    date = _text(date)
    title = _text(title)
    org = _text(org)
    if not date and not title and not org:
        return None
    try:
        paragraph = container.add_paragraph()
    except Exception:
        return None
    _zero_spacing(paragraph, 0.0, CN_ENTRY_GAP_PT)
    try:
        paragraph.paragraph_format.keep_with_next = True
    except Exception:
        pass
    width = _container_width_cm(container, width_cm)
    ratios = tuple(profile.entry_columns or (0.24, 0.46, 0.26))
    ratios = tuple(_number(r, 0.0) for r in ratios)
    span = sum(ratios) or 1.0
    base = _normal_font_size(container)
    playful = _text(profile.template) == "playful"
    family = _family_for(profile)

    # LaTeX boxes each value in its own minipage (or lets \hfill shrink); Word
    # tabs do not wrap inside a column, so overlong entries degrade to stacked
    # lines instead of gluing the date to the title and bleeding into the
    # margin. The estimates are deliberately generous: the 0.45 cm slack
    # absorbs the font substitution (Cambria -> Caladea) that makes a "just
    # fits" line wrap, and a value longer than 72% of the measure is never
    # pushed with a right tab, because the tab would drop its first line into
    # the middle of the page.
    gap = 0.30
    slack = 0.45
    date_w = _estimate_width_cm(date, base, bold=True) if date else 0.0
    title_w = _estimate_width_cm(title, base, bold=True) if title else 0.0
    org_w = _estimate_width_cm(org, base, bold=True) if org else 0.0
    # The organization is the right-hand column. A right tab cannot wrap inside
    # its column: once the text is wider than the column, LibreOffice/Word put
    # the first line at the margin and drop the tail back to the page-left
    # margin (a gray orphan). Treat "wider than its own column" as a separate
    # right-aligned paragraph, even when the three fields together "fit" the
    # full measure.
    org_col = width * (ratios[2] / span) if len(ratios) >= 3 else width * 0.26
    middle_col = width * (ratios[1] / span) if len(ratios) >= 2 else width * 0.46
    org_in_column = org_w * 1.08 <= max(org_col - 0.05, 0.5)
    title_in_column = title_w * 1.12 <= max(middle_col - 0.1, 0.8)
    # The date and the title keep their own line whenever both fit their
    # columns; the organization is what moves to its own right-aligned
    # paragraph when it cannot wrap inside its column.
    fits_title = (
        date_w * 1.10 + title_w * 1.12 + gap + slack <= width
        and title_in_column
    )
    fits_all = fits_title and org_in_column
    if date and title and fits_title:
        if playful:
            _tab_stop(paragraph, width * ratios[0] / span, WD_TAB_ALIGNMENT.LEFT)
        else:
            _tab_stop(
                paragraph,
                width * (ratios[0] + ratios[1] / 2.0) / span,
                WD_TAB_ALIGNMENT.CENTER,
            )
    if org and fits_all:
        _tab_stop_right(paragraph, width)

    def write(target, text, bold=True, color=None, italic=False, size=None):
        try:
            run = target.add_run(text)
            run.bold = bool(bold)
            run.italic = bool(italic)
            run.font.size = Pt(size if size is not None else base)
            if color is not None:
                run.font.color.rgb = color
            _run_font(run, family)
            return run
        except Exception:
            return None

    date_color = palette.role("gray") if (playful and palette is not None) else (
        palette.role("accent") if palette is not None else None
    )
    org_color = palette.role("gray") if palette is not None else None
    title_color = (
        palette.role("accent") if (playful and palette is not None) else None
    )
    if date:
        write(paragraph, date, color=date_color,
              size=max(base - 1.5, 7.0) if playful else None)
    if title:
        if date and fits_title:
            prefix = "\t"
        elif date:
            prefix = "\n"
        else:
            prefix = ""
        write(paragraph, prefix + title, color=title_color)

    org_is_own_line = bool(org) and not fits_all and bool(date or title)
    if org:
        if not org_is_own_line:
            # It fits after the title on the same tabbed line (or it is the
            # only field, so no tab is emitted).
            prefix = "\t" if (date or title) and fits_all else ""
            write(paragraph, prefix + org, color=org_color,
                  size=max(base - 1.5, 7.0) if playful else None)
        else:
            # A tab-aligned run that does not fit would wrap back to the page
            # left margin as a gray orphan. Draw it on its own paragraph,
            # right-aligned and indented to the organization column, so every
            # wrapped line stays inside that column and keeps the right axis.
            org_paragraph = container.add_paragraph()
            _zero_spacing(org_paragraph, 0.0, CN_ENTRY_GAP_PT)
            try:
                org_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                left_cm = width * (ratios[0] + ratios[1]) / span
                org_paragraph.paragraph_format.left_indent = Cm(max(left_cm, 0.0))
                org_paragraph.paragraph_format.right_indent = Cm(0)
            except Exception:
                pass
            write(org_paragraph, org, color=org_color,
                  size=max(base - 1.5, 7.0) if playful else None)
    return paragraph



def _add_gray_italic(doc, text, palette):
    """Support line (organization, institution) in italic gray."""
    value = _text(text)
    if not value:
        return None
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(value)
    run.italic = True
    if palette is not None:
        run.font.color.rgb = palette.gray
    return paragraph


def _set_rpr_fonts(r_pr, family):
    """Write explicit ascii/hAnsi/eastAsia/cs fonts on an ``w:rPr`` element."""
    if r_pr is None:
        return
    r_fonts = r_pr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)
    for attribute in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        r_fonts.attrib.pop(qn(attribute), None)
    r_fonts.set(qn("w:ascii"), family)
    r_fonts.set(qn("w:hAnsi"), family)
    r_fonts.set(qn("w:eastAsia"), EAST_ASIA_FONT)
    r_fonts.set(qn("w:cs"), family)


def _set_rpr_size(r_pr, size_pt):
    """Set ``w:sz``/``w:szCs`` on an ``w:rPr`` element (half-points)."""
    if r_pr is None:
        return
    half_points = str(int(round(_clamp_number(size_pt, DEFAULT_FONT_SIZE, 1.0, 200.0) * 2)))
    for tag in ("w:sz", "w:szCs"):
        node = r_pr.find(qn(tag))
        if node is None:
            node = OxmlElement(tag)
            r_pr.append(node)
        node.set(qn("w:val"), half_points)


def _document_defaults(doc):
    """``(rPr, pPr)`` of ``w:docDefaults``, created when the template lacks them."""
    styles_element = doc.styles.element
    defaults = styles_element.find(qn("w:docDefaults"))
    if defaults is None:
        defaults = OxmlElement("w:docDefaults")
        styles_element.insert(0, defaults)

    rpr_default = defaults.find(qn("w:rPrDefault"))
    if rpr_default is None:
        rpr_default = OxmlElement("w:rPrDefault")
        defaults.insert(0, rpr_default)
    r_pr = rpr_default.find(qn("w:rPr"))
    if r_pr is None:
        r_pr = OxmlElement("w:rPr")
        rpr_default.append(r_pr)

    ppr_default = defaults.find(qn("w:pPrDefault"))
    if ppr_default is None:
        ppr_default = OxmlElement("w:pPrDefault")
        defaults.append(ppr_default)
    p_pr = ppr_default.find(qn("w:pPr"))
    if p_pr is None:
        p_pr = OxmlElement("w:pPr")
        ppr_default.append(p_pr)
    return r_pr, p_pr


def _set_document_default_spacing(doc, profile):
    """Default paragraph spacing from the profile (replaces 10pt after / 1.15)."""
    _, p_pr = _document_defaults(doc)
    spacing = p_pr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        p_pr.insert(0, spacing)
    after = max(float(profile.parskip_pt), 0.0)
    line = max(float(profile.line_spacing), 0.5)
    spacing.set(qn("w:before"), "0")
    spacing.set(qn("w:after"), str(int(round(after * 20))))
    spacing.set(qn("w:line"), str(int(round(line * 240))))
    spacing.set(qn("w:lineRule"), "auto")
    spacing.set(qn("w:beforeAutospacing"), "0")
    spacing.set(qn("w:afterAutospacing"), "0")


def _configure_document(doc, prefs_dict, profile=None):
    """Page size, margins, fonts and dense spacing from prefs_dict + profile."""
    profile = _profile_or_default(profile)
    p = prefs_dict if isinstance(prefs_dict, dict) else {}
    width, height = PAPER_SIZES.get(_text(_value(p, "paper")).lower() or "a4", PAPER_SIZES["a4"])
    section = doc.sections[0]
    section.page_width = Cm(width)
    section.page_height = Cm(height)
    margins = _value(p, "margins") or {}
    section.top_margin = Cm(_number(_value(margins, "top"), DEFAULT_MARGIN))
    section.bottom_margin = Cm(_number(_value(margins, "bottom"), DEFAULT_MARGIN))
    section.left_margin = Cm(_number(_value(margins, "left"), DEFAULT_MARGIN))
    section.right_margin = Cm(_number(_value(margins, "right"), DEFAULT_MARGIN))

    size = _number(_value(p, "font_size"), DEFAULT_FONT_SIZE)
    family = SANS_FONT if _text(profile.font_family).lower() == "sans" else SERIF_FONT

    # Document default rPr: runs inherit the explicit fonts (and size).
    default_r_pr, _ = _document_defaults(doc)
    _set_rpr_fonts(default_r_pr, family)
    _set_rpr_size(default_r_pr, size)
    _set_document_default_spacing(doc, profile)

    # Normal style: the same fonts plus the profile's paragraph rhythm.
    style = doc.styles["Normal"]
    style.font.size = Pt(size)
    style.font.name = family
    _set_rpr_fonts(style.element.get_or_add_rPr(), family)
    paragraph_format = style.paragraph_format
    paragraph_format.space_before = Pt(0)
    paragraph_format.space_after = Pt(max(float(profile.parskip_pt), 0.0))
    paragraph_format.line_spacing = max(float(profile.line_spacing), 0.5)


def _add_education_entry(container, entry, L, palette, profile=None, width_cm=None,
                         with_course=False):
    """Latin education entry: date/title line, italic institution, grade line."""
    degree_type = _text(option_label(_value(entry, "degree_type"), L.get("degree_type")))
    degree = _text(_value(entry, "degree"))
    label = " — ".join(x for x in (degree_type, degree) if x)
    _add_entry_title(
        container, _value(entry, "start"), _value(entry, "end"), label, palette,
        profile, width_cm,
    )
    _add_gray_italic(container, _value(entry, "institution"), palette)
    grade = _text(_value(entry, "grade"))
    if grade:
        paragraph = container.add_paragraph()
        _zero_spacing(paragraph, 0.0, 1.0)
        paragraph.add_run(_text(L["grade"]) + " ").bold = True
        paragraph.add_run(grade)


def _add_work_entry(container, entry, L, palette, profile=None, width_cm=None,
                    with_course=False):
    """Latin work entry: date/title line, italic company, mode, achievements."""
    _add_entry_title(
        container, _value(entry, "start"), _value(entry, "end"),
        _value(entry, "position"), palette, profile, width_cm,
    )
    _add_gray_italic(container, _value(entry, "company"), palette)
    work_mode = _text(option_label(_value(entry, "work_mode"), L.get("work_mode")))
    if work_mode:
        paragraph = container.add_paragraph()
        _zero_spacing(paragraph, 0.0, 1.0)
        run = paragraph.add_run("(" + work_mode + ")")
        run.font.size = Pt(max(_normal_font_size(container) - 2.0, 7.0))
        if palette is not None:
            run.font.color.rgb = palette.gray
        _run_font(run, _family_for(_profile_or_default(profile)))
    for achievement in _text(_value(entry, "achievements")).splitlines():
        achievement = achievement.strip()
        if achievement:
            _add_bullet(container, achievement, palette, profile)


def _add_project_entry(container, entry, L, palette, profile=None, width_cm=None,
                       with_course=False):
    """Latin project entry: date/title line, organization, description, result."""
    _add_entry_title(
        container, _value(entry, "start"), _value(entry, "end"),
        _value(entry, "name"), palette, profile, width_cm,
    )
    organization = _text(_value(entry, "organization"))
    course = _text(_value(entry, "course")) if with_course else ""
    if organization or course:
        paragraph = container.add_paragraph()
        _zero_spacing(paragraph, 0.0, 1.0)
        if organization:
            run = paragraph.add_run(organization)
            run.italic = True
            if palette is not None:
                run.font.color.rgb = palette.gray
            _run_font(run, _family_for(_profile_or_default(profile)))
        if course:
            if organization:
                paragraph.add_run("   ")
            paragraph.add_run(course)
    _add_paragraphs(container, _value(entry, "description"))
    result = _text(_value(entry, "result"))
    if result:
        paragraph = container.add_paragraph()
        paragraph.add_run(_text(L["result"]) + " ").bold = True
        paragraph.add_run(result)
    link = _text(_value(entry, "link"))
    if link:
        paragraph = container.add_paragraph()
        paragraph.add_run(_text(L["link"]) + " ").bold = True
        paragraph.add_run(link)


def _add_cn_work_entry(container, entry, L, palette, profile=None,
                       width_cm=None, with_course=False):
    """Chinese work entry: one three-column line and square-marker achievements.

    ``work_mode`` is folded into the organization string as
    ``Company (Remote)``, exactly like ``_chinese_work_entry`` in latex_gen.
    """
    date = _date_range(_value(entry, "start"), _value(entry, "end"))
    position = _text(_value(entry, "position"))
    company = _text(_value(entry, "company"))
    work_mode = _text(option_label(_value(entry, "work_mode"), L.get("work_mode")))
    if work_mode:
        # A non-breaking space keeps ``(Remote)`` / ``(现场)`` together: the
        # narrow right-hand column may still wrap, but it never splits the
        # opening bracket from its content.
        company = (company + "\u00a0(" + work_mode + ")").strip()
    _add_cn_entry_line(container, date, position, company, palette, profile, width_cm)
    for achievement in _text(_value(entry, "achievements")).splitlines():
        achievement = achievement.strip()
        if achievement:
            _add_bullet(container, achievement, palette, profile)


def _add_cn_education_entry(container, entry, L, palette, profile=None,
                            width_cm=None, with_course=False):
    """Chinese education entry: date / institution / degree line plus the grade."""
    date = _date_range(_value(entry, "start"), _value(entry, "end"))
    institution = _text(_value(entry, "institution"))
    degree_type = _text(option_label(_value(entry, "degree_type"), L.get("degree_type")))
    degree = _text(_value(entry, "degree"))
    label = " — ".join(x for x in (degree_type, degree) if x)
    _add_cn_entry_line(container, date, institution, label, palette, profile, width_cm)
    grade = _text(_value(entry, "grade"))
    if grade:
        paragraph = container.add_paragraph()
        _zero_spacing(paragraph, 0.0, CN_ENTRY_GAP_PT)
        paragraph.add_run(_text(L["grade"]) + " ").bold = True
        paragraph.add_run(grade)


def _add_cn_project_entry(container, entry, L, palette, profile=None,
                          width_cm=None, with_course=False):
    """Chinese project entry: three-column line + description/result/link bullets."""
    date = _date_range(_value(entry, "start"), _value(entry, "end"))
    name = _text(_value(entry, "name"))
    organization = _text(_value(entry, "organization"))
    if with_course:
        course = _text(_value(entry, "course"))
        if course:
            organization = (organization + " — " + course) if organization else course
    _add_cn_entry_line(container, date, name, organization, palette, profile, width_cm)
    for line in _text(_value(entry, "description")).splitlines():
        line = line.strip()
        if line:
            _add_bullet(container, line, palette, profile)
    result = _text(_value(entry, "result"))
    if result:
        paragraph = _bullet_slot(container, palette, profile, 1)
        if paragraph is not None:
            paragraph.add_run(_text(L["result"]) + " ").bold = True
            paragraph.add_run(result)
    link = _text(_value(entry, "link"))
    if link:
        paragraph = _bullet_slot(container, palette, profile, 1)
        if paragraph is not None:
            paragraph.add_run(_text(L["link"]) + " ").bold = True
            paragraph.add_run(link)


#: Entry renderer per section for the Latin templates (``university_projects``
#: adds the course line).
_LATIN_ENTRY_RENDERERS = {
    "work": _add_work_entry,
    "internships": _add_work_entry,
    "education": _add_education_entry,
    "projects": _add_project_entry,
    "university_projects": lambda c, e, L, p, pr, w=None: _add_project_entry(
        c, e, L, p, pr, w, True,
    ),
}

#: Entry renderer per section for the Chinese-style templates.
_CN_ENTRY_RENDERERS = {
    "work": _add_cn_work_entry,
    "internships": _add_cn_work_entry,
    "education": _add_cn_education_entry,
    "projects": _add_cn_project_entry,
    "university_projects": lambda c, e, L, p, pr, w=None: _add_cn_project_entry(
        c, e, L, p, pr, w, True,
    ),
}


def _entry_renderer(key, profile):
    """Entry builder for ``key`` in the template family of ``profile``."""
    table = _CN_ENTRY_RENDERERS if _text(profile.template) in CN_STYLE_TEMPLATES else _LATIN_ENTRY_RENDERERS
    return table.get(key)



def _add_skills_section(doc, d, L, palette, title=None, profile=None):
    raw_entries = _value(d, "skills")
    entries = [e for e in raw_entries if isinstance(e, dict)] if isinstance(raw_entries, (list, tuple)) else []
    rows = []
    for e in entries:
        category = _text(_value(e, "category"))
        values = [v.strip() for v in _text(_value(e, "values")).split(",") if v.strip()]
        if category or values:
            rows.append((category, values))
    if not rows:
        return
    _add_heading(doc, title or L["skills"], palette, profile)
    for category, values in rows:
        paragraph = doc.add_paragraph()
        if category and values:
            paragraph.add_run(category + L["skill_separator"] + " ").bold = True
            paragraph.add_run(", ".join(values))
        elif category:
            paragraph.add_run(category).bold = True
        else:
            paragraph.add_run(", ".join(values))


def _add_pairs_section(container, entries, L, key, field_a, field_b, palette, title=None, profile=None):
    """Languages/references: one bulleted ``name --- value`` line per entry.

    ``latex_gen._pairs`` wraps the same rows in ``_itemize`` with a ``" --- "``
    separator, so the Word export keeps the bullet and the exact separator.
    """
    rows = []
    if not isinstance(entries, (list, tuple)):
        return
    for e in entries:
        if not isinstance(e, dict):
            continue
        a = _text(_value(e, field_a))
        b = _text(_value(e, field_b))
        if a or b:
            rows.append((a, b))
    if not rows:
        return
    try:
        title = title or L[key]
    except Exception:
        title = title or key
    _add_heading(container, title, palette, profile)
    for a, b in rows:
        paragraph = _bullet_slot(container, palette, profile, 1)
        if paragraph is None:
            continue
        if a:
            paragraph.add_run(a).bold = True
        if a and b:
            paragraph.add_run(" --- " + b)
        elif b:
            paragraph.add_run(b)


def _block_anchor(value):
    """Valid anchor or "end" for a block with a missing or unknown position."""
    anchor = _text(value)
    return anchor if anchor in BLOCK_ANCHORS else "end"


def _group_blocks(d):
    """Distribute free blocks by anchor; ignore anything that is not a dict."""
    groups = {anchor: [] for anchor in BLOCK_ANCHORS}
    entries = _value(d, "blocks")
    if not isinstance(entries, (list, tuple)):
        return groups
    for block in entries:
        if isinstance(block, dict):
            groups[_block_anchor(_value(block, "position"))].append(block)
    return groups


def _separator_specs(profile, style):
    """``(role, pt)`` list of a separator style; LaTeX defaults when missing."""
    defaults = {
        "line": (("accent", 0.6),),
        "band": (("accent", 3.5),),
    }
    specs = ()
    try:
        specs = tuple(profile.separators.get(style) or ())
    except Exception:
        specs = ()
    out = []
    for spec in specs:
        try:
            if len(spec) >= 2:
                out.append((spec[0], spec[1]))
        except Exception:
            continue
    return tuple(out) or defaults.get(style, (("accent", 0.6),))


def _separator_rule(doc, spec, palette, before_pt, after_pt):
    """Tight rule paragraph (bottom border) of one separator hairline."""
    paragraph = doc.add_paragraph()
    _zero_spacing(paragraph, before_pt, after_pt)
    docx_shapes.set_exact_line_height(paragraph, 0.9)
    docx_shapes.set_paragraph_mark_size(paragraph, 0.9)
    role, size = spec[0], _clamp_number(spec[1], 0.6, 0.25, 12.0)
    color = palette.role_hex(role) if palette is not None else COLOR_ACCENT
    docx_shapes.set_rule(paragraph, "bottom", color, size, 1)
    return paragraph


def _line_separator(doc, palette=None, profile=None):
    """Thin separator: tight paragraphs carrying the profile's hairline(s).

    LaTeX draws ``\\cvblockline`` as 0.45em / rule / 0.45em. Most templates use
    one 0.6-0.7pt hairline, but harvard stacks a gray 0.5pt + 0.25pt pair and
    ribbon an accent 0.7pt + gold 0.4pt pair: every spec of the profile is
    drawn, on its own 0.9pt paragraph, so the secondary hairline of the
    template survives. No 11pt empty shaded block is involved.
    """
    specs = _separator_specs(profile, "line")
    paragraphs = []
    for index, spec in enumerate(specs):
        last = index == len(specs) - 1
        paragraphs.append(
            _separator_rule(
                doc, spec, palette,
                4.5 if index == 0 else 0.6,
                4.5 if last else 0.6,
            )
        )
    return paragraphs[0] if paragraphs else None


def _band_separator(doc, palette=None, profile=None):
    """Wide separator: a small shaded bar plus the template's secondary rule.

    ``\\cvblockband`` is a solid accent rule of 0.3-0.35em (3.2-3.9pt at the
    11pt body size). A profile whose band starts with a thick colour becomes a
    shaded bar of exactly that height; every following ``(role, pt)`` pair is a
    hairline under it (the gold trim of ribbon, the coral hairline of playful).
    A band made only of hairlines (navy) draws the rules and no fill at all.
    """
    specs = _separator_specs(profile, "band")
    role, size = specs[0][0], _clamp_number(specs[0][1], 3.5, 0.25, 12.0)
    fill = palette.role_hex(role) if palette is not None else COLOR_ACCENT
    paragraphs = []
    if size >= 1.8:
        bar = docx_shapes.shaded_bar(doc, fill, thickness_pt=size)
        if bar is not None:
            try:
                bar.paragraph_format.space_before = Pt(4.5)
                bar.paragraph_format.space_after = Pt(0.8)
            except Exception:
                pass
            paragraphs.append(bar)
        tail = specs[1:]
        before = 0.8
    else:
        tail = specs
        before = 4.5
    for index, spec in enumerate(tail):
        last = index == len(tail) - 1
        paragraphs.append(
            _separator_rule(
                doc, spec, palette, before,
                4.5 if last else 0.8,
            )
        )
        before = 0.8
    return paragraphs[0] if paragraphs else None


def _render_separator_block(doc, block, palette=None, profile=None):
    """A separator is always drawn; an unknown style falls back to "line"."""
    style = _text(_value(block, "style"))
    if style not in SEPARATOR_STYLES:
        style = "line"
    if style == "band":
        _band_separator(doc, palette, profile)
    elif style == "space":
        paragraph = doc.add_paragraph()
        _zero_spacing(paragraph)
        docx_shapes.set_exact_line_height(paragraph, 22.0)
        docx_shapes.set_paragraph_mark_size(paragraph, 2.0)
    else:
        _line_separator(doc, palette, profile)


def _render_section_block(doc, block, palette=None, profile=None):
    """Bold title and content by lines; it is skipped only when all is empty."""
    title = _text(_value(block, "title"))
    if not title and not _text(_value(block, "content")):
        return
    if title:
        _add_heading(doc, title, palette, profile)
    _add_paragraphs(doc, _value(block, "content"))


def _render_list_block(doc, block, palette=None, profile=None):
    """Generic list: title/detail or period/description pairs.

    A free list block is always drawn as one column: its ``mode`` only selects
    the row shape (title/detail vs period/description); the ``columns`` grid
    belongs to the entry sections (see ``_add_entry_columns``).
    """
    mode = _text(_value(block, "mode"))
    if mode not in LIST_MODES:
        mode = "columns"
    title = _text(_value(block, "title"))
    entries = _value(block, "entries")
    rows = []
    for entry in entries if isinstance(entries, (list, tuple)) else []:
        if not isinstance(entry, dict):
            continue
        if mode == "period":
            period = _text(_value(entry, "period"))
            description = _text(_value(entry, "description"))
            if period or description:
                rows.append((period, description))
        else:
            heading = _text(_value(entry, "title"))
            detail = _text(_value(entry, "detail"))
            if heading or detail:
                rows.append((heading, detail))
    if not rows:
        return
    if title:
        _add_heading(doc, title, palette, profile)
    for a, b in rows:
        if mode == "period":
            if a:
                paragraph = doc.add_paragraph()
                run = paragraph.add_run(a)
                run.italic = True
                if palette is not None:
                    run.font.color.rgb = palette.gray
            if b:
                doc.add_paragraph(b)
        else:
            paragraph = doc.add_paragraph()
            if a and b:
                paragraph.add_run(a).bold = True
                paragraph.add_run(" --- " + b)
            elif a:
                paragraph.add_run(a).bold = True
            else:
                paragraph.add_run(b)


def _render_blocks(doc, blocks, palette=None, profile=None):
    """Draw the blocks of one anchor in the same list order."""
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = _text(_value(block, "type"))
        if block_type == "separator":
            _render_separator_block(doc, block, palette, profile)
        elif block_type == "section":
            _render_section_block(doc, block, palette, profile)
        elif block_type == "list":
            _render_list_block(doc, block, palette, profile)


def _section_columns(d, key, profile):
    """Per-section column count, clamped to 1-3 (1 for the Chinese family).

    Only the Latin templates honour ``data["columns"]``: the Chinese-style
    templates draw a three-column entry line inside a single body column, so a
    ``columns`` value is ignored there, exactly like latex_gen's
    ``_chinese_render_section``.
    """
    if not bool(getattr(profile, "columns_supported", False)):
        return 1
    if _text(profile.template) in CN_STYLE_TEMPLATES:
        return 1
    raw = _value(d, "columns")
    value = 1
    try:
        if isinstance(raw, dict):
            value = raw.get(key, 1)
    except Exception:
        value = 1
    try:
        value = int(value)
    except Exception:
        value = 1
    return min(max(value, 1), 3)


def _add_entry_columns(doc, entries, render, columns, L, palette, profile):
    """Render the entries of one section in a fixed ``columns``-wide table.

    Balanced row-major distribution (like ``_render_section``: rows of
    ``columns`` entries), equal columns whose widths sum to the text width and
    a hair of inner padding as the gutter. Single-column sections never reach
    here. The last row may keep empty trailing cells: they have no borders and
    no fill, so nothing is drawn for them.
    """
    columns = min(max(int(_clamp_number(columns, 1, 1, 3)), 1), 3)
    if columns <= 1 or len(entries) <= 1:
        for entry in entries:
            render(doc, entry, L, palette, profile)
        return
    total = _text_width_cm(doc)
    width = total / float(columns)
    table = docx_shapes.fixed_table(doc, tuple(width for _ in range(columns)))
    if table is None:
        for entry in entries:
            render(doc, entry, L, palette, profile)
        return
    rows = (len(entries) + columns - 1) // columns
    for index in range(1, rows):
        try:
            table.add_row()
        except Exception:
            break
    for index, entry in enumerate(entries):
        try:
            cell = table.cell(index // columns, index % columns)
        except Exception:
            continue
        _cell_padding(cell, top=0, right=0.14, bottom=0, left=0.14)
        try:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
        except Exception:
            pass
        try:
            render(cell, entry, L, palette, profile, width - 0.28)
            _drop_leading_empty(cell)
        except Exception:
            try:
                cell.add_paragraph(_text(_value(entry, "position")) or _text(_value(entry, "name")))
            except Exception:
                continue
        try:
            last = cell.paragraphs[-1]
            last.paragraph_format.space_after = Pt(max(CN_ENTRY_GAP_PT, 0.0))
        except Exception:
            pass
    return table


def _add_body(doc, d, L, palette=None, profile=None):
    """Sections with the same order, visibility and titles as latex_gen.

    The normalized order and the hidden sections are delegated to latex_gen
    (normalize_section_order / is_section_hidden) and the custom titles to
    custom_section_title, with L[key] as fallback. The text is plain, without
    LaTeX escaping. ``palette`` colors the headings and separators; None keeps
    the default accent. ``profile`` selects the heading shape, the bullet
    marker and the entry family (Latin date/title line vs the Chinese
    three-column line), and enables the per-section ``columns`` of the six
    Latin templates.

    Free blocks are interleaved after their anchor section; the "start" and
    "end" anchors open and close the body. An empty or hidden section still
    shows the blocks anchored to it (positional anchor) and emits no heading.
    """
    profile = _profile_or_default(profile)
    groups = _group_blocks(d)
    _render_blocks(doc, groups["start"], palette, profile)

    for key in latex_gen.normalize_section_order(d):
        if not latex_gen.is_section_hidden(d, key):
            title = latex_gen.custom_section_title(d, key) or L[key]
            render = _entry_renderer(key, profile)
            if key == "summary":
                if _text(_value(d, "summary")):
                    _add_heading(doc, title, palette, profile)
                    _add_paragraphs(doc, _value(d, "summary"))
            elif render is not None:
                entries = _entries_with_content(_value(d, key))
                if entries:
                    _add_heading(doc, title, palette, profile)
                    _add_entry_columns(
                        doc, entries, render, _section_columns(d, key, profile),
                        L, palette, profile,
                    )
            elif key == "skills":
                _add_skills_section(doc, d, L, palette, title, profile)
            elif key == "languages":
                _add_pairs_section(doc, _value(d, "languages"), L, key, "language", "level", palette, title, profile)
            elif key == "references":
                _add_pairs_section(doc, _value(d, "references"), L, key, "name", "contact", palette, title, profile)
        # Block anchored to this section: it is emitted even if the section is
        # hidden or empty, to preserve the chosen positional anchor.
        _render_blocks(doc, groups[key], palette, profile)
    _render_blocks(doc, groups["end"], palette, profile)


def export(data, prefs_dict, path):
    """Export `data` to a DOCX file at `path`.

    `prefs_dict` uses the same keys as prefs.load(): paper, margins,
    font_size and colors (primary, secondary, text, gray). The palette falls
    back to the colors of the selected LaTeX template, so a default export is
    visually the same design as the PDF. Every template renders its own
    heading shape, entry line family and bullet marker; the Latin templates
    also honour ``data["columns"]`` (1-3) as a balanced fixed table.
    """
    if not isinstance(data, dict):
        data = {}
    try:
        L = LANG.get(str(_value(data, "cv_language", "zh")), LANG["zh"])
    except Exception:
        L = LANG["zh"]
    profile = docx_profiles.profile_for(_template_id(data))
    doc = Document()
    _configure_document(doc, prefs_dict or {}, profile)
    palette = _build_palette(data, prefs_dict)
    # text -> Normal style base color; the accent is used by headings/header.
    if palette.text is not None:
        doc.styles["Normal"].font.color.rgb = palette.text
    body = _add_header(doc, data, L, palette, profile)
    if body is not None and hasattr(body, "_tc"):
        # Sidebar family: the whole CV lives in the body cell of the page-wide
        # header table so the accent bar runs beside it on every page.
        _add_body(body, data, L, palette, profile)
        # Word wants a paragraph after a trailing table; keep it sub-point so
        # it cannot spill a blank page out of the at-least row height.
        tail = doc.add_paragraph()
        _zero_spacing(tail)
        docx_shapes.set_exact_line_height(tail, 0.8)
    else:
        _add_body(doc, data, L, palette, profile)
    doc.save(path)
