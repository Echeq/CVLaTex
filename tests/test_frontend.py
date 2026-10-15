# -*- coding: utf-8 -*-
"""Static checks of the frontend, without a browser or pywebview.

The integration verification includes `node --check web/app.js` and
`node --check web/i18n.js` to validate the syntax of the frontend; this suite
does not run Node: it only checks that web/i18n.js, web/index.html, web/app.js
and web/style.css contain the structure, the frozen bridge calls and the
handlers the pipeline expects (English identifiers, multilingual i18n
(es/en/zh/ru), English-first default, close guard, installer cancellation,
blocks and zoom).
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PATH = os.path.join(ROOT, "web", "index.html")
JS_PATH = os.path.join(ROOT, "web", "app.js")
CSS_PATH = os.path.join(ROOT, "web", "style.css")
I18N_PATH = os.path.join(ROOT, "web", "i18n.js")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


HTML = _read(HTML_PATH)
JS = _read(JS_PATH)
CSS = _read(CSS_PATH)
I18N = _read(I18N_PATH)

# Frozen bridge surface of main.Api (docs/refactor-map.md).
FROZEN_API = {
    "init", "empty_data", "load_sample", "template_colors", "choose_file",
    "choose_photo", "save_image", "export_pdf", "export_tex", "export_docx",
    "export_cv", "open_cv", "autosave", "autosave_read", "autosave_clear",
    "import_tex", "install_latex", "cancel_install", "choose_latex_path",
    "check_latex", "open_preview", "set_prefs", "get_prefs", "dismiss_setup",
    "compile", "compile_tex", "set_dirty", "quit_app",
}

# Legacy Spanish bridge names that must not survive the rewrite.
OLD_API = (
    "elegir_foto", "abrir_cv", "guardar_imagen", "exportar_pdf",
    "exportar_tex", "exportar_docx", "exportar_cv", "importar_tex",
    "cargar_ejemplo", "compilar_tex", "autosave_borrar", "autosave_leer",
    "comprobar_latex", "elegir_ruta_latex", "marcar_setup_ignorado",
    "colores_plantilla", "datos_vacios",
)

# Frozen data-accion values (old value -> new value; zoom values are unchanged).
FROZEN_ACTIONS = (
    "new", "open", "save", "export-pdf", "export-tex", "export-docx",
    "import-tex", "settings", "undo", "redo", "paper:a4", "paper:letter",
    "paper:legal", "margins:normal", "margins:narrow", "margins:custom",
    "font:10", "font:11", "font:12", "template:classic", "template:harvard",
    "template:modern", "template:creative", "template:chinese", "load-sample",
    "reset-all",
    "add:columns:1", "add:columns:2", "add:columns:3", "add:period",
    "add:block-line", "add:block-band", "add:block-space", "add:section",
    "manage-blocks", "recompile", "toggle:auto-compile", "toggle:latex",
    "theme:light", "theme:dark", "theme:system", "help", "credits",
    "setup-engine", "close-modal", "zoom:75", "zoom:100", "zoom:125",
    "exit-without-saving", "open-preview",
)

OLD_ACTIONS = (
    "nuevo", "abrir", "guardar", "exportar-pdf", "exportar-tex",
    "exportar-docx", "importar-tex", "preferencias", "deshacer", "rehacer",
    "papel:a4", "papel:letter", "papel:legal", "margenes:normal",
    "margenes:estrecho", "margenes:personalizado", "fuente:10", "fuente:11",
    "fuente:12", "plantilla:clasico", "plantilla:harvard", "plantilla:moderno",
    "plantilla:creativo", "plantilla:chino", "cargar-ejemplo",
    "bloque:columnas:1", "bloque:columnas:2", "bloque:columnas:3",
    "bloque:periodo", "bloque:linea", "bloque:banda", "bloque:espacio",
    "bloque:seccion", "bloques:gestion", "recompilar", "toggle:autocompilar",
    "tema:claro", "tema:oscuro", "tema:sistema", "ayuda", "creditos",
    "preferencias-motor", "cerrar-modal",
)

# Frozen primary DOM ids.
FROZEN_IDS = (
    "toolbar", "menus", "splitter", "form-area", "form-panel", "preview-area",
    "preview-bar", "status-bar", "pdf", "toasts", "modal-confirm",
    "modal-settings", "modal-margins", "modal-custom-section",
    "modal-list-block", "modal-blocks", "modal-help", "modal-credits",
    "modal-wizard", "modal-crop", "settings-colors",
    "pf-color-primary", "pf-color-primary-wheel", "pf-color-primary-reset",
    "pf-color-secondary", "pf-color-secondary-wheel", "pf-color-secondary-reset",
    "pf-color-text", "pf-color-text-wheel", "pf-color-text-reset",
    "pf-color-gray", "pf-color-gray-wheel", "pf-color-gray-reset",
    "ui-language", "install-cancel", "latex-panel", "latex-text",
    "confirm-message", "confirm-cancel", "confirm-accept", "confirm-exit",
    "preview-notice",
)

# Frozen JS function names.
FROZEN_FUNCTIONS = (
    "parseHex", "readColorPrefs", "loadTemplateColors", "saveColorPrefs",
    "setupColorPrefs", "syncColorWheel", "markDirty", "scheduleCompile",
    "compileNow", "applyZoom", "applySplit", "setupSplitter", "enterLatexMode",
    "exitLatexMode", "renderForm", "renderDynamicList", "saveCurrentCv",
    "recordHistory", "undo", "redo", "mutateBlocks", "moveBlock",
    "createSeparatorBlock", "applyCollapse", "toggleCollapse", "normalizeImage",
    "dataHasContent", "hasContent", "openListBlockModal", "acceptListBlock",
    "readListEntries", "setupPrefs", "openPrefs", "blockAnchorsUI",
    "setupPreviewFallback", "openPreview",
)

# Social networks data contract shared with the backend (order matters).
SOCIAL_NETWORKS = (
    "github", "linkedin", "x", "instagram", "facebook", "youtube",
    "tiktok", "telegram", "wechat", "website", "other",
)


def _function_body(name):
    """Return the body of a top-level function (closing '}' at column 0)."""
    m = re.search(r"function %s\([^)]*\) \{(.*?)\n\}" % name, JS, re.S)
    assert m, "function %s not found in web/app.js" % name
    return m.group(1)


def _css_block(selector):
    """Return the body of the CSS rule for the exact selector."""
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    assert m, "rule %s not found in web/style.css" % selector
    return m.group(1)


def _i18n_pairs(lang):
    """Keys and string values of the `lang` table inside web/i18n.js."""
    start = I18N.index("\n  %s: {" % lang)
    end = I18N.index("\n  },", start)
    return dict(re.findall(r'^\s{4}([a-z0-9_]+): "([^"]*)"', I18N[start:end], re.M))


# ---------------- i18n ----------------

def test_i18n_has_multilingual_tables_and_english_fallback():
    assert os.path.isfile(I18N_PATH)
    assert "const I18N" in I18N
    for lang in ("es", "en", "zh", "ru"):
        assert "\n  %s: {" % lang in I18N, lang
    assert "function t(key)" in I18N
    # Unknown keys fall back to the English table and then to the key itself.
    assert "I18N.en[key]" in I18N
    assert "function setLang(code)" in I18N
    assert "function applyI18n(root = document)" in I18N
    assert "document.documentElement.lang" in I18N
    assert "data-i18n-placeholder" in I18N
    # Accessible names are translated through the same mechanism.
    assert "data-i18n-aria-label" in I18N
    assert 'setAttribute("aria-label"' in I18N
    # Canonical select labels mirror the backend LANG tables.
    assert "OPTION_LABELS" in I18N
    assert "degree_type" in I18N and "work_mode" in I18N
    assert "other: \"Otro\"" in I18N


def test_i18n_tables_have_identical_key_sets():
    """es/en/zh/ru stay in sync and the removed preview-menu keys are gone."""
    tables = {lang: _i18n_pairs(lang) for lang in ("es", "en", "zh", "ru")}
    for lang in ("es", "en", "zh", "ru"):
        assert len(tables[lang]) >= 100, lang
        assert set(tables[lang]) == set(tables["es"]), lang
    for removed in ("menu_preview", "action_recompile", "action_auto_compile"):
        for lang in ("es", "en", "zh", "ru"):
            assert removed not in tables[lang], (lang, removed)


def test_i18n_socials_keys():
    """The socials card keys exist in the four tables with their frozen values."""
    tables = {lang: _i18n_pairs(lang) for lang in ("es", "en", "zh", "ru")}
    expected = {
        "socials_title": {
            "es": "Redes sociales", "en": "Social networks",
            "zh": "社交网络", "ru": "Социальные сети",
        },
        "social_add": {
            "es": "+ Añadir red social", "en": "+ Add social network",
            "zh": "+ 添加社交网络", "ru": "+ Добавить соцсеть",
        },
        "network_website": {
            "es": "Web", "en": "Website", "zh": "网站", "ru": "Веб-сайт",
        },
        "network_other": {
            "es": "Otra", "en": "Other", "zh": "其他", "ru": "Другая",
        },
    }
    for key, values in expected.items():
        for lang, value in values.items():
            assert tables[lang].get(key) == value, (lang, key)
    for key in ("socials_title", "social_add", "social_network", "social_label",
                "social_value", "network_website", "network_other", "social_remove"):
        for lang in ("es", "en", "zh", "ru"):
            assert tables[lang].get(key), (lang, key)


def test_i18n_credits_keys():
    """The credits slogan, GitHub label and story live in the four tables."""
    tables = {lang: _i18n_pairs(lang) for lang in ("es", "en", "zh", "ru")}
    expected = {
        "credits_slogan": {
            "es": " — Currículums estandarizados, profesionales y sin complicaciones.",
            "en": " — Standardized, professional CVs without the hassle.",
            "zh": " — 标准化、专业的简历，简单省心。",
            "ru": " — Стандартные профессиональные резюме без лишних сложностей.",
        },
        "credits_github": {
            "es": "GitHub:", "en": "GitHub:", "zh": "GitHub：", "ru": "GitHub:",
        },
        "credits_story": {
            "es": "CVLaTeX nació para que cualquier universitario pueda crear su CV gratis y de forma portable, sin cuentas, suscripciones ni microtransacciones: un editor cómodo que genera un CV en formato estándar y lo compila a un PDF profesional, todo en tu propio equipo.",
            "en": "CVLaTeX was born so that any university student can build their CV for free and portably, with no accounts, subscriptions or microtransactions: a comfortable editor that produces a standard-format CV and compiles it to a professional PDF, all on your own machine.",
            "zh": "CVLaTeX 的初衷是让每位大学生都能免费、便携地制作简历，没有账号、订阅或微交易：一个顺手的编辑器，生成标准格式的简历并编译为专业 PDF，一切都在你自己的电脑上完成。",
            "ru": "CVLaTeX создан для того, чтобы любой студент мог бесплатно и портативно сделать своё резюме — без аккаунтов, подписок и микротранзакций: удобный редактор, который формирует резюме стандартного формата и компилирует его в профессиональный PDF прямо на вашем компьютере.",
        },
    }
    for key, values in expected.items():
        for lang, value in values.items():
            assert tables[lang].get(key) == value, (lang, key)
    # The old placeholders are gone from every table.
    for removed in ("credits_about", "credits_author"):
        for lang in ("es", "en", "zh", "ru"):
            assert removed not in tables[lang], (lang, removed)


def test_i18n_template_group_keys():
    """The template submenu group headings and labels exist in the four tables with frozen values."""
    tables = {lang: _i18n_pairs(lang) for lang in ("es", "en", "zh", "ru")}
    expected = {
        "template_group_ats": {
            "es": "Compatible con ATS", "en": "ATS Friendly",
            "zh": "ATS 友好", "ru": "Совместимо с ATS",
        },
        "template_group_chinese": {
            "es": "Estándar chino", "en": "Chinese Standard",
            "zh": "中文标准", "ru": "Китайский стандарт",
        },
        "template_group_normal": {
            "es": "CV normal", "en": "Normal CV",
            "zh": "普通简历", "ru": "Обычное резюме",
        },
        "template_sidebar": {
            "es": "Barra lateral (izquierda)", "en": "Sidebar (left)",
            "zh": "侧边栏（左）", "ru": "Боковая панель (слева)",
        },
        "template_sidebar_right": {
            "es": "Barra lateral (derecha)", "en": "Sidebar (right)",
            "zh": "侧边栏（右）", "ru": "Боковая панель (справа)",
        },
    }
    for key, values in expected.items():
        for lang, value in values.items():
            assert tables[lang].get(key) == value, (lang, key)


def test_i18n_reset_all_values():
    """The reset item is translated in the four tables with its frozen values."""
    tables = {lang: _i18n_pairs(lang) for lang in ("es", "en", "zh", "ru")}
    expected = {
        "es": "Vaciar todo (restablecer)",
        "en": "Reset everything",
        "zh": "重置全部内容",
        "ru": "Сбросить всё",
    }
    for lang, value in expected.items():
        assert tables[lang].get("action_reset_all") == value, lang


def test_index_loads_i18n_before_app():
    i18n_pos = HTML.index('<script src="/i18n.js"></script>')
    app_pos = HTML.index('<script src="/app.js"></script>')
    assert i18n_pos < app_pos


def test_index_has_ui_language_selector():
    """The settings selector offers the four UI languages with native names."""
    assert 'id="ui-language"' in HTML
    for value, label in (
        ("en", "English"), ("es", "Español"), ("zh", "中文"), ("ru", "Русский"),
    ):
        assert '<option value="%s">%s</option>' % (value, label) in HTML, value
    select = re.search(r'<select id="ui-language">(.*?)</select>', HTML, re.S)
    assert select
    values = re.findall(r'<option value="([a-z]{2})">', select.group(1))
    assert values == ["en", "es", "zh", "ru"]
    assert "Interface language" in HTML


def test_index_uses_i18n_attributes():
    assert 'data-i18n="' in HTML
    assert 'data-i18n-title="' in HTML
    assert 'data-i18n-placeholder="' in HTML
    assert 'data-i18n-aria-label="' in HTML

    # The four color pickers translate both their tooltip and accessible name.
    for field, key in (
        ("primary", "color_pick_primary"),
        ("secondary", "color_pick_secondary"),
        ("text", "color_pick_text"),
        ("gray", "color_pick_gray"),
    ):
        m = re.search(r"<input[^>]*id=\"pf-color-%s-wheel\"[^>]*>" % field, HTML)
        assert m, field
        assert 'data-i18n-title="%s"' % key in m.group(0), field
        assert 'data-i18n-aria-label="%s"' % key in m.group(0), field
        assert 'aria-label="' in m.group(0), field

    # No user-visible attribute (title/placeholder/aria-label) is left
    # hardcoded without an applyI18n translation; there is no alt text at all.
    for tag in re.findall(r"<[^>]+>", HTML):
        if 'aria-label="' in tag:
            assert "data-i18n-aria-label=" in tag, tag
        if 'title="' in tag:
            assert "data-i18n-title=" in tag, tag
        if 'placeholder="' in tag:
            assert "data-i18n-placeholder=" in tag, tag
    assert 'alt="' not in HTML

    # Every key referenced by a data-i18n* attribute resolves in ALL tables,
    # and no HTML-referenced value keeps an unresolved {placeholder}.
    keys = set(re.findall(r'data-i18n(?:-title|-placeholder|-aria-label)?="([^"]+)"', HTML))
    assert keys
    for lang in ("es", "en", "zh", "ru"):
        table = _i18n_pairs(lang)
        missing = sorted(keys - set(table))
        assert not missing, (lang, missing)
        unresolved = sorted(k for k in keys if "{" in table[k])
        assert not unresolved, (lang, unresolved)


def test_index_credits_modal_content():
    """Credits: slogan, literal author, GitHub link and story; placeholders gone."""
    modal = HTML[HTML.index('id="modal-credits"'):HTML.index('id="modal-confirm"')]
    assert 'data-i18n="credits_slogan"' in modal
    assert 'data-i18n="credits_developed"' in modal
    assert '<span class="credits-name">Elvis Enrique Chen Qiu</span>' in modal
    # The GitHub handle is an anchor: pywebview's Windows WebView2 backend
    # turns a target="_blank" NewWindowRequested into a system-browser open
    # (OPEN_EXTERNAL_LINKS_IN_BROWSER), never an in-app navigation.
    assert '<a href="https://github.com/ECHEQ" rel="noopener" target="_blank">ECHEQ</a>' in modal
    assert 'data-i18n="credits_tinytex"' in modal
    # The story sits after the GitHub line and before the TinyTeX thanks.
    github_pos = modal.index('data-i18n="credits_github"')
    story_pos = modal.index('data-i18n="credits_story"')
    tinytex_pos = modal.index('data-i18n="credits_tinytex"')
    assert github_pos < story_pos < tinytex_pos
    # The old placeholder keys are gone from the HTML too.
    assert "credits_about" not in HTML and "credits_author" not in HTML
    # The anchor stays visible in both themes.
    assert "var(--accent)" in _css_block("#modal-credits a")


# ---------------- frozen ids and actions ----------------

def test_index_has_all_frozen_dom_ids():
    for dom_id in FROZEN_IDS:
        assert 'id="%s"' % dom_id in HTML, dom_id


def test_index_has_all_frozen_actions():
    for action in FROZEN_ACTIONS:
        assert 'data-accion="%s"' % action in HTML, action


def test_index_has_no_old_spanish_actions():
    for action in OLD_ACTIONS:
        assert 'data-accion="%s"' % action not in HTML, action
    # Old Spanish data-marca values are gone as well.
    for marca in ("autocompilar", "tema-claro", "tema-oscuro", "tema-sistema",
                  "plantilla-clasico", "plantilla-harvard", "plantilla-moderno",
                  "plantilla-creativo", "plantilla-chino"):
        assert 'data-marca="%s"' % marca not in HTML, marca


def test_index_preview_menu_removed():
    """The whole preview menu is gone; the preview bar keeps its own buttons."""
    assert "Previsualización" not in HTML
    assert 'data-i18n="menu_preview"' not in HTML
    assert 'data-marca="auto-compile"' not in HTML
    assert 'id="recompile-button"' in HTML
    assert 'data-accion="recompile"' in HTML
    assert 'id="auto-button"' in HTML
    assert 'data-accion="toggle:auto-compile"' in HTML


def test_index_view_latex_moved_to_edit_menu():
    """toggle:latex moved into Edit, after the template submenu and before the sample."""
    # One entry in the Edit menu plus the back-to-form button in the LaTeX bar.
    assert HTML.count('data-accion="toggle:latex"') == 2
    edit_menu = HTML[HTML.index('data-i18n="menu_edit"'):HTML.index('data-i18n="menu_add"')]
    latex_pos = edit_menu.index('data-accion="toggle:latex"')
    template_pos = edit_menu.index('data-i18n="submenu_template"')
    sample_pos = edit_menu.index('data-accion="load-sample"')
    assert template_pos < latex_pos < sample_pos
    # The item must not carry a leading mark span (that span caused the indent);
    # the active state is painted through the `active` class instead.
    item = re.search(r'<a data-accion="toggle:latex">(.*?)</a>', edit_menu, re.S)
    assert item, "Edit menu toggle:latex link not found"
    assert 'class="mark"' not in item.group(1)
    assert 'data-marca="latex"' not in item.group(1)
    assert 'data-i18n="action_view_latex"' in item.group(1)
    assert 'data-marca="latex"' not in HTML


def test_index_reset_all_after_load_sample():
    """The Edit menu offers Reset everything right below Load sample CV."""
    edit_menu = HTML[HTML.index('data-i18n="menu_edit"'):HTML.index('data-i18n="menu_add"')]
    sample_pos = edit_menu.index('data-accion="load-sample"')
    reset_pos = edit_menu.index('data-accion="reset-all"')
    assert sample_pos < reset_pos
    # A separator sits between the sample item and the reset item.
    assert "<hr>" in edit_menu[sample_pos:reset_pos]
    reset_item = edit_menu[reset_pos:]
    assert 'data-i18n="action_reset_all"' in reset_item
    assert ">Reset everything</a>" in reset_item


def test_index_template_submenu_groups():
    """The seven templates are grouped under three labelled, non-clickable headings.

    Order: ATS Friendly (classic, harvard), Chinese Standard (chinese) and
    Normal CV (modern, creative, sidebar, sidebar-right); the groups are
    separated with <hr>.
    """
    edit_menu = HTML[HTML.index('data-i18n="menu_edit"'):HTML.index('data-i18n="menu_add"')]
    start = edit_menu.index('data-i18n="submenu_template"')
    subdrop = edit_menu[start:edit_menu.index('data-accion="toggle:latex"', start)]
    # The headings keep their exact markup: a div (never an anchor), so they are
    # not clickable and cannot trigger data-accion handlers.
    for key, label in (
        ("template_group_ats", "ATS Friendly"),
        ("template_group_chinese", "Chinese Standard"),
        ("template_group_normal", "Normal CV"),
    ):
        assert '<div class="menu-heading" data-i18n="%s">%s</div>' % (key, label) in subdrop, key
        assert HTML.count('data-i18n="%s"' % key) == 1, key
    assert '<a class="menu-heading"' not in subdrop
    # Each link lives under its group: slices between headings.
    ats = subdrop[subdrop.index('data-i18n="template_group_ats"'):
                  subdrop.index('data-i18n="template_group_chinese"')]
    chinese = subdrop[subdrop.index('data-i18n="template_group_chinese"'):
                      subdrop.index('data-i18n="template_group_normal"')]
    normal = subdrop[subdrop.index('data-i18n="template_group_normal"'):]
    assert 'data-accion="template:classic"' in ats
    assert 'data-accion="template:harvard"' in ats
    assert 'data-accion="template:modern"' not in ats
    assert 'data-accion="template:creative"' not in ats
    assert 'data-accion="template:sidebar"' not in ats
    assert 'data-accion="template:sidebar-right"' not in ats
    assert 'data-accion="template:chinese"' not in ats
    assert 'data-accion="template:chinese"' in chinese
    assert 'data-accion="template:modern"' not in chinese
    assert 'data-accion="template:sidebar"' not in chinese
    assert 'data-accion="template:sidebar-right"' not in chinese
    assert re.findall(r'data-accion="template:([a-z-]+)"', normal) == [
        "modern", "creative", "sidebar", "sidebar-right",
    ]
    # The groups are separated with the menu hr and every link keeps its mark.
    for before, after in (
        ('data-accion="template:harvard"', 'data-i18n="template_group_chinese"'),
        ('data-accion="template:chinese"', 'data-i18n="template_group_normal"'),
    ):
        assert "<hr>" in subdrop[subdrop.index(before):subdrop.index(after)], (before, after)
    for value in ("classic", "harvard", "modern", "creative", "sidebar", "sidebar-right", "chinese"):
        assert 'data-marca="template-%s"' % value in subdrop, value
    # Small muted label: not a clickable menu item.
    heading_css = _css_block(".menu-heading")
    assert "cursor: default" in heading_css
    assert "var(--text-soft)" in heading_css


def test_index_static_text_is_english():
    """Static fallbacks are English because English is the default UI language."""
    assert '<html lang="en">' in HTML
    for spanish in (
        "Editor de CV", "Archivos", "Editar", "Añadir", "Previsualización",
        "Tema", "Ayuda", "Créditos", "Abrir", "Guardar", "Exportar",
        "Preferencias", "Deshacer", "Rehacer", "Recompilar", "Esperando",
        "Sin foto", "Sin logo", "Cerrar", "Cancelar", "Aceptar", "Aplicar",
        "Configurar motor", "Guía rápida", "Motor LaTeX", "Datos personales",
    ):
        assert spanish not in HTML, spanish


def test_index_export_submenu_order_and_single_import():
    """Export is a submenu with pdf/tex/docx before the single import-tex."""
    assert '<div class="sub">' in HTML
    export_start = HTML.index('data-i18n="submenu_export"')
    subdrop = HTML.index('<div class="menu-drop subdrop">', export_start)
    import_pos = HTML.index('data-accion="import-tex"', export_start)
    assert export_start < subdrop < import_pos
    for action in ('data-accion="export-pdf"', 'data-accion="export-tex"', 'data-accion="export-docx"'):
        pos = HTML.index(action, export_start)
        assert subdrop < pos < import_pos, action
    assert HTML.count('data-accion="import-tex"') == 1
    assert 'data-accion="import"' not in HTML


# ---------------- frozen bridge calls ----------------

def test_app_uses_only_frozen_api_names():
    used = set(re.findall(r"api\.([A-Za-z_][A-Za-z0-9_]*)", JS))
    assert used, "no api.<name> calls found in web/app.js"
    assert used <= FROZEN_API, sorted(used - FROZEN_API)
    # The pywebview readiness probe checks a frozen name.
    assert 'typeof window.pywebview.api.init === "function"' in JS
    for name in ("api.init(", "api.get_prefs(", "api.set_dirty(", "api.quit_app(",
                 "api.cancel_install(", "api.install_latex(", "api.choose_photo(",
                 "api.save_image(", "api.export_cv(", "api.autosave_read("):
        assert name in JS, name


def test_app_has_no_old_spanish_api_names():
    for name in OLD_API:
        assert name not in JS, name


def test_app_has_all_frozen_function_names():
    for name in FROZEN_FUNCTIONS:
        assert "function %s(" % name in JS, name


# ---------------- retained regressions ----------------

def test_app_block_ids_use_uuid_or_hex_fallback():
    assert "crypto.randomUUID" in JS
    # Fallback when crypto.randomUUID is unavailable.
    assert "0123456789abcdef" in JS


def test_app_zoom_uses_pdf_viewer_fragment():
    assert '"#zoom="' in JS
    assert '"&view=FitH"' in JS


def test_app_entry_titles_come_from_i18n():
    assert 't("entry_duplicate")' in JS
    assert 't("entry_up")' in JS
    assert 't("entry_down")' in JS
    assert 't("entry_delete")' in JS
    for literal in ('"Duplicar entrada"', '"Subir entrada"', '"Bajar entrada"', '"Eliminar entrada"'):
        assert literal not in JS, literal


def test_app_collapse_helpers_use_i18n():
    assert "function applyCollapse(" in JS
    assert "function toggleCollapse(" in JS
    assert 't("no_entries")' in JS
    assert "colapsoUI" not in JS


def test_app_normalize_image_signature_and_jpeg_quality():
    for token in ("1600", "512", "image/jpeg", "image/png", "toDataURL"):
        assert token in JS, token
    assert "function normalizeImage(sourceUrl, maxSide, mime, quality)" in JS
    assert 'normalizeImage(r.url, 1600, "image/jpeg", 0.9)' in JS
    assert 'normalizeImage(r.url, 512, "image/png")' in JS
    assert 'toDataURL("image/jpeg", 0.9)' in JS


def test_app_uses_english_section_keys_and_order():
    for token in (
        "section_titles",
        "hidden_sections",
        "section_order",
        "function sectionOrder(",
        "function blockAnchorsUI(",
        "DEFAULT_SECTION_ORDER",
        "section-title-input",
        "section-hide-button",
        "section-up-button",
        "section-down-button",
    ):
        assert token in JS, token
    for token in ("titulos_seccion", "secciones_ocultas", "orden_secciones",
                  "ORDEN_SECCIONES_DEFECTO", "anclasUI"):
        assert token not in JS, token


def test_app_personal_card_is_slimmed():
    """The personal card dropped birth date, nationality, website, GitHub, LinkedIn."""
    body = _function_body("renderForm")
    for kept in (
        "cvLanguageField()", 'basicField("name"', 'basicField("profession"',
        'basicField("email"', 'basicField("phone"', 'basicField("address"',
        'basicField("school_name"', 'personalLogoField("school_logo"',
    ):
        assert kept in body, kept
    for removed in ('basicField("birth_date"', 'basicField("nationality"',
                    'basicField("website"', 'basicField("github"',
                    'basicField("linkedin"'):
        assert removed not in body, removed
        assert removed not in JS, removed
    assert "birth_date" not in JS
    assert "nationality" not in JS
    # The removed i18n keys are gone from the four tables too.
    for removed in ("field_birth_date", "field_nationality", "field_website",
                    "field_github", "field_linkedin"):
        assert removed not in I18N, removed


def test_app_socials_card():
    """The new card is a dynamic list with add, remove and edit history."""
    body = _function_body("renderSocials")
    for token in (
        't("social_add")', 't("social_network")', 't("social_label")',
        't("social_value")', 't("social_remove")',
        "recordHistory(true)", "recordHistory(false)", "markDirty(true)",
    ):
        assert token in body, token
    assert 'wrap.id = "socials-list"' in body
    assert 'add.id = "social-add"' in body
    # add (1) and remove (1) are structural; the three edits are not.
    assert body.count("recordHistory(true)") == 2
    assert body.count("recordHistory(false)") == 3
    form = _function_body("renderForm")
    assert 'sectionCard(t("socials_title"))' in form
    assert "renderSocials()" in form
    assert "function socialNetworkLabel(" in JS


def test_app_socials_networks_and_label_toggle():
    """The 11 network values and the custom-name toggle when network == other."""
    m = re.search(r"const SOCIAL_NETWORKS = \[(.*?)\n\];", JS, re.S)
    assert m, "SOCIAL_NETWORKS not found in web/app.js"
    values = re.findall(r'value: "([^"]+)"', m.group(1))
    assert values == list(SOCIAL_NETWORKS)
    # Only website/other are translated; the nine brands stay literal.
    assert 'labelKey: "network_website"' in m.group(1)
    assert 'labelKey: "network_other"' in m.group(1)
    # The custom-name input is only visible when the selected network is other.
    body = _function_body("renderSocials")
    assert 'customField.hidden = social.network !== "other"' in body
    # Add always appends a valid row with the GitHub network.
    assert 'socialsList().push({ network: "github", label: "", value: "" })' in body


def test_app_list_block_helpers():
    for token in (
        "function openListBlockModal(",
        "function acceptListBlock(",
        "function readListEntries(",
        "list-block-entries",
        '"columns"',
        '"period"',
    ):
        assert token in JS, token
    for token in ("abrirModalBloqueListado", "aceptarBloqueListado",
                  "leerEntradasLista", "MODOS_LISTA"):
        assert token not in JS, token


def test_app_data_has_content_and_autosave_recovery():
    assert "function dataHasContent(" in JS
    assert "function hasContent(" in JS
    assert "datosConContenido" not in JS
    assert "dataHasContent(state.data)" in _function_body("hasContent")
    assert "if (pendingAutosave && dataHasContent(pendingAutosave)) offerRecovery(pendingAutosave);" in JS
    assert "else if (pendingAutosave) clearAutosave();" in JS


def test_app_recovery_accept_marks_dirty_and_compiles():
    """Accepting the recovered CV refreshes the preview and re-arms the guard."""
    body = _function_body("offerRecovery")
    render_pos = body.index("renderForm();")
    marks_pos = body.index("updateMarks();")
    dirty_pos = body.index("markDirty(true);")
    compile_pos = body.index("compileNow();")
    assert render_pos < marks_pos < dirty_pos < compile_pos
    assert 't("toast_recovered")' in body
    # The discard callback still only clears the autosave and the dirty flag.
    assert body.count("markDirty(false);") == 1


def test_app_latex_mode_mark_uses_scoped_active_class():
    """updateMarks toggles `active` on the Edit-menu link (never #back-to-form)."""
    body = _function_body("updateMarks")
    assert 'menus.querySelector(\'[data-accion="toggle:latex"]\')' in body
    assert 'classList.toggle("active", state.mode === "latex")' in body
    assert '[data-marca="latex"]' not in JS


# ---------------- close guard and installer ----------------

def test_app_close_guard_tokens():
    for token in (
        "api.set_dirty(",
        "window.__onCloseRequest",
        "api.quit_app(",
        '"#modal-confirm"',
        '"#confirm-exit"',
        't("close_guard_message")',
        "function saveAndExit(",
        "state.filePath",
        "api.export_cv(state.data, state.filePath)",
        't("save")',
        't("close_guard_save_failed")',
    ):
        assert token in JS, token
    # The three-option guard is fully translated in every language.
    for lang in ("es", "en", "zh", "ru"):
        table = _i18n_pairs(lang)
        assert "save" in table and "close_guard_save_failed" in table, lang
    assert 'data-accion="exit-without-saving"' in HTML
    assert 'data-i18n="exit_without_saving"' in HTML
    # The dirty flag is cleared after save/open/new/sample/import.
    for name in ("saveCurrentCv", "openCv", "newCv", "loadSample", "importTex"):
        assert "markDirty(false)" in _function_body(name), name
    # The current .cvjson path is tracked on open/save and dropped when the
    # document comes from new/import/sample (no destination to save into).
    assert "state.filePath = r.ruta || null;" in _function_body("openCv")
    assert "state.filePath = r.ruta;" in _function_body("saveCurrentCv")
    for name in ("newCv", "importTex", "loadSample"):
        assert "state.filePath = null;" in _function_body(name), name


def test_app_installer_cancel_tokens():
    assert "api.cancel_install(" in JS
    assert "api.install_latex(" in JS
    assert '"#install-cancel"' in JS
    assert 'id="install-cancel"' in HTML
    assert '"#modal-wizard"' in JS


def test_app_install_warning_tokens():
    """The wizard surfaces the non-fatal checksum warning (live + on done)."""
    assert "__onInstallProgress = function (p)" in JS
    assert "if (p.warning)" in JS
    assert '$("#wz-progress-text").textContent = p.warning;' in JS
    assert "__onInstallDone = function (r)" in JS
    assert 'toast(r.warning ? r.msg + " " + r.warning : r.msg);' in JS


# ---------------- Linux preview fallback ----------------

def test_index_linux_preview_notice_tokens():
    """Linux-only notice + system-viewer button, wired to api.open_preview()."""
    assert 'id="preview-notice"' in HTML
    assert 'data-accion="open-preview"' in HTML
    assert 'data-i18n="preview_linux_notice"' in HTML
    assert 'data-i18n="preview_linux_open"' in HTML
    # Hidden by default and only Linux unhides it.
    notice = re.search(r'<div id="preview-notice"[^>]*>', HTML)
    assert notice and "hidden" in notice.group(0), "the notice must start hidden"
    assert 'notice.hidden = platform !== "linux"' in _function_body("setupPreviewFallback")
    assert "setupPreviewFallback(info.platform)" in JS
    assert "api.open_preview(" in _function_body("openPreview")
    # The system viewer opens a file:// URI through the backend.
    assert "api.open_preview(" in JS


def test_i18n_linux_preview_keys_in_four_languages():
    tables = {lang: _i18n_pairs(lang) for lang in ("es", "en", "zh", "ru")}
    for lang in ("es", "en", "zh", "ru"):
        assert tables[lang].get("preview_linux_notice"), lang
        assert tables[lang].get("preview_linux_open"), lang
    assert tables["es"]["preview_linux_notice"] == (
        "La previsualización integrada no está disponible en Linux; usa el botón "
        "para abrir el PDF con el visor del sistema."
    )


# ---------------- LaTeX mode and form regressions ----------------

def test_app_render_form_recreates_form_panel():
    """Regression: returning from LaTeX mode crashed with #form-panel null."""
    body = _function_body("renderForm")
    assert 'let cont = $("#form-panel");' in body
    assert "if (!cont) {" in body
    assert 'document.createElement("div")' in body
    assert 'cont.id = "form-panel"' in body
    assert "host.appendChild(cont)" in body


def test_app_latex_mode_keeps_the_form():
    """enterLatexMode hides #form-panel instead of emptying #form-area."""
    enter = _function_body("enterLatexMode")
    assert 'form.innerHTML = ""' not in enter
    assert "panelForm.hidden = true" in enter
    assert '$("#latex-panel")' in enter
    assert 'cont.id = "latex-panel"' in enter
    assert 'area.id = "latex-text"' in enter
    assert "host.appendChild(cont)" in enter
    # exitLatexMode removes #latex-panel, shows #form-panel and repaints.
    exit_body = _function_body("exitLatexMode")
    assert '$("#latex-panel")' in exit_body
    assert "pl.remove()" in exit_body
    assert "panelForm.hidden = false" in exit_body
    assert "renderForm()" in exit_body
    assert "state.texManual = null" in exit_body
    assert "state.texEdited = false" in exit_body


def test_app_uses_english_prefs_keys():
    for token in (
        'set_prefs("paper"',
        'set_prefs("font_size"',
        'set_prefs("auto_compile"',
        'set_prefs("theme"',
        'set_prefs("colors"',
        'set_prefs("margins"',
        'set_prefs("split"',
        'set_prefs("ui_language"',
        "state.prefs.auto_compile",
        "state.prefs.font_size",
    ):
        assert token in JS, token
    for token in ('set_prefs("papel"', 'set_prefs("fuente"', 'set_prefs("autocompilar"',
                  'set_prefs("tema"', 'set_prefs("colores"', 'set_prefs("margenes"'):
        assert token not in JS, token


# ---------------- CSS ----------------

def test_css_frozen_rules():
    assert "#splitter { flex: 0 0 5px; cursor: col-resize;" in CSS
    assert "display: flex" in _css_block(".color-row")
    assert ".colors-note" in CSS
    assert ".menu-drop a.disabled" in CSS
    active_rule = _css_block(".menu-drop a.active")
    assert "var(--accent)" in active_rule
    # The active state must not reintroduce the indentation it replaced.
    assert "margin" not in active_rule and "padding" not in active_rule
    assert "flex: 1 1 auto" in _css_block("#latex-panel")
    latex_text = _css_block("#latex-text")
    assert "flex: 1 1 auto" in latex_text
    assert "min-height: 0" in latex_text
