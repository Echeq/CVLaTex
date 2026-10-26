# -*- coding: utf-8 -*-
"""Per-template Word layout profiles.

Each LaTeX template has its own visual identity: a header shape, a section
heading treatment, entry columns, bullet style and separators. This module
freezes that identity as data so a later layout module can render a .docx that
mirrors the selected template.

Design rules for this module:

* it does **not** import ``latex_gen`` (no circular import and no LaTeX work),
* it stores **colour role names**, never RGB values: ``docx_gen._Palette``
  resolves ``accent``, ``accent2``, ``accent3``, ``gray``, ``text``,
  ``white``, ``black``, ``navy`` and ``purple`` to real colours later,
* every measure was copied from ``templates/<id>/*.tex`` and the matching
  ``latex_gen._header_*``/``_sidebar`` helper, not invented.

``heading_rule_specs`` is a tuple of ``(role, pt)`` pairs. A ``pt`` of ``0.0``
means a filled plate/bar without a hairline; its height lives in
``heading_plate_mm``. ``separators`` maps the four free-block separator styles
(``line``, ``band``, ``thick``, ``double``) to the same ``(role, pt)`` tuples.

``logo_ratio`` is the logo width over the photo width (the templates ship a
2.4cm logo above a 4.0cm photo, hence 0.60). ``photo_ratio`` is the image
column as a fraction of the header width. ``line_spacing`` is the Word body
multiplier that approximates the LaTeX article leading.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateProfile:
    """Frozen layout vocabulary for one LaTeX template."""

    template: str = "classic"
    header_kind: str = "lines"
    name_role: str = "accent"
    name_pt: float = 17.0
    name_caps: bool = False
    name_bold: bool = True
    name_align: str = "left"
    band: bool = False
    band_role: str = "accent"
    band_width_ratio: float = 1.0
    band_height_pt: float = 0.0
    band_extra_cm: float = 0.0
    photo_ratio: float = 0.28
    photo_above_contacts: bool = False
    logo_ratio: float = 0.60
    contact_layout: str = "lines"
    heading_kind: str = "rule"
    heading_rule_specs: tuple = ()
    heading_title_pt: float = 15.0
    heading_plate_mm: float = 0.0
    entry_kind: str = "classic"
    entry_columns: tuple = None
    columns_supported: bool = False
    bullet_kind: str = "dot"
    rule_roles: tuple = ()
    font_family: str = "serif"
    parskip_pt: float = 4.0
    line_spacing: float = 1.15
    page_frame: bool = False
    page_frame_role_size: tuple = ()
    separators: dict = field(default_factory=dict)
    # Sidebar geometry (0.0 for every other template).
    sidebar_bar_cm: float = 0.0
    sidebar_inner_cm: float = 0.0
    body_left_cm: float = 0.0


def _separators(line, band=None, thick=None, double=None):
    """Build the four-key separator mapping, defaulting missing styles."""
    band = band if band is not None else line
    thick = thick if thick is not None else band
    double = double if double is not None else line
    return {"line": line, "band": band, "thick": thick, "double": double}


PROFILES = {
    # Accent underline name, left logo/photo, hairline section rules.
    "classic": TemplateProfile(
        template="classic",
        header_kind="lines",
        name_role="text",
        name_pt=17.0,
        name_caps=False,
        name_bold=True,
        name_align="left",
        band=False,
        photo_ratio=0.28,
        photo_above_contacts=False,
        contact_layout="lines",
        heading_kind="rule",
        heading_rule_specs=(("accent", 0.7),),
        heading_title_pt=15.0,
        entry_kind="classic",
        entry_columns=None,
        columns_supported=True,
        bullet_kind="dot",
        rule_roles=("accent", "gray"),
        font_family="serif",
        parskip_pt=4.0,
        line_spacing=1.15,
        separators=_separators(
            (("accent", 0.6),), (("accent", 3.5),), (("accent", 3.5),),
            (("accent", 0.6),),
        ),
    ),
    # Centred academic header, small caps name, gray double rule.
    "harvard": TemplateProfile(
        template="harvard",
        header_kind="centered",
        name_role="text",
        name_pt=17.0,
        name_caps=True,
        name_bold=True,
        name_align="center",
        band=False,
        photo_ratio=0.28,
        photo_above_contacts=False,
        contact_layout="lines",
        heading_kind="rule",
        heading_rule_specs=(("gray", 0.4),),
        heading_title_pt=14.4,
        entry_kind="classic",
        entry_columns=None,
        columns_supported=True,
        bullet_kind="dot",
        rule_roles=("text", "gray"),
        font_family="serif",
        parskip_pt=4.0,
        line_spacing=1.15,
        separators=_separators(
            (("accent", 0.6),), (("accent", 3.5),), (("accent", 3.5),),
            (("gray", 0.5), ("gray", 0.25)),
        ),
    ),
    # Big accent name and a heavy 2.5pt header rule.
    "modern": TemplateProfile(
        template="modern",
        header_kind="accent_rule",
        name_role="accent",
        name_pt=24.0,
        name_caps=False,
        name_bold=True,
        name_align="left",
        band=False,
        photo_ratio=0.26,
        photo_above_contacts=False,
        contact_layout="lines",
        heading_kind="rule",
        heading_rule_specs=(("accent", 1.6),),
        heading_title_pt=14.4,
        entry_kind="classic",
        entry_columns=None,
        columns_supported=True,
        bullet_kind="dot",
        rule_roles=("accent", "gray"),
        font_family="serif",
        parskip_pt=4.0,
        line_spacing=1.15,
        separators=_separators(
            (("accent", 0.6),), (("accent", 3.5),), (("accent", 3.5),),
            (("accent", 0.6),),
        ),
    ),
    # Full-width accent band above contacts/photo, two-tone section rules.
    "creative": TemplateProfile(
        template="creative",
        header_kind="band",
        name_role="white",
        name_pt=24.0,
        name_caps=False,
        name_bold=True,
        name_align="left",
        band=True,
        band_role="accent",
        band_width_ratio=1.0,
        band_height_pt=0.0,
        photo_ratio=0.28,
        photo_above_contacts=False,
        contact_layout="lines",
        heading_kind="double_rule",
        heading_rule_specs=(("accent2", 0.9), ("accent3", 1.8)),
        heading_title_pt=14.4,
        entry_kind="classic",
        entry_columns=None,
        columns_supported=True,
        bullet_kind="dot",
        rule_roles=("accent", "accent2", "accent3", "gray"),
        font_family="serif",
        parskip_pt=4.0,
        line_spacing=1.15,
        separators=_separators(
            (("accent", 0.6),), (("accent", 3.5),), (("accent", 3.5),),
            (("accent", 0.6), ("accent2", 0.4)),
        ),
    ),
    # 1.6cm accent plate behind a 22pt name, plate+tail section heads.
    "chinese": TemplateProfile(
        template="chinese",
        header_kind="plate_band",
        name_role="white",
        name_pt=22.0,
        name_caps=False,
        name_bold=True,
        name_align="left",
        band=True,
        band_role="accent",
        band_width_ratio=0.70,
        band_height_pt=45.35,
        photo_ratio=0.28,
        photo_above_contacts=False,
        contact_layout="lines",
        heading_kind="plate_tail",
        heading_rule_specs=(("accent", 0.0), ("accent2", 0.0)),
        heading_title_pt=17.0,
        heading_plate_mm=7.5,
        entry_kind="compact3",
        entry_columns=(0.24, 0.46, 0.26),
        columns_supported=False,
        bullet_kind="square_navy",
        rule_roles=("accent", "accent2", "gray"),
        font_family="serif",
        parskip_pt=3.0,
        line_spacing=1.15,
        separators=_separators(
            (("accent", 0.6),), (("accent", 3.5),), (("accent", 3.5),),
            (("accent", 0.6),),
        ),
    ),
    # Full-height 6.2cm accent side bar on page 1; body starts at 7cm.
    "sidebar": TemplateProfile(
        template="sidebar",
        header_kind="sidebar",
        name_role="accent",
        name_pt=24.0,
        name_caps=False,
        name_bold=True,
        name_align="left",
        band=False,
        photo_ratio=0.28,
        photo_above_contacts=True,
        contact_layout="lines",
        heading_kind="rule",
        heading_rule_specs=(("accent", 0.7),),
        heading_title_pt=15.0,
        entry_kind="classic",
        entry_columns=None,
        columns_supported=True,
        bullet_kind="dot",
        rule_roles=("accent", "gray"),
        font_family="serif",
        parskip_pt=4.0,
        line_spacing=1.15,
        separators=_separators(
            (("accent", 0.6),), (("accent", 3.5),), (("accent", 3.5),),
            (("accent", 0.6),),
        ),
        sidebar_bar_cm=6.2,
        sidebar_inner_cm=4.6,
        body_left_cm=7.0,
    ),
    # Sidebar mirrored to the right margin.
    "sidebar-right": TemplateProfile(
        template="sidebar-right",
        header_kind="sidebar_right",
        name_role="accent",
        name_pt=24.0,
        name_caps=False,
        name_bold=True,
        name_align="left",
        band=False,
        photo_ratio=0.28,
        photo_above_contacts=True,
        contact_layout="lines",
        heading_kind="rule",
        heading_rule_specs=(("accent", 0.7),),
        heading_title_pt=15.0,
        entry_kind="classic",
        entry_columns=None,
        columns_supported=True,
        bullet_kind="dot",
        rule_roles=("accent", "gray"),
        font_family="serif",
        parskip_pt=4.0,
        line_spacing=1.15,
        separators=_separators(
            (("accent", 0.6),), (("accent", 3.5),), (("accent", 3.5),),
            (("accent", 0.6),),
        ),
        sidebar_bar_cm=6.2,
        sidebar_inner_cm=4.6,
        body_left_cm=7.0,
    ),
    # Black tabs, heavy page frame, tabbed section heads.
    "tabbed": TemplateProfile(
        template="tabbed",
        header_kind="tabbed",
        name_role="text",
        name_pt=26.0,
        name_caps=False,
        name_bold=True,
        name_align="left",
        band=False,
        photo_ratio=0.26,
        photo_above_contacts=False,
        contact_layout="two_col_0_48",
        heading_kind="tab",
        heading_rule_specs=(("accent", 0.0), ("accent2", 0.8)),
        heading_title_pt=13.0,
        heading_plate_mm=7.2,
        entry_kind="compact3",
        entry_columns=(0.24, 0.46, 0.26),
        columns_supported=False,
        bullet_kind="square_black",
        rule_roles=("accent", "accent2", "gray"),
        font_family="serif",
        parskip_pt=3.0,
        line_spacing=1.15,
        page_frame=True,
        page_frame_role_size=("text", 1.8, 0.62),
        separators=_separators(
            (("accent", 0.6),), (("accent", 3.2),), (("accent", 3.2),),
            (("accent", 0.6),),
        ),
    ),
    # Blue ribbon with the photo inside the band and gold-trimmed bars.
    "ribbon": TemplateProfile(
        template="ribbon",
        header_kind="band_photo",
        name_role="white",
        name_pt=24.0,
        name_caps=False,
        name_bold=True,
        name_align="left",
        band=True,
        band_role="accent",
        band_width_ratio=1.0,
        band_height_pt=0.0,
        photo_ratio=0.26,
        photo_above_contacts=True,
        contact_layout="lines",
        heading_kind="bar_tick",
        heading_rule_specs=(("accent", 0.0), ("accent2", 1.2)),
        heading_title_pt=13.0,
        heading_plate_mm=0.0,
        entry_kind="compact3",
        entry_columns=(0.24, 0.46, 0.26),
        columns_supported=False,
        bullet_kind="square_navy",
        rule_roles=("accent", "accent2", "gray"),
        font_family="serif",
        parskip_pt=3.0,
        line_spacing=1.15,
        separators=_separators(
            (("accent", 0.7), ("accent2", 0.4)),
            (("accent", 3.0), ("accent2", 0.9)),
            (("accent", 3.0), ("accent2", 0.9)),
            (("accent", 0.7), ("accent2", 0.4)),
        ),
    ),
    # Minimal navy: name, contacts, two thin rules, no filled bands.
    "navy": TemplateProfile(
        template="navy",
        header_kind="minimal",
        name_role="accent",
        name_pt=24.0,
        name_caps=False,
        name_bold=True,
        name_align="left",
        band=False,
        photo_ratio=0.26,
        photo_above_contacts=False,
        contact_layout="lines",
        heading_kind="double_rule",
        heading_rule_specs=(("accent", 0.6), ("accent2", 0.3)),
        heading_title_pt=13.0,
        entry_kind="compact3",
        entry_columns=(0.22, 0.40, 0.34),
        columns_supported=False,
        bullet_kind="square_navy",
        rule_roles=("accent", "accent2", "gray"),
        font_family="serif",
        parskip_pt=3.0,
        line_spacing=1.15,
        separators=_separators(
            (("accent", 0.6),),
            (("accent", 0.6), ("accent2", 0.4)),
            (("accent", 0.6), ("accent2", 0.4)),
            (("accent", 0.6), ("accent2", 0.3)),
        ),
    ),
    # Round badge + coral diamond, sans family, diamond bullets.
    "playful": TemplateProfile(
        template="playful",
        header_kind="playful",
        name_role="accent",
        name_pt=26.0,
        name_caps=False,
        name_bold=True,
        name_align="left",
        band=False,
        photo_ratio=0.26,
        photo_above_contacts=False,
        contact_layout="badges",
        heading_kind="badge",
        heading_rule_specs=(("accent", 1.2), ("accent2", 0.5)),
        heading_title_pt=13.5,
        entry_kind="compact3",
        entry_columns=(0.20, 0.40, 0.37),
        columns_supported=False,
        bullet_kind="diamond_coral",
        rule_roles=("accent", "accent2", "gray"),
        font_family="sans",
        parskip_pt=3.0,
        line_spacing=1.15,
        separators=_separators(
            (("accent", 0.6),),
            (("accent", 2.0), ("accent2", 0.5)),
            (("accent", 2.0), ("accent2", 0.5)),
            (("accent", 1.2), ("accent2", 0.5)),
        ),
    ),
    # Navy banner with a stepped blade tip, navy plates over gray bars.
    "sword": TemplateProfile(
        template="sword",
        header_kind="banner",
        name_role="white",
        name_pt=20.0,
        name_caps=False,
        name_bold=True,
        name_align="left",
        band=True,
        band_role="accent",
        band_width_ratio=0.64,
        band_height_pt=36.85,
        band_extra_cm=1.4,
        photo_ratio=0.26,
        photo_above_contacts=False,
        contact_layout="grid_0_47",
        heading_kind="stair_blade",
        heading_rule_specs=(("accent2", 0.0), ("accent", 0.0)),
        heading_title_pt=13.0,
        heading_plate_mm=7.2,
        entry_kind="compact3",
        entry_columns=(0.24, 0.46, 0.26),
        columns_supported=False,
        bullet_kind="square_navy",
        rule_roles=("accent", "accent2", "gray"),
        font_family="serif",
        parskip_pt=3.0,
        line_spacing=1.15,
        separators=_separators(
            (("accent", 0.6),), (("accent", 3.2),), (("accent", 3.2),),
            (("accent", 0.6),),
        ),
    ),
}

#: Template ids covered by the profile table.
PROFILE_IDS = tuple(PROFILES)


def profile_for(template_id):
    """Profile of ``template_id``; unknown, empty or hostile ids -> classic.

    It accepts the hyphenated canonical ids and the underscore variant used by
    some callers (``sidebar_right``), and it never raises.
    """
    try:
        key = str(template_id).strip().lower()
    except Exception:
        key = ""
    profile = PROFILES.get(key)
    if profile is None:
        profile = PROFILES.get(key.replace("_", "-"))
    return profile if profile is not None else PROFILES["classic"]
