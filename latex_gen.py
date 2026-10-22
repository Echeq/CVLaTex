import os
import re
import sys

import tex_datos

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

TEMPLATES = ("classic", "harvard", "modern", "creative", "chinese", "sidebar", "sidebar-right", "tabbed", "ribbon", "navy", "playful")
TEMPLATE_FILES = {
    "classic": "classic/plantilla.tex",
    "harvard": "harvard/harvard.tex",
    "modern": "modern/moderno.tex",
    "creative": "creative/creativo.tex",
    "chinese": "chinese/chino.tex",
    "sidebar": "sidebar/sidebar.tex",
    "sidebar-right": "sidebar-right/sidebar-right.tex",
    "tabbed": "tabbed/tabbed.tex",
    "ribbon": "ribbon/ribbon.tex",
    "navy": "navy/navy.tex",
    "playful": "playful/playful.tex",
}
# Templates that reuse the three-column Chinese renderers (date/title/org)
# and the shared \cvcnline macro.
CHINESE_STYLE_TEMPLATES = ("chinese", "tabbed", "ribbon", "navy", "playful")

_SPECIALS = re.compile(r"([\\{}$&#_%~^])")
_LATEX_ESCAPES = {
    "\\": "\\\\",
    "{": "\\{",
    "}": "\\}",
    "$": "\\$",
    "&": "\\&",
    "#": "\\#",
    "_": "\\_",
    "%": "\\%",
    "~": "\\textasciitilde{}",
    "^": "\\textasciicircum{}",
}
LOGO_EXTS = {".jpg", ".jpeg", ".png"}
# Width fractions for 1-3 column layouts.
COLUMN_WIDTHS = {1: "1.0", 2: "0.48", 3: "0.31"}

# Default order of the standard CV body sections.
DEFAULT_SECTION_ORDER = (
    "summary", "education", "projects", "university_projects", "internships",
    "work", "skills", "languages", "references",
)

# Free blocks the user interleaves between CV sections.
# The anchor is the section after which the block is inserted; "start" goes
# before everything and "end" after everything.
BLOCK_ANCHORS = (
    "start", "summary", "education", "projects", "university_projects",
    "internships", "work", "skills", "languages", "references", "end",
)
BLOCK_TYPES = ("separator", "section", "list")
SEPARATOR_STYLES = ("line", "band", "space")
# Generic templates for the "list" block: title+detail pairs laid out in
# 1-3 columns, or a period + description line (timeline).
LIST_MODES = ("columns", "period")

# zh font_engine: fontspec fallback chains, resolved at compile time with
# \IfFontExistsTF. Main/sans candidates cover Windows (Microsoft YaHei),
# macOS (PingFang SC) and common Linux CJK fonts; the mono chain covers
# Windows, macOS and Linux. The last candidate is applied unconditionally.
CJK_MAIN_FONTS = (
    "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC",
    "WenQuanYi Zen Hei", "Source Han Sans SC",
)
CJK_MONO_FONTS = ("Consolas", "Menlo", "DejaVu Sans Mono", "Noto Sans Mono")

# Dynamic social entries of the header (`data["socials"]`): canonical network
# keys. Any other value falls back to "other" during migration/sanitizing.
SOCIAL_NETWORKS = (
    "github", "linkedin", "x", "instagram", "facebook", "youtube",
    "tiktok", "telegram", "wechat", "website", "other",
)
# Proper nouns of the social networks: shown as-is, never translated.
_SOCIAL_NAMES = {
    "github": "GitHub",
    "linkedin": "LinkedIn",
    "x": "X",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "youtube": "YouTube",
    "tiktok": "TikTok",
    "telegram": "Telegram",
    "wechat": "WeChat",
}
_SEPARATOR_MACROS = {
    "line": "\\cvblockline",
    "band": "\\cvblockband",
    "space": "\\cvblockspace",
}

# Editable palette from prefs: prefs key -> \definecolor name of the template.
# "text" has no color of its own in the templates and is injected.
_COLOR_MAP = {"primary": "accent", "secondary": "acento2", "gray": "gris"}
_TEMPLATE_COLORS = ("accent", "acento2", "acento3", "gris")
_RE_DEFINE_COLOR = re.compile(
    r"\\definecolor\s*\{\s*([A-Za-z0-9_]+)\s*\}\s*\{\s*RGB\s*\}\s*"
    r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}"
)

LANG = {
    "zh": {
        "title": "个人简历 PERSONAL RESUME",
        "birth_date": "出生年月：", "phone": "手机号码：", "nationality": "国籍：",
        "address": "地址：",
        "email": "邮箱：", "school_name": "毕业院校：", "profession": "意向岗位：",
        "education": "教育背景", "projects": "项目经历",
        "university_projects": "校内项目",
        "internships": "实习经历", "work": "工作经历", "skills": "技能特长",
        "languages": "语言能力", "references": "推荐人", "summary": "个人简介",
        "grade": "成绩：", "result": "成果：",
        "website": "网站", "link": "链接",
        "skill_separator": "：",
        "work_mode": {"onsite": "现场", "hybrid": "混合", "remote": "远程"},
        "degree_type": {
            "primary": "小学", "secondary": "初中", "high_school": "高中",
            "vocational_mid": "中专", "vocational_high": "大专",
            "bachelor": "本科", "engineering": "工科", "licentiate": "学士",
            "diploma": "专科", "architecture": "建筑学", "master": "硕士",
            "phd": "博士", "postgraduate": "进修", "course": "培训",
            "other": "其他",
        },
    },
    "es": {
        "title": "CURRÍCULUM",
        "birth_date": "Nacimiento:", "phone": "Teléfono:", "nationality": "Nacionalidad:",
        "address": "Dirección:",
        "email": "Correo:", "school_name": "Institución de egreso:", "profession": "Puesto deseado:",
        "education": "Educación", "projects": "Proyectos",
        "university_projects": "Proyectos universitarios",
        "internships": "Pasantías", "work": "Experiencia laboral", "skills": "Habilidades",
        "languages": "Idiomas", "references": "Referencias", "summary": "Perfil",
        "grade": "Nota:", "result": "Resultado:",
        "website": "Web", "link": "Enlace",
        "skill_separator": ":",
        "work_mode": {"onsite": "Presencial", "hybrid": "Híbrido", "remote": "Remoto"},
        "degree_type": {
            "primary": "Primaria", "secondary": "Secundaria (ESO)",
            "high_school": "Bachillerato", "vocational_mid": "FP Grado Medio",
            "vocational_high": "FP Grado Superior", "bachelor": "Grado Universitario",
            "engineering": "Ingeniería", "licentiate": "Licenciatura",
            "diploma": "Diplomatura", "architecture": "Arquitectura",
            "master": "Máster", "phd": "Doctorado (PhD)",
            "postgraduate": "Posgrado / Especialización",
            "course": "Curso / Certificación", "other": "Otro",
        },
    },
    "en": {
        "title": "PERSONAL RESUME",
        "birth_date": "Date of birth:", "phone": "Phone:", "nationality": "Nationality:",
        "address": "Address:",
        "email": "Email:", "school_name": "Graduated from:", "profession": "Desired role:",
        "education": "Education", "projects": "Projects",
        "university_projects": "University projects",
        "internships": "Internships", "work": "Work experience", "skills": "Skills",
        "languages": "Languages", "references": "References", "summary": "Profile",
        "grade": "Grade:", "result": "Result:",
        "website": "Website", "link": "Link",
        "skill_separator": ":",
        "work_mode": {"onsite": "On-site", "hybrid": "Hybrid", "remote": "Remote"},
        "degree_type": {
            "primary": "Primary", "secondary": "Secondary", "high_school": "High school",
            "vocational_mid": "Vocational (intermediate)",
            "vocational_high": "Vocational (advanced)",
            "bachelor": "Bachelor's degree", "engineering": "Engineering",
            "licentiate": "Licentiate", "diploma": "Diploma",
            "architecture": "Architecture", "master": "Master's degree",
            "phd": "Doctorate (PhD)",
            "postgraduate": "Postgraduate / Specialization",
            "course": "Course / Certification", "other": "Other",
        },
    },
}


def option_label(value, labels):
    """Label in the document language for a canonical select value.

    Canonical values (e.g. work_mode "remote", degree_type "master") are
    mapped through the LANG tables; an unknown or empty value passes through
    as free text so a CV written before the migration keeps showing what the
    user typed. Never raises.
    """
    try:
        text = "" if value is None else str(value).strip()
    except Exception:
        return ""
    if not text:
        return ""
    if isinstance(labels, dict):
        label = labels.get(text)
        if isinstance(label, str) and label:
            return label
    return text


def _escape(text):
    return _SPECIALS.sub(lambda m: _LATEX_ESCAPES[m.group(1)], text)


def esc(text):
    if not text:
        return ""
    return " ".join(_split_word(word) for word in str(text).split(" "))


def _split_word(word):
    # Chunks are cut on the UNESCAPED text so a cut never splits a macro
    # produced by _escape (e.g. \textasciitilde{}).
    chunks = [word[i:i + 18] for i in range(0, len(word), 18)]
    return "\\allowbreak ".join(_escape(chunk) for chunk in chunks)


def empty_data():
    return {
        "cv_language": "zh",
        "template": "classic",
        "name": "", "profession": "", "email": "", "phone": "",
        "address": "",
        "socials": [],
        "extra_fields": [],
        "photo": "", "photo_original": "", "photo_crop": None,
        "photo_width_cm": 4.0, "photo_height_cm": 5.0,
        "school_name": "", "school_logo": "",
        "school_logo_width_cm": 2.4, "school_logo_height_cm": 0.85,
        "summary": "",
        "work": [],
        "internships": [],
        "projects": [],
        "university_projects": [],
        "education": [],
        "skills": [],
        "languages": [],
        "references": [],
        "blocks": [],
        "section_titles": {},
        "hidden_sections": [],
        "section_order": [],
        "columns": {"work": 1, "internships": 1, "projects": 1, "university_projects": 1, "education": 1},
    }


def extra_logos(data):
    extra = {}
    for key in ("work", "internships", "education", "university_projects"):
        for i, entry in enumerate(data.get(key) or []):
            logo = (entry or {}).get("logo")
            if logo and os.path.isfile(logo):
                ext = os.path.splitext(logo)[1].lower()
                if ext in LOGO_EXTS:
                    extra[f"logo_{key}_{i}{ext}"] = logo
    logo = data.get("school_logo")
    if logo and os.path.isfile(logo):
        ext = os.path.splitext(logo)[1].lower()
        if ext in LOGO_EXTS:
            extra[f"logo_egresado{ext}"] = logo
    return extra


def _logo_ref(key, i, entry):
    logo = (entry or {}).get("logo")
    if not logo or not os.path.isfile(logo):
        return None
    ext = os.path.splitext(logo)[1].lower()
    if ext not in LOGO_EXTS:
        return None
    return f"logo_{key}_{i}{ext}"


def _with_logo(key, i, entry, content):
    ref = _logo_ref(key, i, entry)
    if not ref:
        return content
    return (
        "\\begin{minipage}[t]{1.15cm}\n"
        f"  \\includegraphics[width=\\linewidth,height=1.05cm,keepaspectratio]{{{ref}}}\n"
        "\\end{minipage}%\n"
        "\\begin{minipage}[t]{\\dimexpr\\linewidth-1.3cm\\relax}\n"
        f"{content}"
        "\\end{minipage}\n"
    )


def _box(width, content):
    return (
        f"\\begin{{minipage}}[t]{{{width}\\linewidth}}\n"
        "\\raggedright\n"
        f"{content}"
        "\\end{minipage}"
    )


def _date_range(start, end):
    if start and end:
        return f"{esc(start)} -- {esc(end)}"
    return esc(start) or esc(end)


def _itemize(lines):
    items = "\n".join(f"\\item {l}" for l in lines)
    return (
        "\\begin{itemize}\\setlength{\\itemsep}{1pt}\\setlength{\\parskip}{0pt}\\raggedright\n"
        f"{items}\n"
        "\\end{itemize}\n"
    )


def _paragraphs(text):
    lines = [x.strip() for x in str(text).splitlines() if x.strip()]
    if not lines:
        return ""
    return "\\par\n".join(esc(x) for x in lines) + "\n"


def _section(title, content):
    if not content.strip():
        return ""
    return f"\\cvsection{{{title}}}\n{content}\n"


def _date_title_line(title, start, end):
    date = _date_range(start, end)
    if date and title:
        return f"\\noindent{{\\itshape {date}}} \\hfill {{\\bfseries {title}}}"
    if date:
        return f"\\noindent{{\\itshape {date}}}"
    if title:
        return f"\\noindent{{\\bfseries {title}}}"
    return ""


def _as_text(value):
    """str(value) without surrounding spaces; None or hostile -> "" (never raises)."""
    try:
        return "" if value is None else str(value).strip()
    except Exception:
        return ""


def _lang_text(L, key):
    """Value of a LANG key tolerating a missing/invalid table; English default."""
    try:
        value = L.get(key) if isinstance(L, dict) else None
    except Exception:
        value = None
    if isinstance(value, str) and value.strip():
        return value
    return LANG["en"].get(key) or ""


def social_label(network, label, L=None):
    """Display name of a ``socials`` entry.

    GitHub/LinkedIn/X/... are proper nouns and are never translated; the
    canonical ``website`` and the ``other`` fallback (custom label, else the
    generic "link") come from the document LANG table. An unknown network is
    treated like ``other``; never raises.
    """
    key = _as_text(network)
    if key in _SOCIAL_NAMES:
        return _SOCIAL_NAMES[key]
    text = _as_text(label)
    if key == "website":
        return _lang_text(L, "website")
    return text or _lang_text(L, "link")


def _socials(d):
    """The socials list of the data, or [] for a missing/hostile value."""
    value = d.get("socials")
    if not isinstance(value, (list, tuple)):
        return []
    return value


def _contacts(d, L):
    lines = []

    def add(label, value, mono=False):
        if not value or not str(value).strip():
            return
        v = str(value).strip()
        text = f"\\texttt{{{esc(v)}}}" if mono else esc(v)
        lines.append(f"\\textbf{{{label}}} {text}")

    add(L["phone"], d.get("phone"), mono=True)
    add(L["email"], d.get("email"), mono=True)
    add(L["address"], d.get("address"))
    add(L["school_name"], d.get("school_name"))
    add(L["profession"], d.get("profession"))
    for entry in _socials(d):
        try:
            if not isinstance(entry, dict):
                continue
            value = _as_text(entry.get("value"))
            if not value:
                continue
            label = social_label(entry.get("network"), entry.get("label"), L)
        except Exception:
            continue
        lines.append(f"\\textbf{{{esc(label)}:}} \\texttt{{{esc(value)}}}")
    for x in d.get("extra_fields") or []:
        x = x or {}
        label = str(x.get("label", "")).strip()
        value = str(x.get("value", "")).strip()
        if label and value:
            lines.append(f"\\textbf{{{esc(label)}:}} {esc(value)}")
    if not lines:
        return ""
    return "{\\small\n" + " \\\\\n".join(lines) + "\n\\par}"


def _image_info(d):
    logo_ref = None
    logo = d.get("school_logo")
    if logo and os.path.isfile(logo):
        ext = os.path.splitext(logo)[1].lower()
        if ext in LOGO_EXTS:
            logo_ref = f"logo_egresado{ext}"

    photo = d.get("photo")
    photo_ext = os.path.splitext(photo)[1].lower() if photo else ""
    has_photo = bool(photo and os.path.exists(photo) and photo_ext in LOGO_EXTS)
    return logo_ref, has_photo, photo_ext


def _image_parts(d, logo_ref, has_photo, photo_ext):
    parts = []
    if logo_ref:
        try:
            lw = float(d.get("school_logo_width_cm") or 2.4)
            lh = float(d.get("school_logo_height_cm") or 0.85)
        except (TypeError, ValueError):
            lw, lh = 2.4, 0.85
        lw = min(max(lw, 0.5), 6.0)
        lh = min(max(lh, 0.3), 4.0)
        parts.append(
            f"\\noindent\\includegraphics[width={lw:g}cm,height={lh:g}cm,keepaspectratio]{{{logo_ref}}}\n"
        )
    if has_photo:
        try:
            width = float(d.get("photo_width_cm") or 4.0)
            height = float(d.get("photo_height_cm") or 5.0)
        except (TypeError, ValueError):
            width, height = 4.0, 5.0
        width = min(max(width, 1.0), 12.0)
        height = min(max(height, 1.0), 15.0)
        if logo_ref:
            parts.append("\\vspace{0.15em}\n")
        parts.append(
            "{\\setlength{\\fboxsep}{3pt}\n"
            f"\\fcolorbox{{gris}}{{white}}{{\\includegraphics[width={width:g}cm,height={height:g}cm,keepaspectratio]{{foto{photo_ext}}}}}\n"
            "}\n"
        )
    return parts


def _header_classic(d, L, parts):
    title = f"{{\\small\\bfseries\\color{{gris}} {L['title']}}}\n"
    name = f"{{\\LARGE\\bfseries {esc(d.get('name', ''))}}}"
    contact = _contacts(d, L)

    right_col = ""
    if parts:
        right_col = (
            "\\begin{minipage}[t]{0.28\\textwidth}\n"
            "\\raggedleft\n"
            "\\vspace{0.5em}\n"
            + "".join(parts)
            + "\\end{minipage}\n"
        )

    if right_col:
        row = (
            "\\noindent\n"
            "\\begin{minipage}[t]{0.7\\textwidth}\n"
            f"  {title}\\par\n"
            "  \\vspace{0.15em}\n"
            f"  {name}\\par\n"
            "  \\vspace{0.4em}\n"
            f"  {contact}\n"
            "\\end{minipage}%\n"
            f"\\hfill\n{right_col}"
        )
    else:
        row = (
            "\\noindent\n"
            f"  {title}\\par\n"
            "  \\vspace{0.15em}\n"
            f"  {name}\\par\n"
            "  \\vspace{0.4em}\n"
            f"  {contact}\n"
        )
    return row + "\n\\vspace{0.3em}\n{\\color{accent}\\hrule height 0.8pt}\n"


def _header_harvard(d, L, parts):
    lines = [
        "\\begin{center}\n",
        f"  {{\\small\\bfseries\\color{{gris}} {L['title']}}}\\par\n",
        "  \\vspace{0.45em}\n",
        f"  {{\\LARGE\\scshape {esc(d.get('name', ''))}}}\\par\n",
    ]
    contact = _contacts(d, L)
    if contact:
        lines.append("  \\vspace{0.4em}\n")
        lines.append("  " + contact.replace("\n", "\n  ") + "\n")
    if parts:
        lines.append("  \\vspace{0.5em}\n")
        lines.extend("  " + p for p in parts)
    lines.append("\\end{center}\n")
    lines.append("\\vspace{0.15em}\n{\\color{gris}\\hrule height 0.5pt}\n")
    lines.append("\\vspace{0.25em}\n{\\color{gris}\\hrule height 0.25pt}\n")
    return "".join(lines)


def _header_modern(d, L, parts):
    title = f"{{\\small\\bfseries\\color{{gris}} {L['title']}}}\n"
    name = f"{{\\Huge\\bfseries\\color{{accent}} {esc(d.get('name', ''))}}}"
    contact = _contacts(d, L)

    if parts:
        row = (
            "\\noindent\n"
            "\\begin{minipage}[t]{0.7\\textwidth}\n"
            f"  {title}"
            "  \\par\n"
            "  \\vspace{0.2em}\n"
            f"  {name}\\par\n"
            "  \\vspace{0.4em}\n"
            f"  {contact}\n"
            "\\end{minipage}%\n"
            "\\hfill\n"
            "\\begin{minipage}[t]{0.28\\textwidth}\n"
            "\\raggedleft\n"
            "\\vspace{0.4em}\n"
            + "".join(parts)
            + "\\end{minipage}\n"
        )
    else:
        row = (
            "\\noindent\n"
            f"  {title}"
            "  \\par\n"
            "  \\vspace{0.2em}\n"
            f"  {name}\\par\n"
            "  \\vspace{0.4em}\n"
            f"  {contact}\n"
        )
    return row + "\\vspace{0.4em}\n{\\color{accent}\\hrule height 2.5pt}\n"


def _header_creative(d, L, parts):
    band = (
        "\\noindent\\colorbox{accent}{%\n"
        "\\begin{minipage}{\\dimexpr\\textwidth-2\\fboxsep\\relax}\n"
        "\\vspace{0.55em}\n"
        f"{{\\color{{white}}\\Huge\\bfseries {esc(d.get('name', ''))}}}\\par\n"
        "\\vspace{0.3em}\n"
        f"{{\\color{{white}}\\small\\bfseries {L['title']}}}\\par\n"
        "\\vspace{0.55em}\n"
        "\\end{minipage}}\n"
    )
    contact = _contacts(d, L)
    if parts:
        blocks = (
            "\\vspace{0.6em}\n"
            "\\noindent\n"
            "\\begin{minipage}[t]{0.68\\textwidth}\n"
            f"{contact}\n"
            "\\end{minipage}%\n"
            "\\hfill\n"
            "\\begin{minipage}[t]{0.28\\textwidth}\n"
            "\\raggedleft\n"
            "\\vspace{0.3em}\n"
            + "".join(parts)
            + "\\end{minipage}\n"
        )
    elif contact:
        blocks = "\\vspace{0.6em}\n" + contact + "\n"
    else:
        blocks = ""
    return (
        band
        + blocks
        + "\\vspace{0.4em}\n"
        + "{\\color{accent}\\hrule height 1.2pt}\n"
        + "\\vspace{0.15em}\n"
        + "{\\color{gris}\\hrule height 0.4pt}\n"
    )


def _header_chinese(d, L, parts):
    band = (
        "\\noindent\\begingroup\\setlength{\\fboxsep}{0pt}%\n"
        "\\colorbox{accent}{%\n"
        "\\parbox[c][1.6cm][c]{\\linewidth}{%\n"
        "\\hspace{0.4em}{\\color{white}\\bfseries\\fontsize{22}{24}\\selectfont "
        + L["title"] +
        "}}}\n"
        "\\endgroup\\par\n"
    )
    name = esc(d.get("name", "")).strip()
    contact = _contacts(d, L)

    left_col = [band]
    if name:
        left_col.append("\\vspace{0.35em}\n")
        left_col.append(f"{{\\color{{accent}}\\fontsize{{18}}{{21}}\\selectfont {name}}}\\par\n")
    if contact:
        left_col.append("\\vspace{0.45em}\n" + contact + "\n")

    if parts:
        row = (
            "\\noindent\n"
            "\\begin{minipage}[t]{0.7\\textwidth}\n"
            + "".join(left_col)
            + "\\end{minipage}%\n"
            "\\hfill\n"
            "\\begin{minipage}[t]{0.28\\textwidth}\n"
            "\\raggedleft\n"
            "\\vspace{0.3em}\n"
            + "".join(parts)
            + "\\end{minipage}\n"
        )
    else:
        row = "".join(left_col)
    return row + "\\vspace{0.6em}\n{\\color{accent}\\hrule height 1.0pt}\n"


def _contact_lines(contact):
    """Lines of the block produced by ``_contacts`` ([] when it is empty).

    ``_contacts`` joins the entries with ``\\\\`` inside a ``{\\small ... \\par}``
    group; the new headers need the individual lines to place them in columns
    or behind a badge. Only that wrapper is stripped here, so every entry is
    carried over verbatim and the socials keep their exact labels.
    """
    if not contact or not contact.strip():
        return []
    body = contact.strip()
    prefix = "{\\small"
    if body.startswith(prefix):
        body = body[len(prefix):].lstrip("\n")
    if body.endswith("\\par}"):
        body = body[:-len("\\par}")].rstrip()
    return [line for line in body.split(" \\\\\n") if line.strip()]


def _contact_plain_width(line):
    """Approximate visible width of a contact line in 10pt em units.

    CJK glyphs are roughly twice as wide as the Latin average, so they weigh
    two units. Commands and grouping braces are not visible and are dropped.
    """
    text = re.sub(r"\\[A-Za-z]+\*?", "", line)
    text = text.replace("{", "").replace("}", "")
    return sum(2 if ord(char) > 0x2E80 else 1 for char in text)


def _contact_columns(contact):
    """Two balanced columns, or one column when long strings would break.

    Two 0.48 columns of the header's 0.7 text block hold about 30 Latin
    characters per line at 10pt, so anything longer (URLs, emails, long
    institution names) keeps the clean single-column block from ``_contacts``.
    """
    lines = _contact_lines(contact)
    if len(lines) < 2:
        return contact
    if max(_contact_plain_width(line) for line in lines) > 30:
        return contact
    columns = ([], [])
    for index, line in enumerate(lines):
        columns[index % 2].append(line)

    def column(items):
        return (
            "\\begin{minipage}[t]{0.48\\linewidth}\n"
            "\\raggedright\\small\n"
            + "\\\\\n".join(items)
            + "\n\\end{minipage}"
        )

    return column(columns[0]) + "%\n\\hfill\n" + column(columns[1]) + "\n"


def _badge_contacts(contact):
    """Contact lines prefixed with a small accent/acento2 diamond badge."""
    lines = _contact_lines(contact)
    if not lines:
        return ""
    badge = (
        "\\raisebox{-0.08em}{\\makebox[1.2em][c]{"
        "\\colorbox{accent}{\\color{acento2}\\rotatebox{45}{\\rule{0.34em}{0.34em}}}"
        "}}"
    )
    return (
        "{\\setlength{\\fboxsep}{1pt}\\small\n"
        + "\\\\\n".join(f"{badge}\\hspace{{0.5em}}{line}" for line in lines)
        + "\n\\par}"
    )


def _header_tabbed(d, L, parts):
    """Black-tab header: huge LANG title, name and two balanced contact columns.

    The photo/logo row keeps the content inside the text block; the heavy page
    frame belongs to the template. An empty ``parts`` list gives the left
    column the full width, so the header still looks intentional.
    """
    name = esc(d.get("name", "")).strip()
    contact = _contacts(d, L)
    # The huge LANG title stands on its own: the old 0.5em square was sized at
    # 11pt and sat on the baseline, reading as a stray period before the title
    # (the reference design has no marker).
    title = (
        "\\noindent"
        f"{{\\fontsize{{26}}{{30}}\\selectfont\\bfseries\\color{{accent}} {L['title']}}}\\par\n"
    )
    left = []
    if name:
        left.append(f"{{\\LARGE\\bfseries {name}}}\\par\n")
    if contact:
        left.append("\\vspace{0.45em}\n")
        left.append(_contact_columns(contact) + "\n")
    if parts:
        row = (
            "\\noindent\n"
            "\\begin{minipage}[t]{0.7\\textwidth}\n"
            "\\raggedright\n"
            + "".join(left)
            + "\\end{minipage}%\n"
            "\\hfill\n"
            "\\begin{minipage}[t]{0.26\\textwidth}\n"
            "\\raggedleft\n"
            "\\vspace{0.25em}\n"
            + "".join(parts)
            + "\\end{minipage}\n"
        )
    else:
        row = "\\noindent\n" + "".join(left)
    return (
        title
        + "\\vspace{0.2em}\n"
        + row
        + "\\vspace{0.55em}\n"
        + "{\\color{accent}\\hrule height 2.2pt}\n"
        + "\\vspace{0.12em}\n"
        + "{\\color{acento2}\\hrule height 0.6pt}\n"
    )


def _header_ribbon(d, L, parts):
    """Blue ribbon band with the LANG title as subtitle and a gold rule.

    The band is a zero-padding ``\\colorbox`` over the full text block, so a
    template band drawn behind the header lines up with it; the contacts stay
    on white below the gold ``acento2`` rule. Empty ``parts`` stretches the
    band's text column to the full width.
    """
    name = esc(d.get("name", "")).strip()
    contact = _contacts(d, L)
    band_left = (
        "\\vspace{0.45em}\n"
        f"{{\\color{{white}}\\small\\bfseries {L['title']}}}\\par\n"
        "\\vspace{0.15em}\n"
    )
    if name:
        band_left += (
            "{\\hyphenpenalty=10000\\exhyphenpenalty=10000"
            "\\color{white}\\fontsize{24}{28}\\selectfont\\bfseries "
            + name
            + "\\par}\n"
        )
    band_left += "\\vspace{0.45em}\n"
    if parts:
        # The band wraps a full-\linewidth minipage, so it always matches the
        # gold rule and the text block. The inner columns keep a 0.04 gap;
        # [c] keeps the title/name optically centred against a tall photo
        # (a [t] variant pushed all the leftover blue below the text instead).
        band = (
            "\\noindent\\begingroup\\setlength{\\fboxsep}{0pt}%\n"
            "\\colorbox{accent}{%\n"
            "\\begin{minipage}{\\linewidth}\n"
            "\\begin{minipage}[c]{0.7\\linewidth}\n"
            "\\raggedright\n"
            + band_left
            + "\\end{minipage}%\n"
            "\\hfill\n"
            "\\begin{minipage}[c]{0.26\\linewidth}\n"
            "\\raggedleft\n"
            + "".join(parts)
            + "\\end{minipage}%\n"
            "\\end{minipage}%\n"
            "}\n"
            "\\endgroup\\par\n"
        )
    else:
        band = (
            "\\noindent\\begingroup\\setlength{\\fboxsep}{0pt}%\n"
            "\\colorbox{accent}{%\n"
            "\\begin{minipage}[c]{\\linewidth}\n"
            "\\raggedright\n"
            + band_left
            + "\\end{minipage}%\n"
            "}\n"
            "\\endgroup\\par\n"
        )
    out = band + "\\vspace{0.2em}\n{\\color{acento2}\\hrule height 2.4pt}\n"
    if contact:
        out += "\\vspace{0.5em}\n" + contact + "\n"
    return out


def _header_navy(d, L, parts):
    """Navy minimal header: small LANG title above a large name and thin rules."""
    name = esc(d.get("name", "")).strip()
    contact = _contacts(d, L)
    left = [
        f"{{\\small\\bfseries\\color{{accent}} {L['title']}}}\\par\n",
        "\\vspace{0.12em}\n",
    ]
    if name:
        left.append(
            # Ragged right (set by the surrounding block) plus disabled
            # hyphenation: a long zh name must wrap at spaces, never as
            # "FER-/NÁNDEZ". \par must stay inside the group so the paragraph
            # is broken with those penalties still active.
            "{\\hyphenpenalty=10000\\exhyphenpenalty=10000"
            "\\fontsize{24}{27}\\selectfont\\bfseries\\color{accent} "
            + name
            + "\\par}\n"
        )
        left.append("\\vspace{0.3em}\n")
    if contact:
        left.append(contact + "\n")
    if parts:
        row = (
            "\\noindent\n"
            "\\begin{minipage}[t]{0.72\\textwidth}\n"
            "\\raggedright\n"
            + "".join(left)
            + "\\end{minipage}%\n"
            "\\hfill\n"
            "\\begin{minipage}[t]{0.26\\textwidth}\n"
            "\\raggedleft\n"
            "\\vspace{0.15em}\n"
            + "".join(parts)
            + "\\end{minipage}\n"
        )
    else:
        # \raggedright also in the full-width branch: justified text stretched
        # the zh name's first line (underfull hbox) instead of wrapping it.
        row = "\\noindent{\\raggedright\n" + "".join(left) + "\\par}\n"
    return (
        row
        + "\\vspace{0.45em}\n"
        + "{\\color{accent}\\hrule height 0.6pt}\n"
        + "\\vspace{0.12em}\n"
        + "{\\color{acento2}\\hrule height 0.3pt}\n"
    )


def _header_playful(d, L, parts):
    """Playful header: small LANG title, large name and badged contact lines."""
    name = esc(d.get("name", "")).strip()
    contact = _badge_contacts(_contacts(d, L))
    left = [
        f"{{\\small\\bfseries\\color{{accent}} {L['title']}}}\\par\n",
        "\\vspace{0.18em}\n",
    ]
    if name:
        left.append(
            "{\\hyphenpenalty=10000\\exhyphenpenalty=10000"
            "\\fontsize{26}{30}\\selectfont\\bfseries\\color{accent} "
            + name
            + "\\par}\n"
        )
        left.append("\\vspace{0.45em}\n")
    if contact:
        left.append(contact + "\n")
    if parts:
        # 0.72 instead of 0.7: the full zh name fits on its own line at 26pt
        # before the Latin transliteration wraps, so the name does not need a
        # third line in the narrow column.
        row = (
            "\\noindent\n"
            "\\begin{minipage}[t]{0.72\\textwidth}\n"
            "\\raggedright\n"
            + "".join(left)
            + "\\end{minipage}%\n"
            "\\hfill\n"
            "\\begin{minipage}[t]{0.26\\textwidth}\n"
            "\\raggedleft\n"
            "\\vspace{0.25em}\n"
            + "".join(parts)
            + "\\end{minipage}\n"
        )
    else:
        # \raggedright in the full-width branch: justification stretched the
        # zh name's first line and pushed LUCÍA to the far right.
        row = "\\noindent{\\raggedright\n" + "".join(left) + "\\par}\n"
    return (
        row
        + "\\vspace{0.5em}\n"
        + "{\\color{accent}\\hrule height 1.2pt}\n"
        + "\\vspace{0.12em}\n"
        + "{\\color{acento2}\\hrule height 0.5pt}\n"
    )


def _header_sidebar(d, L, parts):
    """Main column header of the sidebar template: name, profession and rule.

    The photo, the logos and the contacts live in the left bar (see
    ``_sidebar``), so ``parts`` is intentionally ignored here. Empty name and
    profession yield "" (never a marker).
    """
    name = esc(d.get("name", "")).strip()
    profession = esc(d.get("profession", "")).strip()
    if not name and not profession:
        return ""
    lines = []
    if name:
        lines.append(f"{{\\Huge\\bfseries\\color{{accent}} {name}}}\\par\n")
    if profession:
        lines.append("\\vspace{0.4em}\n")
        lines.append(f"{{\\large\\scshape\\color{{gris}} {profession}}}\\par\n")
    lines.append("\\vspace{0.6em}\n{\\color{accent}\\hrule height 1.2pt}\n")
    return "".join(lines)


def _sidebar(d, L):
    """Bar content of the sidebar templates: photo, logo and contacts.

    White text over the accent bar. The whole block is a zero-height overlay
    shifted into the bar (inner x=0.8cm, width 4.6cm): the "sidebar" variant
    shifts -6.2cm from the body's left edge (template's 7cm left margin), the
    "sidebar-right" variant shifts textwidth+1.6cm, which lands at
    paperwidth-5.4cm with the template's fixed 7cm right margin. A 1em gap
    separates the image block from the contacts when both are present. The main
    column keeps starting at the top of the text block either way.
    Returns "" when there is neither an image nor a contact (never a marker).
    """
    right = str(d.get("template", "") or "").strip().lower() == "sidebar-right"
    shift = (
        "\\hspace*{\\dimexpr\\textwidth+1.6cm\\relax}"
        if right
        else "\\hspace*{-6.2cm}"
    )
    logo_ref, has_photo, photo_ext = _image_info(d)
    contact = _contacts(d, L)

    def clamp(value, default, low, high):
        try:
            number = float(value or default)
        except (TypeError, ValueError):
            number = default
        return min(max(number, low), high)

    images = []
    if logo_ref:
        lw = clamp(d.get("school_logo_width_cm"), 2.4, 0.5, 4.6)
        images.append(
            f"\\includegraphics[width={lw:g}cm,keepaspectratio]{{{logo_ref}}}\\par\n"
        )
    if has_photo:
        pw = clamp(d.get("photo_width_cm"), 4.0, 1.0, 4.6)
        ph = clamp(d.get("photo_height_cm"), 5.0, 1.0, 8.0)
        if logo_ref:
            images.append("\\vspace{0.4em}\n")
        images.append(
            "{\\setlength{\\fboxsep}{3pt}%\n"
            f"\\fcolorbox{{white}}{{white}}{{\\includegraphics"
            f"[width={pw:g}cm,height={ph:g}cm,keepaspectratio]{{foto{photo_ext}}}}}\\par\n"
            "}\n"
        )
    if not images and not contact:
        return ""
    image_block = ""
    if images:
        image_block = "{\\centering\n" + "".join(images) + "\\par}\n"
    return (
        "\\noindent\\vbox to 0pt{%\n"
        "\\hbox{%\n"
        + shift + "%\n"
        "\\begin{minipage}[t]{4.6cm}%\n"
        "\\raggedright\n"
        "{\\color{white}%\n"
        + image_block
        + ("\\vspace{1em}\n" if images and contact else "")
        + (contact + "\n" if contact else "")
        + "}\\end{minipage}%\n"
        "\\hss}%\n"
        "\\vss}\n"
    )


def _header(d, L, template_name="classic"):
    logo_ref, has_photo, photo_ext = _image_info(d)
    parts = _image_parts(d, logo_ref, has_photo, photo_ext)
    if template_name == "harvard":
        return _header_harvard(d, L, parts)
    if template_name == "modern":
        return _header_modern(d, L, parts)
    if template_name == "creative":
        return _header_creative(d, L, parts)
    if template_name == "chinese":
        return _header_chinese(d, L, parts)
    if template_name == "tabbed":
        return _header_tabbed(d, L, parts)
    if template_name == "ribbon":
        return _header_ribbon(d, L, parts)
    if template_name == "navy":
        return _header_navy(d, L, parts)
    if template_name == "playful":
        return _header_playful(d, L, parts)
    if template_name in ("sidebar", "sidebar-right"):
        return _header_sidebar(d, L, parts)
    return _header_classic(d, L, parts)


def _work_entry(key, entry, idx, L=None):
    L = L or {}
    position = esc(entry.get("position", ""))
    work_mode = esc(option_label(entry.get("work_mode"), L.get("work_mode"))).strip()
    lines = []
    first = _date_title_line(position, entry.get("start", ""), entry.get("end", ""))
    if first:
        lines.append(first)
    if entry.get("company", "").strip():
        lines.append(f"{{\\itshape {esc(entry['company'])}}}")
    if work_mode:
        lines.append(f"({{\\footnotesize\\color{{gris}} {work_mode}}})")
    achievements = [x.strip() for x in str(entry.get("achievements", "")).splitlines() if x.strip()]
    if achievements:
        lines.append(_itemize([esc(x) for x in achievements]))
    if not lines:
        return ""
    return _with_logo(key, idx, entry, "\n".join(lines) + "\n")


def _education_entry(key, entry, idx, L):
    degree_type = esc(option_label(entry.get("degree_type"), L.get("degree_type"))).strip()
    degree = esc(entry.get("degree", "")).strip()
    label = " — ".join(x for x in (degree_type, degree) if x)
    lines = []
    first = _date_title_line(label, entry.get("start", ""), entry.get("end", ""))
    if first:
        lines.append(first)
    if entry.get("institution", "").strip():
        lines.append(f"{{\\itshape {esc(entry['institution'])}}}")
    if entry.get("grade", "").strip():
        lines.append(f"{{\\small\\color{{gris}} \\textbf{{{L['grade']}}} {esc(entry['grade'])}}}")
    if not lines:
        return ""
    return _with_logo(key, idx, entry, "\n".join(lines) + "\n")


def _project_entry(key, entry, idx, L, with_course):
    name = esc(entry.get("name", ""))
    lines = []
    first = _date_title_line(name, entry.get("start", ""), entry.get("end", ""))
    if first:
        lines.append(first)
    parts = []
    if entry.get("organization", "").strip():
        parts.append(f"{{\\itshape {esc(entry['organization'])}}}")
    if with_course and entry.get("course", "").strip():
        parts.append(f"{{\\footnotesize\\color{{gris}} {esc(entry['course'])}}}")
    if parts:
        lines.append("  ".join(parts))
    desc = _paragraphs(entry.get("description", ""))
    if desc:
        lines.append(desc.rstrip("\n"))
    if entry.get("result", "").strip():
        lines.append(f"{{\\footnotesize\\color{{gris}} \\textbf{{{L['result']}}} {esc(entry['result'])}}}")
    if entry.get("link", "").strip():
        lines.append(f"{{\\footnotesize\\color{{gris}} {L['link']}\\texttt{{{esc(entry['link'])}}}}}")
    if not lines:
        return ""
    return _with_logo(key, idx, entry, "\n".join(lines) + "\n") if with_course else "\n".join(lines) + "\n"


_SECTION_RENDERERS = {
    "work": _work_entry,
    "internships": _work_entry,
    "education": _education_entry,
    "projects": lambda c, e, i, L: _project_entry(c, e, i, L, False),
    "university_projects": lambda c, e, i, L: _project_entry(c, e, i, L, True),
}


def _chinese_work_entry(key, entry, idx, L):
    entry = entry or {}
    date_range = _date_range(entry.get("start", ""), entry.get("end", ""))
    position = esc(entry.get("position", "")).strip()
    company = esc(entry.get("company", "")).strip()
    work_mode = esc(option_label(entry.get("work_mode"), L.get("work_mode"))).strip()
    if work_mode:
        company = f"{company} ({work_mode})".strip()
    lines = []
    if date_range or position or company:
        lines.append(f"\\cvcnline{{{date_range}}}{{{position}}}{{{company}}}")
    achievements = [x.strip() for x in str(entry.get("achievements") or "").splitlines() if x.strip()]
    if achievements:
        lines.append(_itemize([esc(x) for x in achievements]))
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _chinese_education_entry(key, entry, idx, L):
    entry = entry or {}
    date_range = _date_range(entry.get("start", ""), entry.get("end", ""))
    institution = esc(entry.get("institution", "")).strip()
    degree_type = esc(option_label(entry.get("degree_type"), L.get("degree_type"))).strip()
    degree = esc(entry.get("degree", "")).strip()
    degree_label = " — ".join(x for x in (degree_type, degree) if x)
    lines = []
    if date_range or institution or degree_label:
        lines.append(f"\\cvcnline{{{date_range}}}{{{institution}}}{{{degree_label}}}")
    if entry.get("grade", "").strip():
        lines.append(f"{{\\small\\color{{gris}} \\textbf{{{L['grade']}}} {esc(entry['grade'])}}}")
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _chinese_project_entry(key, entry, idx, L, with_course):
    entry = entry or {}
    date_range = _date_range(entry.get("start", ""), entry.get("end", ""))
    name = esc(entry.get("name", "")).strip()
    organization = esc(entry.get("organization", "")).strip()
    if with_course:
        course = esc(entry.get("course", "")).strip()
        if course:
            organization = f"{organization} — {course}" if organization else course
    lines = []
    if date_range or name or organization:
        lines.append(f"\\cvcnline{{{date_range}}}{{{name}}}{{{organization}}}")
    items = [esc(x.strip()) for x in str(entry.get("description") or "").splitlines() if x.strip()]
    if entry.get("result", "").strip():
        items.append(f"\\textbf{{{L['result']}}} {esc(entry['result'])}")
    if entry.get("link", "").strip():
        items.append(f"{L['link'].strip()} \\texttt{{{esc(entry['link'])}}}")
    if items:
        lines.append(_itemize(items))
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


_CHINESE_RENDERERS = {
    "work": _chinese_work_entry,
    "internships": _chinese_work_entry,
    "education": _chinese_education_entry,
    "projects": lambda c, e, i, L: _chinese_project_entry(c, e, i, L, False),
    "university_projects": lambda c, e, i, L: _chinese_project_entry(c, e, i, L, True),
}


def _chinese_render_section(key, title, data, L):
    entries = data.get(key) or []
    render = _CHINESE_RENDERERS[key]
    rendered = []
    for entry in entries:
        content = render(key, entry, len(rendered), L)
        if content.strip():
            rendered.append(content)
    if not rendered:
        return ""
    return f"\\cvsection{{{title}}}\n" + "\\vspace{0.35em}\n".join(rendered)


def _render_section(key, title, data, L):
    entries = data.get(key) or []
    entries = [e for e in entries if any(str(v).strip() for v in (e or {}).values())]
    if not entries:
        return ""
    columns = int((data.get("columns") or {}).get(key, 1) or 1)
    columns = min(max(columns, 1), 3)
    render = _SECTION_RENDERERS[key]
    blocks = []
    for start in range(0, len(entries), columns):
        cells = []
        for i, entry in enumerate(entries[start:start + columns]):
            content = render(key, entry, start + i, L)
            if content.strip() == "":
                continue
            cells.append(_box(COLUMN_WIDTHS[columns], content))
        if cells:
            blocks.append("\\noindent " + " \\hfill\n".join(cells) + "\n\\par\n\\vspace{0.7em}\n")
    if not blocks:
        return ""
    return f"\\cvsection{{{title}}}\n" + "\n".join(blocks)


def _categories(entries, L):
    sep = L["skill_separator"]
    lines = []
    for e in entries or []:
        category = esc((e or {}).get("category", "")).strip()
        values = [v.strip() for v in str((e or {}).get("values", "")).split(",") if v.strip()]
        if not category and not values:
            continue
        body = ", ".join(esc(v) for v in values)
        if category and body:
            lines.append(f"\\noindent\\textbf{{{category}{sep}}} {body}")
        elif category:
            lines.append(f"\\noindent\\textbf{{{category}}}")
        else:
            lines.append(f"\\noindent {body}")
    return "\n\n".join(lines) + "\n" if lines else ""


def _pairs(entries, name_field, level_field, sep):
    lines = []
    for e in entries or []:
        name = esc(e.get(name_field, "")).strip()
        level = esc(e.get(level_field, "")).strip()
        if not name and not level:
            continue
        if name and level:
            lines.append(r"\textbf{%s}%s %s" % (name, sep, level))
        elif name:
            lines.append(r"\textbf{%s}" % name)
        else:
            lines.append(level)
    return _itemize(lines) if lines else ""


def _block_anchor(value):
    # Anchor missing or unknown: the block falls at the end of the document.
    anchor = str(value or "").strip()
    return anchor if anchor in BLOCK_ANCHORS else "end"


def _group_blocks(data):
    groups = {anchor: [] for anchor in BLOCK_ANCHORS}
    for block in data.get("blocks") or []:
        if isinstance(block, dict):
            groups[_block_anchor(block.get("position"))].append(block)
    return groups


def _section_block(block):
    title = str(block.get("title") or "").strip()
    content = _paragraphs(block.get("content") or "")
    if not title and not content:
        return ""
    heading = f"\\cvsection{{{esc(title)}}}\n" if title else ""
    return heading + content


def _separator_block(block):
    style = str(block.get("style") or "").strip()
    if style not in SEPARATOR_STYLES:
        style = "line"
    return _SEPARATOR_MACROS[style] + "\n"


def _column_entry(entry):
    heading = esc(entry.get("title", "")).strip()
    detail = esc(entry.get("detail", "")).strip()
    if not heading and not detail:
        return ""
    if heading and detail:
        return f"\\noindent\\textbf{{{heading}}} --- {detail}\n"
    if heading:
        return f"\\noindent\\textbf{{{heading}}}\n"
    return f"\\noindent {detail}\n"


def _period_entry(entry):
    period = esc(entry.get("period", "")).strip()
    description = _paragraphs(entry.get("description", ""))
    if not period and not description.strip():
        return ""
    if period and description.strip():
        return (
            "\\noindent\n"
            "\\begin{minipage}[t]{0.22\\linewidth}\n"
            "\\raggedright\n"
            f"{{\\itshape {period}}}\n"
            "\\end{minipage}%\n"
            "\\hfill\n"
            "\\begin{minipage}[t]{0.74\\linewidth}\n"
            "\\raggedright\n"
            f"{description}"
            "\\end{minipage}\n"
        )
    if period:
        return f"\\noindent{{\\itshape {period}}}\n"
    return description


def _list_block(block):
    mode = str(block.get("mode") or "").strip()
    if mode not in LIST_MODES:
        mode = "columns"
    title = str(block.get("title") or "").strip()
    try:
        columns = int(block.get("columns") or 1)
    except (TypeError, ValueError):
        columns = 1
    columns = min(max(columns, 1), 3)
    render = _period_entry if mode == "period" else _column_entry
    entries = block.get("entries")
    rows = []
    for entry in entries if isinstance(entries, (list, tuple)) else []:
        if not isinstance(entry, dict):
            continue
        content = render(entry)
        if not content.strip():
            continue
        rows.append(_box(COLUMN_WIDTHS[columns], content) if columns > 1 else content)
    if not rows:
        return ""
    if columns > 1:
        lines = []
        for start in range(0, len(rows), columns):
            lines.append(
                "\\noindent " + " \\hfill\n".join(rows[start:start + columns])
                + "\n\\par\n\\vspace{0.7em}\n"
            )
        content = "\n".join(lines)
    else:
        content = "\n\n".join(rows) + "\n"
    heading = f"\\cvsection{{{esc(title)}}}\n" if title else ""
    return heading + content


def _render_blocks(blocks):
    parts = []
    for block in blocks:
        block_type = str(block.get("type") or "").strip()
        if block_type == "section":
            parts.append(_section_block(block))
        elif block_type == "list":
            parts.append(_list_block(block))
        elif block_type == "separator":
            parts.append(_separator_block(block))
    return "".join(parts)


def normalize_section_order(data):
    # Contract replicated in main.py and docx_gen.py: only valid keys, no
    # duplicates (the first occurrence wins) and the missing ones are appended
    # at the end in the default order. Tolerant: never raises.
    try:
        order = data.get("section_order") if isinstance(data, dict) else None
    except Exception:
        order = None
    result = []
    if isinstance(order, (list, tuple)):
        for key in order:
            try:
                key = str(key)
            except Exception:
                continue
            if key in DEFAULT_SECTION_ORDER and key not in result:
                result.append(key)
    for key in DEFAULT_SECTION_ORDER:
        if key not in result:
            result.append(key)
    return result


def custom_section_title(data, key):
    # Trimmed, non-empty title from "section_titles" or None. Never raises.
    try:
        titles = data.get("section_titles") if isinstance(data, dict) else None
    except Exception:
        titles = None
    if not isinstance(titles, dict):
        return None
    try:
        value = titles.get(key)
    except Exception:
        return None
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    return text or None


def is_section_hidden(data, key):
    # True only if `key` appears in "hidden_sections". Never raises.
    try:
        hidden = data.get("hidden_sections") if isinstance(data, dict) else None
    except Exception:
        hidden = None
    if not isinstance(hidden, (list, tuple, set, frozenset)):
        return False
    for x in hidden:
        try:
            if x == key:
                return True
        except Exception:
            continue
    return False


def parse_hex_color(value):
    """Normalize a "#RGB" or "#RRGGBB" color to the tuple (r, g, b).

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
    if len(hex_digits) == 3 and re.fullmatch(r"[0-9A-Fa-f]{3}", hex_digits):
        hex_digits = "".join(c * 2 for c in hex_digits)
    if re.fullmatch(r"[0-9A-Fa-f]{6}", hex_digits) is None:
        return None
    return int(hex_digits[0:2], 16), int(hex_digits[2:4], 16), int(hex_digits[4:6], 16)


def template_colors(tex):
    """Accent colors present in a LaTeX template.

    Returns only the keys found among accent, acento2, acento3 and gris, in
    "#RRGGBB" uppercase format. Never raises.
    """
    colors = {}
    try:
        for match in _RE_DEFINE_COLOR.finditer(tex):
            name = match.group(1)
            if name not in _TEMPLATE_COLORS:
                continue
            r = min(max(int(match.group(2)), 0), 255)
            g = min(max(int(match.group(3)), 0), 255)
            b = min(max(int(match.group(4)), 0), 255)
            colors[name] = "#%02X%02X%02X" % (r, g, b)
    except Exception:
        return colors
    return colors


def _color_value(colors, key):
    """Value of colors[key] tolerating hostile dicts; never raises."""
    try:
        return colors.get(key)
    except Exception:
        return None


def _color_regex(name):
    """Regex of the triplet in a \\definecolor{name}{RGB}{r,g,b}."""
    return re.compile(
        r"(\\definecolor\s*\{\s*" + re.escape(name) + r"\s*\}\s*\{\s*RGB\s*\}\s*\{)"
        r"[^}]*(\})"
    )


def _apply_colors(tex, p):
    """Apply the prefs palette (key "colors") to the LaTeX template.

    primary -> accent, secondary -> acento2 and gray -> gris: when the color
    is already defined in the template only its RGB triplet is replaced
    (nothing else in the line); otherwise its definition is added. text ->
    injected as \\definecolor{cvtexto} before \\begin{document} and activated
    with \\color{cvtexto} right after it. Tolerant to hostile types: it never
    raises and, when no valid color is applied, returns the original tex
    without rebuilding it.
    """
    try:
        colors = p.get("colors") if isinstance(p, dict) else None
    except Exception:
        colors = None
    if not isinstance(colors, dict):
        return tex
    try:
        result = tex
        applied = False
        injections = []
        for key, name in _COLOR_MAP.items():
            rgb = parse_hex_color(_color_value(colors, key))
            if rgb is None:
                continue
            triplet = "%d,%d,%d" % rgb
            result, count = _color_regex(name).subn(
                lambda m, t=triplet: m.group(1) + t + m.group(2), result
            )
            if count:
                applied = True
            else:
                injections.append("\\definecolor{%s}{RGB}{%s}" % (name, triplet))
        text_rgb = parse_hex_color(_color_value(colors, "text"))
        if text_rgb is not None:
            injections.append("\\definecolor{cvtexto}{RGB}{%d,%d,%d}" % text_rgb)
        if injections and isinstance(result, str):
            marker = "\\begin{document}"
            pos = result.find(marker)
            if pos != -1:
                block = "\n".join(injections) + "\n"
                result = result[:pos] + block + result[pos:]
                applied = True
                if text_rgb is not None:
                    # The text color is activated right after the begin.
                    end_pos = pos + len(block) + len(marker)
                    result = result[:end_pos] + "\n\\color{cvtexto}" + result[end_pos:]
        if not applied:
            return tex
        return result
    except Exception:
        return tex


def _font_chain(template, candidates):
    """Nested ``\\IfFontExistsTF`` chain over `candidates`.

    `template` selects the font (`%s`, repeated per engine command); the first
    candidate that exists on the system wins and the last one is applied
    unconditionally as the final fallback.
    """

    def render(font):
        return template % ((font,) * template.count("%s"))

    body = render(candidates[-1])
    for font in reversed(candidates[:-1]):
        body = "\\IfFontExistsTF{%s}{%s}{%s}" % (font, render(font), body)
    return body


def build_tex(data, p):
    template_id = str(data.get("template", "classic") or "classic").strip().lower()
    if template_id not in TEMPLATES:
        template_id = "classic"
    path = os.path.join(BASE_DIR, "templates", TEMPLATE_FILES[template_id])
    with open(path, "r", encoding="utf-8") as f:
        tex = f.read()
    # The template comments document placeholders with {{...}}; they are not
    # part of the generated document and must not survive the substitutions.
    tex = "\n".join(
        line for line in tex.splitlines()
        if not (line.lstrip().startswith("%") and "{{" in line)
    )
    L = LANG.get(str(data.get("cv_language", "zh")), LANG["zh"])

    # Free blocks are inserted after their anchor section; "start" and "end"
    # are resolved separately. Blocks are ALWAYS emitted after their section,
    # even if it is empty or hidden, so their anchor keeps the chosen position.
    groups = _group_blocks(data)
    body = _render_blocks(groups["start"])
    render = _chinese_render_section if template_id in CHINESE_STYLE_TEMPLATES else _render_section
    for key in normalize_section_order(data):
        if not is_section_hidden(data, key):
            title = custom_section_title(data, key)
            title = esc(title) if title is not None else L[key]
            if key == "summary":
                summary = esc(str(data.get("summary", "") or "").strip())
                if summary:
                    body += _section(title, summary + "\n")
            elif key == "skills":
                body += _section(title, _categories(data.get("skills"), L))
            elif key == "languages":
                body += _section(title, _pairs(data.get("languages"), "language", "level", " --- "))
            elif key == "references":
                body += _section(title, _pairs(data.get("references"), "name", "contact", " --- "))
            else:
                body += render(key, title, data, L)
        # Block anchored to this section: emitted even if the section is hidden.
        body += _render_blocks(groups[key])
    body += _render_blocks(groups["end"])
    sidebar = _sidebar(data, L)
    header = _header(data, L, template_id)
    if not sidebar and not header.strip() and not body.strip():
        # A fully empty CV (e.g. a zh "sidebar" CV without a name: its header
        # omits the document title) must still ship one blank page; with no
        # material at all TeX reports "No pages of output" and emits no PDF.
        body += "\\null\n"

    m = p["margins"]
    papers = {"a4": "a4paper", "letter": "letterpaper", "legal": "legalpaper"}
    paper = papers.get(str(p["paper"]), "a4paper")
    if L is LANG["zh"]:
        font_engine = (
            "\\usepackage{fontspec}\n"
            + _font_chain("\\setmainfont{%s}\\setsansfont{%s}", CJK_MAIN_FONTS)
            + "\n"
            + _font_chain("\\setmonofont{%s}", CJK_MONO_FONTS)
        )
    else:
        font_engine = (
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[T1]{fontenc}\n"
            "\\usepackage{lmodern}"
        )
    tex = tex.replace("{{paper}}", paper)
    tex = tex.replace("{{font_engine}}", font_engine)
    tex = tex.replace("{{margin_top}}", f"{m['top']:g}")
    tex = tex.replace("{{margin_bottom}}", f"{m['bottom']:g}")
    tex = tex.replace("{{margin_left}}", f"{m['left']:g}")
    tex = tex.replace("{{margin_right}}", f"{m['right']:g}")
    tex = tex.replace("{{font_size}}", str(p["font_size"]))
    tex = tex.replace("{{sidebar}}", sidebar)
    tex = tex.replace("{{header}}", header)
    tex = tex.replace("{{body}}", body)
    tex = _apply_colors(tex, p)
    return tex_datos.embed(tex, data)
