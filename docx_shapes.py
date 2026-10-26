# -*- coding: utf-8 -*-
"""Word-safe shape primitives for the per-template DOCX layout.

The LaTeX templates draw their visual identity with solid colour bands,
stepped blades, plates with tails and page frames. Word cannot import that
DrawingML safely (python-docx's ``qn`` does not know the ``wps``/``mc``
namespaces), so every shape here is built only from the primitives Word
understands and python-docx exposes:

* paragraph shading (``w:shd``) to paint a filled area,
* exact line spacing (``w:spacing`` with ``lineRule="exact"``) to give that
  area an exact height,
* left/right paragraph indents to give it an exact width,
* paragraph and cell borders (``w:pBdr``/``w:tcBorders``/``w:tblBorders``/
  ``w:pgBorders``) for rules and frames,
* fixed tables with zero cell margins when a plate needs a different colour
  from its tail or when a shape must not wrap.

Twip arithmetic used across this module: ``1 pt = 20 twips`` and
``1 cm = 1440 / 2.54 = 566.929 twips``. ``w:sz`` is always in eighths of a
point and ``w:space`` (paragraph borders) is in points.

Every helper is defensive: hostile or ``None`` inputs never raise and the
created element (or elements) is returned so callers can assert on it.
"""

from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.enum.table import WD_ALIGN_VERTICAL

# ---------------------------------------------------------------------------
# Constants and low-level helpers
# ---------------------------------------------------------------------------

TWIPS_PER_CM = 1440.0 / 2.54
TWIPS_PER_PT = 20.0
PT_PER_CM = 72.0 / 2.54
EMU_PER_CM = 360000

#: Schema order of the ``w:pBdr`` children.
PBDR_EDGES = ("top", "left", "bottom", "right", "between", "bar")

#: Schema order of the ``w:tcBorders`` children.
TCBDR_EDGES = ("top", "left", "bottom", "right", "insideH", "insideV", "tl2br", "tr2bl")

#: Children that follow ``w:pBdr`` inside ``w:pPr`` (schema order).
PBDR_SUCCESSORS = (
    "w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
    "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN",
    "w:bidi", "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind",
    "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
    "w:textDirection", "w:textAlignment", "w:textboxTightWrap",
    "w:outlineLvl", "w:divId", "w:cnfStyle", "w:rPr", "w:sectPr",
    "w:pPrChange",
)

#: Children that follow ``w:shd`` inside ``w:pPr``.
PPR_SHADING_SUCCESSORS = PBDR_SUCCESSORS[1:]

#: Children that follow ``w:rPr`` inside ``w:pPr``.
PPR_RPR_SUCCESSORS = ("w:sectPr", "w:pPrChange")

#: Children that follow ``w:pBdr`` inside ``w:pPr`` when the parent is a cell.
TCBDR_SUCCESSORS = (
    "w:shd", "w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText",
    "w:vAlign", "w:hideMark", "w:headers", "w:cellIns", "w:cellDel",
    "w:cellMerge", "w:tcPrChange",
)

#: Children that follow ``w:tblInd`` inside ``w:tblPr``.
TBLIND_SUCCESSORS = (
    "w:tblBorders", "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook",
    "w:tblCaption", "w:tblDescription", "w:tblPrChange",
)

#: Children that follow ``w:tblW`` inside ``w:tblPr``.
TBLW_SUCCESSORS = (
    "w:jc", "w:tblCellSpacing", "w:tblInd", "w:tblBorders", "w:shd",
    "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption",
    "w:tblDescription", "w:tblPrChange",
)

#: Children that follow ``w:tblBorders`` inside ``w:tblPr``.
TBLBORDERS_SUCCESSORS = (
    "w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption",
    "w:tblDescription", "w:tblPrChange",
)

#: Children that follow ``w:tblLayout`` inside ``w:tblPr``.
TBLLAYOUT_SUCCESSORS = (
    "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription",
    "w:tblPrChange",
)

#: Children that follow ``w:tblCellMar`` inside ``w:tblPr``.
TBLCELLMAR_SUCCESSORS = (
    "w:tblLook", "w:tblCaption", "w:tblDescription", "w:tblPrChange",
)

#: Children that follow ``w:trHeight`` inside ``w:trPr``.
TRHEIGHT_SUCCESSORS = (
    "w:tblHeader", "w:tblCellSpacing", "w:jc", "w:hidden", "w:ins",
    "w:del", "w:trPrChange",
)

#: Children that follow ``w:pgBorders`` inside ``w:sectPr``.
PGBORDERS_SUCCESSORS = (
    "w:lnNumType", "w:pgNumType", "w:cols", "w:formProt", "w:vAlign",
    "w:noEndnote", "w:titlePg", "w:textDirection", "w:bidi",
    "w:rtlGutter", "w:docGrid", "w:printerSettings", "w:sectPrChange",
)

DEFAULT_TEXT_WIDTH_CM = 17.0
DEFAULT_BORDER_PT = 0.75
_HEX_DIGITS = "0123456789abcdefABCDEF"


def _text(value):
    """Return ``value`` as stripped text; ``None`` and hostile objects -> ``""``."""
    if value is None:
        return ""
    try:
        return str(value).strip()
    except Exception:
        return ""


def _number(value, default):
    """Cast to float, falling back to ``default`` for non-numeric values."""
    try:
        return float(value)
    except Exception:
        try:
            return float(default)
        except Exception:
            return 0.0


def _clamp(value, default, low, high):
    """Numeric value clamped to ``[low, high]``; never raises."""
    number = _number(value, default)
    if number != number:  # NaN
        number = _number(default, low)
    return min(max(number, float(low)), float(high))


def _local(tag):
    """Local name of a Clark-notation XML tag."""
    try:
        return tag.rsplit("}", 1)[-1]
    except Exception:
        return ""


def _insert_ordered(parent, element, successors):
    """Insert ``element`` before the first successor found; never raises."""
    try:
        parent.insert_element_before(element, *successors)
    except Exception:
        try:
            parent.append(element)
        except Exception:
            pass


def _color(value, default="auto"):
    """Normalise a colour to six hex digits; invalid input -> ``default``.

    Accepts ``"RRGGBB"``, ``"#RRGGBB"`` and the short ``"#RGB"`` form. ``None``,
    integers and any malformed string fall back to ``default`` so the XML is
    always schema-valid.
    """
    if not isinstance(value, str):
        return default
    text = value.strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) == 3 and all(c in _HEX_DIGITS for c in text):
        text = "".join(c * 2 for c in text)
    if len(text) == 6 and all(c in _HEX_DIGITS for c in text):
        return text
    return default


def _eighths(size_pt, default=DEFAULT_BORDER_PT):
    """Border thickness in eighths of a point, clamped to Word's 2..96."""
    return int(round(_clamp(size_pt, default, 0.25, 12.0) * 8))


def _space_pt(value, default=1):
    """Border ``w:space`` in points, clamped to Word's 0..31."""
    return int(round(_clamp(value, default, 0.0, 31.0)))


def _twips_cm(value):
    """Centimetres -> whole twips."""
    return int(round(_clamp(value, 0.0, -1000.0, 1000.0) * TWIPS_PER_CM))


def _twips_pt(value):
    """Points -> whole twips."""
    return int(round(_clamp(value, 0.0, 0.0, 20000.0) * TWIPS_PER_PT))


def _cm_to_pt(value):
    """Centimetres -> points."""
    return _clamp(value, 0.0, -1000.0, 1000.0) * PT_PER_CM


def _pt_to_cm(value):
    """Points -> centimetres."""
    return _clamp(value, 0.0, -1000.0, 1000.0) / PT_PER_CM


def pt_to_cm(value):
    """Public alias of the points-to-centimetres conversion (never raises)."""
    return _pt_to_cm(value)


def _edges(edges, allowed):
    """Normalise ``edges`` (str, iterable or mapping) to a tuple of valid names."""
    if edges is None:
        return ()
    if isinstance(edges, str):
        candidates = (edges,)
    else:
        try:
            candidates = tuple(edges)
        except Exception:
            return ()
        if isinstance(edges, dict):
            candidates = tuple(edges.keys())
    out = []
    for edge in candidates:
        name = _text(edge).lower()
        if name in allowed and name not in out:
            out.append(name)
    return tuple(out)


def _get_or_add(parent, tag, successors):
    """Find ``tag`` under ``parent`` or create it in schema order."""
    element = parent.find(qn(tag))
    if element is None:
        element = OxmlElement(tag)
        _insert_ordered(parent, element, successors)
    return element


def _rebuild_borders(parent, tag, edge_order, successors, specs, color_default="auto"):
    """Create or replace a border container, keeping schema child order.

    ``specs`` maps edge name -> ``(color, eighths, space, value)``. Existing
    edges not named in ``specs`` are preserved and rewritten in order, so a
    repeated call replaces instead of duplicating.
    """
    container = parent.find(qn(tag))
    existing = {}
    if container is not None:
        for child in list(container):
            existing[_local(child.tag)] = child
        parent.remove(container)
    container = OxmlElement(tag)
    for edge, spec in specs.items():
        color, size8, space, value = spec
        element = OxmlElement("w:" + edge)
        element.set(qn("w:val"), _text(value) or "single")
        element.set(qn("w:sz"), str(size8))
        element.set(qn("w:space"), str(space))
        element.set(qn("w:color"), _color(color, color_default))
        existing[edge] = element
    for edge in edge_order:
        if edge in existing:
            container.append(existing[edge])
    _insert_ordered(parent, container, successors)
    return container


def _add_paragraph(container):
    """Append an empty paragraph to a Document, cell or cell-like container."""
    try:
        return container.add_paragraph()
    except Exception:
        return None


def _paragraph_width_cm(container):
    """Usable text width of a container in centimetres, or ``None``."""
    try:
        sections = getattr(container, "sections", None)
        if sections is not None and len(sections):
            section = sections[0]
            width = section.page_width.cm - section.left_margin.cm - section.right_margin.cm
            if width > 1.0:
                return width
    except Exception:
        pass
    try:
        tc = getattr(container, "_tc", None)
        if tc is not None:
            width = None
            tc_pr = getattr(tc, "tcPr", None)
            if tc_pr is not None:
                tc_w = tc_pr.find(qn("w:tcW"))
                if tc_w is not None and tc_w.get(qn("w:type")) == "dxa":
                    width = _number(tc_w.get(qn("w:w")), 0) / TWIPS_PER_CM
            if width is None:
                cell_width = getattr(container, "width", None)
                width = cell_width.cm if cell_width is not None else None
            if width and width > 0.5:
                margins = 0.28
                if tc_pr is not None:
                    mar = tc_pr.find(qn("w:tcMar"))
                    if mar is not None:
                        total = 0
                        for tag in ("left", "right"):
                            node = mar.find(qn("w:" + tag))
                            if node is not None:
                                total += _number(node.get(qn("w:w")), 0)
                        margins = total / TWIPS_PER_CM
                return max(width - margins, 0.5)
    except Exception:
        pass
    return None


def _resolve_indents(container, width_cm, left_cm, right_cm):
    """Left/right indents (cm) that place a bar of ``width_cm`` in ``container``."""
    text_width = _paragraph_width_cm(container) or DEFAULT_TEXT_WIDTH_CM
    left = _clamp(left_cm, 0.0, 0.0, text_width - 0.2)
    if width_cm is None:
        right = _clamp(right_cm, 0.0, 0.0, text_width)
        if left + right > text_width - 0.2:
            right = max(text_width - left - 0.2, 0.0)
        return left, right
    width = _clamp(width_cm, 1.0, 0.05, text_width)
    right = text_width - left - width
    if right < 0.0:
        # The requested bar is wider than the remaining measure: clip it.
        left = max(text_width - width, 0.0)
        right = 0.0
    return left, right


def _set_alignment(paragraph, align):
    """Apply an alignment given as enum member or string; ignore unknown values."""
    if align is None:
        return
    if isinstance(align, str):
        mapping = {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "centre": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        align = mapping.get(align.strip().lower())
    if align is None:
        return
    try:
        paragraph.alignment = align
    except Exception:
        pass


def _zero_paragraph(paragraph):
    """Remove all vertical and horizontal spacing from a ¶."""
    try:
        fmt = paragraph.paragraph_format
        fmt.space_before = Pt(0)
        fmt.space_after = Pt(0)
        fmt.first_line_indent = Cm(0)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Paragraph rules (w:pBdr)
# ---------------------------------------------------------------------------

def set_rule(paragraph, edges, color_hex, size_pt, space_pt=1, value="single"):
    """Set paragraph borders on ``edges``, replacing earlier ones.

    ``edges`` accepts a single name or any iterable of ``top``/``left``/
    ``bottom``/``right``/``between``/``bar``. ``size_pt`` is converted to
    eighths of a point (``w:sz``) and ``space_pt`` to ``w:space``. A repeated
    call replaces the existing ``w:pBdr`` children instead of duplicating the
    container, and the children are always written in schema order.

    Returns the ``w:pBdr`` element, or ``None`` when the paragraph has no
    usable ``pPr``.
    """
    try:
        p_pr = paragraph._p.get_or_add_pPr()
    except Exception:
        return None
    allowed = _edges(edges, PBDR_EDGES)
    if not allowed:
        return None
    size8 = _eighths(size_pt)
    space = _space_pt(space_pt)
    specs = {edge: (color_hex, size8, space, _text(value) or "single") for edge in allowed}
    return _rebuild_borders(p_pr, "w:pBdr", PBDR_EDGES, PBDR_SUCCESSORS, specs)


def add_rule_below(paragraph, color_hex, size_pt=DEFAULT_BORDER_PT, space_pt=1):
    """Bottom rule for ``paragraph``; returns the ``w:pBdr`` element."""
    return set_rule(paragraph, "bottom", color_hex, size_pt, space_pt)


def add_rule_above(paragraph, color_hex, size_pt=DEFAULT_BORDER_PT, space_pt=1):
    """Top rule for ``paragraph``; returns the ``w:pBdr`` element."""
    return set_rule(paragraph, "top", color_hex, size_pt, space_pt)


def add_double_rule(paragraph, color_hex, size_pt=1.0, space_pt=1, edge="bottom"):
    """Two-stroke rule on one paragraph edge.

    Word stores a single border per paragraph edge, so a two-colour double
    rule cannot be expressed on one paragraph. This helper uses the built-in
    ``double`` stroke of ``w:pBdr`` (two lines in ``color_hex``). Layouts that
    need two different colours stack two paragraphs, each with its own
    ``add_rule_below`` call.
    """
    return set_rule(paragraph, edge, color_hex, size_pt, space_pt, value="double")


# ---------------------------------------------------------------------------
# Shaded bars, blades and plates
# ---------------------------------------------------------------------------

def shade_paragraph(paragraph, color_hex):
    """Paint the paragraph area with ``color_hex`` (``w:shd``), replacing old."""
    try:
        p_pr = paragraph._p.get_or_add_pPr()
    except Exception:
        return None
    shd = p_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        _insert_ordered(p_pr, shd, PPR_SHADING_SUCCESSORS)
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), _color(color_hex, "FFFFFF"))
    return shd


def set_exact_line_height(paragraph, pt):
    """Force an exact rendered line height in points.

    ``w:spacing/@w:line`` is in twentieths of a point when
    ``@w:lineRule="exact"``, so ``pt * 20`` is the whole height of the line.
    """
    value = _clamp(pt, 6.0, 0.1, 1000.0)
    try:
        paragraph.paragraph_format.line_spacing = Pt(value)
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    except Exception:
        pass
    return paragraph


def set_paragraph_mark_size(paragraph, pt):
    """Size the paragraph mark (``w:pPr/w:rPr/w:sz``) so empty ¶s have a height."""
    try:
        p_pr = paragraph._p.get_or_add_pPr()
    except Exception:
        return None
    r_pr = p_pr.find(qn("w:rPr"))
    if r_pr is None:
        r_pr = OxmlElement("w:rPr")
        _insert_ordered(p_pr, r_pr, PPR_RPR_SUCCESSORS)
    half_points = str(int(round(_clamp(pt, 10.0, 0.5, 1000.0) * 2)))
    for tag in ("w:sz", "w:szCs"):
        node = r_pr.find(qn(tag))
        if node is None:
            node = OxmlElement(tag)
            r_pr.append(node)
        node.set(qn("w:val"), half_points)
    return r_pr


def shaded_bar(container, color_hex, width_cm=None, thickness_pt=6.0,
               left_cm=0.0, right_cm=0.0, align=None):
    """Append a paragraph painted as a solid bar.

    The rendered height is ``thickness_pt``: exact line spacing is set to
    ``thickness_pt * 20`` twips (``w:line``) and the paragraph mark is sized to
    the same value, so an empty paragraph cannot collapse or grow. The painted
    area is the text between the indents: ``width_cm`` wide starting at
    ``left_cm`` when given, otherwise the container measure minus ``left_cm``
    and ``right_cm``.

    Returns the paragraph, or ``None`` if the container cannot take one.
    """
    paragraph = _add_paragraph(container)
    if paragraph is None:
        return None
    thickness = _clamp(thickness_pt, 6.0, 0.1, 1000.0)
    _zero_paragraph(paragraph)
    set_exact_line_height(paragraph, thickness)
    set_paragraph_mark_size(paragraph, thickness)
    left, right = _resolve_indents(container, width_cm, left_cm, right_cm)
    try:
        paragraph.paragraph_format.left_indent = Cm(left)
        paragraph.paragraph_format.right_indent = Cm(right)
    except Exception:
        pass
    _set_alignment(paragraph, align)
    shade_paragraph(paragraph, color_hex)
    return paragraph


def full_width_bar(container, color_hex, thickness_pt, left_cm=0, right_cm=0):
    """Solid bar spanning the container width minus the given indents."""
    return shaded_bar(
        container, color_hex, width_cm=None, thickness_pt=thickness_pt,
        left_cm=left_cm, right_cm=right_cm,
    )


def stepped_blade(container, base_width_cm, steps=12, step_cm=None,
                  color_hex="000000", height_pt=7.0, align="right",
                  left_cm=0.0, right_cm=0.0):
    """Stack shaded paragraphs into the stair blade of ``templates/sword``.

    The sword template draws the tip with twelve rules whose widths are
    ``1, 11/12, ... 1/12`` of ``base_width_cm``, each ``0.6mm`` high, all
    starting from the same left edge (the blade is attached to the right end of
    the section plate). ``steps`` rows are emitted, each ``height_pt / steps``
    high, and one ``step_cm`` narrower than the row above.

    ``align="right"`` keeps the right edge fixed (the shape steps in from the
    right margin); ``align="left"`` keeps the left edge at ``left_cm`` (the
    literal sword construction, whose left edge sits on the plate end).

    Returns the list of created paragraphs (possibly empty).
    """
    steps = int(_clamp(steps, 12, 1, 64))
    total_height = _clamp(height_pt, 7.0, 0.5, 200.0)
    base_width = _clamp(base_width_cm, 2.0, 0.05, 100.0)
    height = total_height / steps
    step_width = _clamp(step_cm, base_width / steps, 0.0, base_width)
    text_width = _paragraph_width_cm(container) or DEFAULT_TEXT_WIDTH_CM
    left = _clamp(left_cm, 0.0, -text_width, text_width)
    right = _clamp(right_cm, 0.0, 0.0, text_width)
    paragraphs = []
    for index in range(steps):
        width = max(base_width - index * step_width, 0.02)
        if str(align).strip().lower() == "right":
            row_left = max(text_width - right - width, 0.0)
            row_right = right
        else:
            row_left = left
            row_right = max(text_width - left - width, 0.0)
        paragraph = shaded_bar(
            container, color_hex, width_cm=None, thickness_pt=height,
            left_cm=row_left, right_cm=row_right,
        )
        if paragraph is None:
            break
        paragraphs.append(paragraph)
    return paragraphs


def plate_with_tail(container, plate_width_cm, plate_height_pt, plate_color_hex,
                    title_text, title_color_hex, title_pt, tail_color_hex,
                    text_width_cm, margin_cm=0.15):
    """Coloured plate hugging a title plus a tail bar filling the line.

    A single shaded paragraph cannot give the plate and the tail two colours,
    so the shape is a 1x2 fixed table with zero cell margins and no borders:
    the left cell is ``plate_color_hex`` and holds the title, the right cell is
    ``tail_color_hex`` and only adds height.

    Long titles (``plate_width_cm`` too close to ``text_width_cm``, or the text
    wider than the available plate) fall back to a full-width plate with the
    title inside and no tail.

    Returns the created table.
    """
    text_width = _clamp(text_width_cm, DEFAULT_TEXT_WIDTH_CM, 1.0, 100.0)
    height_pt = _clamp(plate_height_pt, 20.0, 2.0, 400.0)
    height_cm = _pt_to_cm(height_pt)
    title_pt = _clamp(title_pt, 11.0, 1.0, 200.0)
    margin = _clamp(margin_cm, 0.15, 0.0, 5.0)
    plate_width = _clamp(plate_width_cm, 0.0, 0.0, text_width)
    long_title = (
        plate_width <= 0.0
        or plate_width >= text_width - margin
        or is_long_title(title_text, title_pt, plate_width)
    )
    if long_title:
        table = fixed_table(container, (text_width,))
        if table is None:
            return None
        cell = table.cell(0, 0)
        shade_cell(cell, plate_color_hex)
        _zero_cell_margins(cell)
        exact_row_height(table.rows[0], height_cm, rule="atLeast")
        paragraph = cell.paragraphs[0]
        _zero_paragraph(paragraph)
        _plate_title_run(paragraph, title_text, title_color_hex, title_pt)
        try:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        except Exception:
            pass
        return table

    tail_width = max(text_width - plate_width, 0.05)
    table = fixed_table(container, (plate_width, tail_width))
    if table is None:
        return None
    exact_row_height(table.rows[0], height_cm)
    plate_cell = table.cell(0, 0)
    tail_cell = table.cell(0, 1)
    shade_cell(plate_cell, plate_color_hex)
    shade_cell(tail_cell, tail_color_hex)
    _zero_cell_margins(plate_cell)
    _zero_cell_margins(tail_cell)
    paragraph = plate_cell.paragraphs[0]
    _zero_paragraph(paragraph)
    _plate_title_run(paragraph, title_text, title_color_hex, title_pt)
    for cell in (plate_cell, tail_cell):
        try:
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        except Exception:
            pass
    tail_paragraph = tail_cell.paragraphs[0]
    _zero_paragraph(tail_paragraph)
    set_exact_line_height(tail_paragraph, max(height_pt - 4.0, 1.0))
    return table


def _plate_title_run(paragraph, title_text, title_color_hex, title_pt):
    """Add the bold title run of a plate paragraph (never raises)."""
    try:
        run = paragraph.add_run(_text(title_text))
        run.bold = True
        run.font.size = Pt(_clamp(title_pt, 11.0, 1.0, 200.0))
        rgb = _color(title_color_hex, "FFFFFF")
        if rgb != "auto":
            from docx.shared import RGBColor

            run.font.color.rgb = RGBColor(
                int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)
            )
        return run
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def fixed_table(container, widths_cm, borders=None):
    """One-row fixed table with exact column widths and zero cell spacing.

    ``w:tblW`` is written as ``dxa`` (the sum of the widths in twips),
    ``w:tblLayout`` is ``fixed``, every ``w:gridCol``/``w:tcW`` pair shares the
    same width and ``w:tblCellMar`` is zero. ``borders=None`` means all six
    edges are ``nil``; a mapping ``{edge: (color, size_pt)}`` draws them.

    Returns the table, or ``None`` if the container refuses a table.
    """
    widths = []
    try:
        raw_widths = list(widths_cm) if widths_cm is not None else []
    except Exception:
        raw_widths = []
    for width in raw_widths:
        widths.append(_clamp(width, 1.0, 0.05, 100.0))
    if not widths:
        return None
    try:
        table = container.add_table(rows=1, cols=len(widths))
    except Exception:
        return None
    try:
        table.autofit = False
    except Exception:
        pass
    total_twips = sum(int(round(width * TWIPS_PER_CM)) for width in widths)
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        _insert_ordered(tbl_pr, tbl_w, TBLW_SUCCESSORS)
    tbl_w.set(qn("w:w"), str(total_twips))
    tbl_w.set(qn("w:type"), "dxa")

    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        _insert_ordered(tbl_pr, layout, TBLLAYOUT_SUCCESSORS)
    layout.set(qn("w:type"), "fixed")

    _zero_table_cell_margins(table)
    for index, width in enumerate(widths):
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
    _table_borders(table, borders)
    return table


def nested_table(cell, widths_cm, borders=None):
    """Same as :func:`fixed_table` but appended inside ``cell`` (depth 2 max)."""
    return fixed_table(cell, widths_cm, borders)


def _zero_table_cell_margins(table):
    """Write ``w:tblCellMar`` with all four sides at zero."""
    try:
        tbl_pr = table._tbl.tblPr
    except Exception:
        return None
    mar = tbl_pr.find(qn("w:tblCellMar"))
    if mar is None:
        mar = OxmlElement("w:tblCellMar")
        _insert_ordered(tbl_pr, mar, TBLCELLMAR_SUCCESSORS)
    for tag in ("top", "left", "bottom", "right"):
        node = mar.find(qn("w:" + tag))
        if node is None:
            node = OxmlElement("w:" + tag)
            mar.append(node)
        node.set(qn("w:w"), "0")
        node.set(qn("w:type"), "dxa")
    return mar


def _table_borders(table, borders):
    """Build ``w:tblBorders``: nil by default or the supplied edge mapping."""
    try:
        tbl_pr = table._tbl.tblPr
    except Exception:
        return None
    container = tbl_pr.find(qn("w:tblBorders"))
    if container is not None:
        tbl_pr.remove(container)
    container = OxmlElement("w:tblBorders")
    if borders is None:
        specs = {edge: ("auto", 0, 0, "nil") for edge in ("top", "left", "bottom", "right", "insideH", "insideV")}
    elif isinstance(borders, dict):
        specs = {}
        for edge, spec in borders.items():
            name = _text(edge).lower()
            if name not in ("top", "left", "bottom", "right", "insideH", "insideV"):
                continue
            if isinstance(spec, str) and spec.lower() == "nil":
                specs[name] = ("auto", 0, 0, "nil")
                continue
            if isinstance(spec, (list, tuple)) and len(spec) >= 2:
                color, size = spec[0], spec[1]
            else:
                color, size = "000000", DEFAULT_BORDER_PT
            specs[name] = (color, _eighths(size), 0, "single")
    else:
        specs = {edge: ("000000", _eighths(DEFAULT_BORDER_PT), 0, "single")
                 for edge in ("top", "left", "bottom", "right", "insideH", "insideV")}
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        if edge not in specs:
            specs[edge] = ("auto", 0, 0, "nil")
        color, size8, space, value = specs[edge]
        element = OxmlElement("w:" + edge)
        element.set(qn("w:val"), _text(value) or "nil")
        element.set(qn("w:sz"), str(size8))
        element.set(qn("w:space"), str(space))
        element.set(qn("w:color"), _color(color, "auto"))
        container.append(element)
    _insert_ordered(tbl_pr, container, TBLBORDERS_SUCCESSORS)
    return container


def shade_cell(cell, color_hex):
    """Fill a table cell with ``color_hex`` (``w:tcPr/w:shd``), replacing old."""
    try:
        tc_pr = cell._tc.get_or_add_tcPr()
    except Exception:
        return None
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        _insert_ordered(tc_pr, shd, TCBDR_SUCCESSORS)
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), _color(color_hex, "FFFFFF"))
    return shd


def set_cell_borders(cell, color_hex, size_pt=DEFAULT_BORDER_PT, edges=None):
    """Border ``edges`` (all four by default) around a table cell."""
    try:
        tc_pr = cell._tc.get_or_add_tcPr()
    except Exception:
        return None
    allowed = _edges(edges, TCBDR_EDGES) or ("top", "left", "bottom", "right")
    size8 = _eighths(size_pt)
    specs = {edge: (color_hex, size8, 0, "single") for edge in allowed}
    return _rebuild_borders(tc_pr, "w:tcBorders", TCBDR_EDGES, TCBDR_SUCCESSORS, specs)


def image_frame(cell, color_hex, size_pt=DEFAULT_BORDER_PT):
    """Thin frame around a cell that holds a picture (all four edges)."""
    return set_cell_borders(cell, color_hex, size_pt, edges=("top", "left", "bottom", "right"))


def _zero_cell_margins(cell):
    """Per-cell padding of zero on all four sides."""
    try:
        tc_pr = cell._tc.get_or_add_tcPr()
    except Exception:
        return None
    mar = tc_pr.find(qn("w:tcMar"))
    if mar is None:
        mar = OxmlElement("w:tcMar")
        _insert_ordered(tc_pr, mar, TCBDR_SUCCESSORS[3:])
    for tag in ("top", "left", "bottom", "right"):
        node = mar.find(qn("w:" + tag))
        if node is None:
            node = OxmlElement("w:" + tag)
            mar.append(node)
        node.set(qn("w:w"), "0")
        node.set(qn("w:type"), "dxa")
    return mar


def set_cell_indent(table, left_twips):
    """Shift a table with ``w:tblInd`` (negative values pull it into the margin)."""
    try:
        tbl_pr = table._tbl.tblPr
    except Exception:
        return None
    indent = tbl_pr.find(qn("w:tblInd"))
    if indent is None:
        indent = OxmlElement("w:tblInd")
        _insert_ordered(tbl_pr, indent, TBLIND_SUCCESSORS)
    indent.set(qn("w:w"), str(int(round(_clamp(left_twips, 0, -20000, 20000)))))
    indent.set(qn("w:type"), "dxa")
    return indent


def exact_row_height(row, cm, rule="exact"):
    """Set a row height in centimetres (``exact`` by default, or ``atLeast``)."""
    try:
        tr_pr = row._tr.get_or_add_trPr()
    except Exception:
        return None
    height = tr_pr.find(qn("w:trHeight"))
    if height is None:
        height = OxmlElement("w:trHeight")
        _insert_ordered(tr_pr, height, TRHEIGHT_SUCCESSORS)
    height.set(qn("w:val"), str(_twips_cm(cm)))
    height.set(qn("w:hRule"), "atLeast" if str(rule).lower() == "atleast" else "exact")
    return height


def page_frame(section, color_hex, size_pt, offset_cm):
    """Draw the four page borders of ``section`` in the page margin.

    The borders use ``w:offsetFrom="page"`` so they hug the paper edge instead
    of the text block; ``offset_cm`` is converted to the ``w:space`` value in
    points (Word's 0..31 range). ``w:sz`` is the stroke in eighths of a point.
    Returns the ``w:pgBorders`` element.
    """
    try:
        sect_pr = getattr(section, "_sectPr", section)
    except Exception:
        return None
    if sect_pr is None:
        return None
    container = sect_pr.find(qn("w:pgBorders"))
    if container is not None:
        sect_pr.remove(container)
    container = OxmlElement("w:pgBorders")
    container.set(qn("w:offsetFrom"), "page")
    size8 = _eighths(size_pt)
    space = int(round(_clamp(_cm_to_pt(offset_cm), 0.62, 0.0, 31.0)))
    for edge in ("top", "left", "bottom", "right"):
        element = OxmlElement("w:" + edge)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), str(size8))
        element.set(qn("w:space"), str(space))
        element.set(qn("w:color"), _color(color_hex, "auto"))
        container.append(element)
    _insert_ordered(sect_pr, container, PGBORDERS_SUCCESSORS)
    return container


# ---------------------------------------------------------------------------
# Text metrics and paragraph utilities
# ---------------------------------------------------------------------------

def text_width_cm(text, font_pt, cjk=False, bold=False):
    """Estimate the rendered width of ``text`` in centimetres.

    Heuristic only, used to size plates and tab stops (never to lay out the
    body): a Latin character averages ``0.5em`` and a CJK/full-width character
    ``1.0em`` of the font size; bold text is scaled by ``1.03``. Per-character
    classification handles mixed Latin/CJK strings; ``cjk=True`` forces every
    character to the CJK weight. Empty or unusable input returns ``0.0``; the
    result is clamped to ``0.2..200`` cm.
    """
    value = _text(text)
    if not value:
        return 0.0
    size = _clamp(font_pt, 11.0, 0.5, 200.0)
    em_units = 0.0
    for char in value:
        if cjk or ord(char) >= 0x2E80:
            em_units += 1.0
        else:
            em_units += 0.5
    factor = 1.03 if bold else 1.0
    width = em_units * size * factor / PT_PER_CM
    return min(max(width, 0.2), 200.0)


#: Alias used by ``is_long_title`` because its parameter shadows the function.
_estimate_width_cm = text_width_cm


def is_long_title(text, font_pt, text_width_cm, pad_em=1.2):
    """True when a plate title would leave no room for its bar or tail.

    ``pad_em`` is the horizontal padding of the plate in em of ``font_pt``.
    The comparison is ``estimated title width + padding >= available width``;
    empty titles are never long.
    """
    if not _text(text):
        return False
    width = _clamp(text_width_cm, DEFAULT_TEXT_WIDTH_CM, 0.1, 100.0)
    size = _clamp(font_pt, 11.0, 0.5, 200.0)
    pad = _clamp(pad_em, 1.2, 0.0, 20.0) * size / PT_PER_CM
    # The parameter shadows the module function; use the alias defined above.
    return _estimate_width_cm(text, size) + pad >= width


def keep_with_next(paragraph):
    """Keep ``paragraph`` on the same page as the following one."""
    try:
        paragraph.paragraph_format.keep_with_next = True
    except Exception:
        pass
    return paragraph


def set_tab_stop_right(paragraph, position_cm):
    """Add a right-aligned tab stop at ``position_cm``; returns the tab stop."""
    try:
        stops = paragraph.paragraph_format.tab_stops
        return stops.add_tab_stop(Cm(_clamp(position_cm, 0.0, 0.0, 100.0)), WD_TAB_ALIGNMENT.RIGHT)
    except Exception:
        return None


def hanging_indent(paragraph, cm):
    """Hang ``cm`` centimetres: positive left indent, negative first line."""
    value = abs(_clamp(cm, 0.0, 0.0, 100.0))
    try:
        paragraph.paragraph_format.left_indent = Cm(value)
        paragraph.paragraph_format.first_line_indent = Cm(-value)
    except Exception:
        pass
    return paragraph
