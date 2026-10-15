# -*- coding: utf-8 -*-
"""Word (.docx) CV generation with python-docx.

It does not depend on LaTeX or pywebview: only on python-docx and on the
latex_gen helpers (LANG translation table, section order/visibility/titles).
"""

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import latex_gen
from latex_gen import BLOCK_ANCHORS, LANG, LIST_MODES, SEPARATOR_STYLES, option_label

# Page size in centimetres: (width, height).
PAPER_SIZES = {
    "a4": (21.0, 29.7),
    "letter": (21.59, 27.94),
    "legal": (21.59, 35.56),
}

# Image extensions accepted for the photo.
PHOTO_EXTS = {".jpg", ".jpeg", ".png"}

DEFAULT_MARGIN = 2.0
DEFAULT_FONT_SIZE = 11.0
NAME_FONT_SIZE = 20.0
DEFAULT_PHOTO_WIDTH = 4.0

# Accent blue of the classic template (default CV color): used in the
# borders and bands of the free-block separators.
COLOR_ACCENT = "233A5E"


def _text(value):
    """Return the value as text without surrounding spaces."""
    if value is None:
        return ""
    return str(value).strip()


def _number(value, default):
    """Cast to float and fall back to the default when not numeric."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


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


def _entries_with_content(entries):
    """Filter empty entries, just like latex_gen does with sections."""
    if not isinstance(entries, (list, tuple)):
        return []
    return [entry for entry in entries if _has_content(entry)]


def _has_content(entry):
    if not isinstance(entry, dict):
        return bool(_text(entry))
    return any(_text(value) for value in entry.values())


def _date_range(start, end):
    start = _text(start)
    end = _text(end)
    if start and end:
        return f"{start} – {end}"
    return start or end


def _add_paragraphs(doc, text):
    """Add one paragraph per non-empty line (descriptions and profile)."""
    for line in str(text or "").splitlines():
        line = line.strip()
        if line:
            doc.add_paragraph(line)


def _add_bullet(doc, text):
    """Simple bullet; if the template lacks the style, use a prefix."""
    try:
        doc.add_paragraph(text, style="List Bullet")
    except Exception:
        doc.add_paragraph("• " + text)


def _add_heading(doc, title, color=None):
    """Section title in bold, two points larger than the normal font.

    ``color`` (RGBColor) tints the title; None keeps the default color.
    """
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(title)
    run.bold = True
    size = doc.styles["Normal"].font.size
    base = size.pt if size is not None else DEFAULT_FONT_SIZE
    run.font.size = Pt(base + 2)
    rgb = _to_rgb(color)
    if rgb is not None:
        run.font.color.rgb = rgb
    return paragraph


def _add_entry_title(doc, start, end, title):
    """First line of an entry: date in italics and title in bold."""
    date = _date_range(start, end)
    title = _text(title)
    if not date and not title:
        return None
    paragraph = doc.add_paragraph()
    if date:
        paragraph.add_run(date).italic = True
    if title:
        if date:
            paragraph.add_run("   ")
        paragraph.add_run(title).bold = True
    return paragraph


def _configure_document(doc, prefs_dict):
    """Page size, margins and Normal font size from prefs_dict."""
    p = prefs_dict or {}
    width, height = PAPER_SIZES.get(str(p.get("paper") or "a4").lower(), PAPER_SIZES["a4"])
    section = doc.sections[0]
    section.page_width = Cm(width)
    section.page_height = Cm(height)
    margins = p.get("margins") or {}
    section.top_margin = Cm(_number(margins.get("top"), DEFAULT_MARGIN))
    section.bottom_margin = Cm(_number(margins.get("bottom"), DEFAULT_MARGIN))
    section.left_margin = Cm(_number(margins.get("left"), DEFAULT_MARGIN))
    section.right_margin = Cm(_number(margins.get("right"), DEFAULT_MARGIN))
    doc.styles["Normal"].font.size = Pt(_number(p.get("font_size"), DEFAULT_FONT_SIZE))


def _add_contacts(doc, d, L):
    """Contact line with the LANG translated labels; skips empty values."""
    pieces = []

    def add(label, value):
        value = _text(value)
        if value:
            pieces.append((label, value))

    add(L["phone"], d.get("phone"))
    add(L["email"], d.get("email"))
    add(L["address"], d.get("address"))
    add(L["school_name"], d.get("school_name"))
    add(L["profession"], d.get("profession"))
    socials = d.get("socials")
    if isinstance(socials, (list, tuple)):
        for x in socials:
            try:
                if not isinstance(x, dict):
                    continue
                value = _text(x.get("value"))
                if not value:
                    continue
                label = latex_gen.social_label(x.get("network"), x.get("label"), L)
            except Exception:
                continue
            pieces.append((label + ":", value))
    for x in d.get("extra_fields") or []:
        x = x or {}
        label = _text(x.get("label"))
        value = _text(x.get("value"))
        if label and value:
            pieces.append((label + ":", value))
    if not pieces:
        return
    paragraph = doc.add_paragraph()
    for i, (label, value) in enumerate(pieces):
        if i:
            paragraph.add_run("   |   ")
        run = paragraph.add_run(label + " ")
        run.bold = True
        paragraph.add_run(value)


def _add_photo(doc, d):
    """Insert the photo if it is a valid file; ignore any failure."""
    photo = _text(d.get("photo"))
    if not photo:
        return
    if os.path.splitext(photo)[1].lower() not in PHOTO_EXTS or not os.path.isfile(photo):
        return
    try:
        width = float(d.get("photo_width_cm") or DEFAULT_PHOTO_WIDTH)
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        paragraph.add_run().add_picture(photo, width=Cm(width))
    except Exception:
        # Any image failure is ignored: the export never breaks.
        pass


def _add_header(doc, d, L):
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(_text(d.get("name")))
    run.bold = True
    run.font.size = Pt(NAME_FONT_SIZE)
    profession = _text(d.get("profession"))
    if profession:
        doc.add_paragraph().add_run(profession).italic = True
    _add_contacts(doc, d, L)
    _add_photo(doc, d)


def _add_education_entry(doc, entry, L):
    degree_type = _text(option_label(entry.get("degree_type"), L.get("degree_type")))
    degree = _text(entry.get("degree"))
    label = " — ".join(x for x in (degree_type, degree) if x)
    _add_entry_title(doc, entry.get("start"), entry.get("end"), label)
    institution = _text(entry.get("institution"))
    if institution:
        doc.add_paragraph().add_run(institution).italic = True
    grade = _text(entry.get("grade"))
    if grade:
        paragraph = doc.add_paragraph()
        paragraph.add_run(_text(L["grade"]) + " ").bold = True
        paragraph.add_run(grade)


def _add_work_entry(doc, entry, L):
    _add_entry_title(doc, entry.get("start"), entry.get("end"), entry.get("position"))
    company = _text(entry.get("company"))
    if company:
        doc.add_paragraph().add_run(company).italic = True
    work_mode = _text(option_label(entry.get("work_mode"), L.get("work_mode")))
    if work_mode:
        doc.add_paragraph().add_run("(" + work_mode + ")")
    achievements = [x.strip() for x in str(entry.get("achievements") or "").splitlines() if x.strip()]
    for achievement in achievements:
        _add_bullet(doc, achievement)


def _add_project_entry(doc, entry, L, with_course):
    _add_entry_title(doc, entry.get("start"), entry.get("end"), entry.get("name"))
    organization = _text(entry.get("organization"))
    course = _text(entry.get("course")) if with_course else ""
    if organization or course:
        paragraph = doc.add_paragraph()
        if organization:
            paragraph.add_run(organization).italic = True
        if course:
            if organization:
                paragraph.add_run("   ")
            paragraph.add_run(course)
    _add_paragraphs(doc, entry.get("description"))
    result = _text(entry.get("result"))
    if result:
        paragraph = doc.add_paragraph()
        paragraph.add_run(_text(L["result"]) + " ").bold = True
        paragraph.add_run(result)
    link = _text(entry.get("link"))
    if link:
        paragraph = doc.add_paragraph()
        paragraph.add_run(_text(L["link"]) + " ").bold = True
        paragraph.add_run(link)


def _add_skills_section(doc, d, L, title=None, color=None):
    entries = [e for e in (d.get("skills") or []) if isinstance(e, dict)]
    rows = []
    for e in entries:
        category = _text(e.get("category"))
        values = [v.strip() for v in str(e.get("values") or "").split(",") if v.strip()]
        if category or values:
            rows.append((category, values))
    if not rows:
        return
    _add_heading(doc, title or L["skills"], color)
    for category, values in rows:
        paragraph = doc.add_paragraph()
        if category and values:
            paragraph.add_run(category + L["skill_separator"] + " ").bold = True
            paragraph.add_run(", ".join(values))
        elif category:
            paragraph.add_run(category).bold = True
        else:
            paragraph.add_run(", ".join(values))


def _add_pairs_section(doc, entries, L, key, field_a, field_b, title=None, color=None):
    rows = []
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        a = _text(e.get(field_a))
        b = _text(e.get(field_b))
        if a or b:
            rows.append((a, b))
    if not rows:
        return
    _add_heading(doc, title or L[key], color)
    for a, b in rows:
        paragraph = doc.add_paragraph()
        if a and b:
            paragraph.add_run(a).bold = True
            paragraph.add_run(" – " + b)
        elif a:
            paragraph.add_run(a).bold = True
        else:
            paragraph.add_run(b)


def _block_anchor(value):
    """Valid anchor or "end" for a block with a missing or unknown position."""
    anchor = _text(value)
    return anchor if anchor in BLOCK_ANCHORS else "end"


def _group_blocks(d):
    """Distribute free blocks by anchor; ignore anything that is not a dict."""
    groups = {anchor: [] for anchor in BLOCK_ANCHORS}
    entries = d.get("blocks")
    if not isinstance(entries, (list, tuple)):
        return groups
    for block in entries:
        if isinstance(block, dict):
            groups[_block_anchor(block.get("position"))].append(block)
    return groups


def _bottom_border(paragraph, color, thickness=6):
    """Add the lower border XML (w:pBdr) to the given paragraph."""
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(thickness))
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def _add_shading(paragraph, color):
    """Add the shading XML (w:shd) to the given paragraph."""
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    p_pr.append(shd)


def _line_separator(doc, color=None):
    """Thin separator: empty paragraph with a lower border in the accent color."""
    paragraph = doc.add_paragraph()
    _bottom_border(paragraph, _hex_from_color(color) or COLOR_ACCENT)
    return paragraph


def _band_separator(doc, color=None):
    """Wide separator: empty paragraph shaded with the accent color."""
    hex_color = _hex_from_color(color) or COLOR_ACCENT
    paragraph = doc.add_paragraph()
    _bottom_border(paragraph, hex_color, thickness=24)
    _add_shading(paragraph, hex_color)
    return paragraph


def _render_separator_block(doc, block, color=None):
    """A separator is always drawn; an unknown style falls back to "line"."""
    style = _text(block.get("style"))
    if style not in SEPARATOR_STYLES:
        style = "line"
    if style == "band":
        _band_separator(doc, color)
    elif style == "space":
        doc.add_paragraph()
    else:
        _line_separator(doc, color)


def _render_section_block(doc, block, color=None):
    """Bold title and content by lines; it is skipped only when all is empty."""
    title = _text(block.get("title"))
    if not title and not _text(block.get("content")):
        return
    if title:
        _add_heading(doc, title, color)
    _add_paragraphs(doc, block.get("content"))


def _render_list_block(doc, block, color=None):
    """Generic list: title/detail or period/description pairs.

    Block columns degrade to a single column (same as the rest of the
    sections with ``columns`` in the Word export).
    """
    mode = _text(block.get("mode"))
    if mode not in LIST_MODES:
        mode = "columns"
    title = _text(block.get("title"))
    entries = block.get("entries")
    rows = []
    for entry in entries if isinstance(entries, (list, tuple)) else []:
        if not isinstance(entry, dict):
            continue
        if mode == "period":
            period = _text(entry.get("period"))
            description = _text(entry.get("description"))
            if period or description:
                rows.append((period, description))
        else:
            heading = _text(entry.get("title"))
            detail = _text(entry.get("detail"))
            if heading or detail:
                rows.append((heading, detail))
    if not rows:
        return
    if title:
        _add_heading(doc, title, color)
    for a, b in rows:
        if mode == "period":
            if a:
                doc.add_paragraph().add_run(a).italic = True
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


def _render_blocks(doc, blocks, color=None):
    """Draw the blocks of one anchor in the same list order."""
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = _text(block.get("type"))
        if block_type == "separator":
            _render_separator_block(doc, block, color)
        elif block_type == "section":
            _render_section_block(doc, block, color)
        elif block_type == "list":
            _render_list_block(doc, block, color)


def _add_body(doc, d, L, color=None):
    """Sections with the same order, visibility and titles as latex_gen.

    The normalized order and the hidden sections are delegated to latex_gen
    (normalize_section_order / is_section_hidden) and the custom titles to
    custom_section_title, with L[key] as fallback. The text is plain,
    without LaTeX escaping. ``color`` (RGBColor) tints the headings; None
    leaves them with the default color.

    Free blocks are interleaved after their anchor section; the "start" and
    "end" anchors open and close the body. An empty or hidden section still
    shows the blocks anchored to it (positional anchor).
    """
    groups = _group_blocks(d)
    _render_blocks(doc, groups["start"], color)

    for key in latex_gen.normalize_section_order(d):
        if not latex_gen.is_section_hidden(d, key):
            title = latex_gen.custom_section_title(d, key) or L[key]
            if key == "summary":
                if _text(d.get("summary")):
                    _add_heading(doc, title, color)
                    _add_paragraphs(doc, d.get("summary"))
            elif key == "education":
                entries = _entries_with_content(d.get("education"))
                if entries:
                    _add_heading(doc, title, color)
                    for entry in entries:
                        _add_education_entry(doc, entry, L)
            elif key == "projects":
                entries = _entries_with_content(d.get("projects"))
                if entries:
                    _add_heading(doc, title, color)
                    for entry in entries:
                        _add_project_entry(doc, entry, L, False)
            elif key == "university_projects":
                entries = _entries_with_content(d.get("university_projects"))
                if entries:
                    _add_heading(doc, title, color)
                    for entry in entries:
                        _add_project_entry(doc, entry, L, True)
            elif key == "internships":
                entries = _entries_with_content(d.get("internships"))
                if entries:
                    _add_heading(doc, title, color)
                    for entry in entries:
                        _add_work_entry(doc, entry, L)
            elif key == "work":
                entries = _entries_with_content(d.get("work"))
                if entries:
                    _add_heading(doc, title, color)
                    for entry in entries:
                        _add_work_entry(doc, entry, L)
            elif key == "skills":
                _add_skills_section(doc, d, L, title, color)
            elif key == "languages":
                _add_pairs_section(doc, d.get("languages"), L, key, "language", "level", title, color)
            elif key == "references":
                _add_pairs_section(doc, d.get("references"), L, key, "name", "contact", title, color)
        # Block anchored to this section: it is emitted even if the section is
        # hidden or empty, to preserve the chosen positional anchor.
        _render_blocks(doc, groups[key], color)
    _render_blocks(doc, groups["end"], color)


def export(data, prefs_dict, path):
    """Export `data` to a DOCX file at `path`.

    `prefs_dict` uses the same keys as prefs.load(): paper, margins,
    font_size and colors (primary and text). Section columns degrade to a
    single column.
    """
    data = data or {}
    L = LANG.get(str(data.get("cv_language", "zh")), LANG["zh"])
    doc = Document()
    _configure_document(doc, prefs_dict or {})
    # text -> Normal style base color; primary -> separators and headings.
    text_color = _pref_color(prefs_dict, "text")
    if text_color is not None:
        doc.styles["Normal"].font.color.rgb = text_color
    _add_header(doc, data, L)
    _add_body(doc, data, L, _pref_color(prefs_dict, "primary"))
    doc.save(path)
