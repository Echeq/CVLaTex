"use strict";

/* CVLaTeX frontend. All user-visible strings come from web/i18n.js through
   `t()`; identifiers and comments are English. The bridge calls mirror the
   frozen Api surface of main.py, including its Spanish envelope keys
   (`errores`, `ruta`, `cancelado`, ...), which are part of the wire format. */

let api = null;

function waitForApi() {
  return new Promise((resolve) => {
    let done = false;
    const check = () => {
      if (
        !done &&
        window.pywebview &&
        window.pywebview.api &&
        typeof window.pywebview.api.init === "function"
      ) {
        done = true;
        clearInterval(timer);
        resolve(window.pywebview.api);
      }
    };
    const timer = setInterval(check, 30);
    window.addEventListener("pywebviewready", check);
    setTimeout(() => {
      if (!done) {
        done = true;
        clearInterval(timer);
        resolve((window.pywebview && window.pywebview.api) || null);
      }
    }, 5000);
  });
}

const $ = (selector, base) => (base || document).querySelector(selector);
const $$ = (selector, base) => Array.from((base || document).querySelectorAll(selector));

const state = {
  data: null,
  prefs: null,
  filePath: null,
  latexOk: false,
  mode: "form",
  tex: null,
  texManual: null,
  texEdited: false,
  dirty: false,
  compileId: 0,
  timer: null,
  zoom: 100,
  undoStack: [],
  redoStack: [],
  statusKey: "",
  statusSuffix: "",
  statusClass: "",
  preview: { state: "idle" },
};

let emptyData = null;

const CV_LANGUAGES = [
  { value: "zh", labelKey: "cv_language_zh" },
  { value: "es", labelKey: "cv_language_es" },
  { value: "en", labelKey: "cv_language_en" },
];

const TEMPLATES_CV = [
  { value: "classic", labelKey: "template_classic" },
  { value: "harvard", labelKey: "template_harvard" },
  { value: "modern", labelKey: "template_modern" },
  { value: "creative", labelKey: "template_creative" },
  { value: "sidebar", labelKey: "template_sidebar" },
  { value: "sidebar-right", labelKey: "template_sidebar_right" },
  { value: "chinese", labelKey: "template_chinese" },
];

const THEMES = ["light", "dark", "system"];

const COLOR_FIELDS = ["primary", "secondary", "text", "gray"];

/* Canonical entry schema (English keys, docs/refactor-map.md). Select values
   are canonical keys; their labels come from the backend LANG tables through
   `optionLabel()` in web/i18n.js. */
const DYNAMIC_SECTIONS = {
  work: {
    titleKey: "dyn_work",
    columns: true,
    fields: [
      { k: "work_mode", labelKey: "field_work_mode", type: "select", options: ["onsite", "hybrid", "remote"], optionKind: "work_mode" },
      { k: "position", labelKey: "field_position" },
      { k: "company", labelKey: "field_company" },
      { k: "start", labelKey: "field_start" },
      { k: "end", labelKey: "field_end" },
      { k: "achievements", labelKey: "field_achievements", area: true },
      { k: "logo", labelKey: "field_company_logo", type: "logo" },
    ],
  },
  internships: {
    titleKey: "dyn_internships",
    columns: true,
    fields: [
      { k: "work_mode", labelKey: "field_work_mode", type: "select", options: ["onsite", "hybrid", "remote"], optionKind: "work_mode" },
      { k: "position", labelKey: "field_position" },
      { k: "company", labelKey: "field_company" },
      { k: "start", labelKey: "field_start" },
      { k: "end", labelKey: "field_end" },
      { k: "achievements", labelKey: "field_achievements", area: true },
      { k: "logo", labelKey: "field_company_logo", type: "logo" },
    ],
  },
  projects: {
    titleKey: "dyn_projects",
    columns: true,
    fields: [
      { k: "name", labelKey: "field_project_name" },
      { k: "organization", labelKey: "field_organization" },
      { k: "start", labelKey: "field_start" },
      { k: "end", labelKey: "field_end" },
      { k: "description", labelKey: "field_description", area: true },
      { k: "result", labelKey: "field_result" },
      { k: "link", labelKey: "field_link" },
    ],
  },
  university_projects: {
    titleKey: "dyn_university_projects",
    columns: true,
    fields: [
      { k: "name", labelKey: "field_project_name" },
      { k: "course", labelKey: "field_course" },
      { k: "organization", labelKey: "field_university_company" },
      { k: "start", labelKey: "field_start" },
      { k: "end", labelKey: "field_end" },
      { k: "description", labelKey: "field_description", area: true },
      { k: "result", labelKey: "field_result" },
      { k: "link", labelKey: "field_link" },
      { k: "logo", labelKey: "field_university_logo", type: "logo" },
    ],
  },
  education: {
    titleKey: "dyn_education",
    columns: true,
    fields: [
      { k: "degree_type", labelKey: "field_degree_type", type: "select", options: ["primary", "secondary", "high_school", "vocational_mid", "vocational_high", "bachelor", "engineering", "licentiate", "diploma", "architecture", "master", "phd", "postgraduate", "course", "other"], optionKind: "degree_type" },
      { k: "degree", labelKey: "field_degree" },
      { k: "institution", labelKey: "field_institution" },
      { k: "start", labelKey: "field_start" },
      { k: "end", labelKey: "field_end" },
      { k: "grade", labelKey: "field_grade" },
      { k: "logo", labelKey: "field_institution_logo", type: "logo" },
    ],
  },
  skills: {
    titleKey: "dyn_skills",
    fields: [
      { k: "category", labelKey: "field_category" },
      { k: "values", labelKey: "field_values" },
    ],
  },
  languages: {
    titleKey: "dyn_languages",
    fields: [
      { k: "language", labelKey: "field_language" },
      { k: "level", labelKey: "field_level" },
    ],
  },
  references: {
    titleKey: "dyn_references",
    fields: [
      { k: "name", labelKey: "field_name" },
      { k: "contact", labelKey: "field_contact" },
    ],
  },
  extra_fields: {
    titleKey: "dyn_extra_fields",
    fields: [
      { k: "label", labelKey: "field_label" },
      { k: "value", labelKey: "field_value" },
    ],
  },
};

/* Social networks card: state.data.socials is a list of
   {network, label, value}. The nine proper nouns keep their brand name in
   every language; "website" and "other" are translated through their i18n
   keys. Empty-value entries are dropped by the backend, so the UI keeps rows
   while editing and always starts a new one with a valid network. */
const SOCIAL_NETWORKS = [
  { value: "github", label: "GitHub" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "x", label: "X" },
  { value: "instagram", label: "Instagram" },
  { value: "facebook", label: "Facebook" },
  { value: "youtube", label: "YouTube" },
  { value: "tiktok", label: "TikTok" },
  { value: "telegram", label: "Telegram" },
  { value: "wechat", label: "WeChat" },
  { value: "website", labelKey: "network_website" },
  { value: "other", labelKey: "network_other" },
];

// Default order of the standard CV body sections (kept in sync with
// latex_gen.DEFAULT_SECTION_ORDER). The user can reorder, rename and hide
// them from the form.
const DEFAULT_SECTION_ORDER = [
  "summary", "education", "projects", "university_projects", "internships",
  "work", "skills", "languages", "references",
];

// Visible default name of every section and block anchor.
const ANCHOR_NAME_KEYS = {
  start: "section_start",
  summary: "section_summary",
  education: "section_education",
  projects: "section_projects",
  university_projects: "section_university_projects",
  internships: "section_internships",
  work: "section_work",
  skills: "section_skills",
  languages: "section_languages",
  references: "section_references",
  end: "section_end",
};

/* ---------------- standard sections: name, order and visibility ---------------- */

function savedSectionTitle(key) {
  const titles = state.data ? state.data.section_titles : null;
  if (!titles || typeof titles !== "object") return "";
  const value = titles[key];
  return value == null ? "" : String(value);
}

// Visible label of a section: the custom title if present; otherwise the
// localized default name.
function sectionName(key) {
  const custom = savedSectionTitle(key).trim();
  if (custom) return custom;
  if (ANCHOR_NAME_KEYS[key]) return t(ANCHOR_NAME_KEYS[key]);
  if (DYNAMIC_SECTIONS[key]) return t(DYNAMIC_SECTIONS[key].titleKey);
  return String(key);
}

// Effective order of the standard sections: valid keys only, no duplicates
// (the first one wins) and missing keys appended at the end in default order.
// Never mutates state.data: the full list is materialized when reordering.
function sectionOrder() {
  const raw = state.data && Array.isArray(state.data.section_order) ? state.data.section_order : [];
  const order = [];
  raw.forEach((value) => {
    if (typeof value !== "string") return;
    if (DEFAULT_SECTION_ORDER.indexOf(value) >= 0 && order.indexOf(value) < 0) order.push(value);
  });
  DEFAULT_SECTION_ORDER.forEach((key) => {
    if (order.indexOf(key) < 0) order.push(key);
  });
  return order;
}

function isSectionHidden(key) {
  const hidden = state.data ? state.data.hidden_sections : null;
  return Array.isArray(hidden) && hidden.indexOf(key) >= 0;
}

// Free block anchors: start + standard sections in their current order + end.
function blockAnchorsUI() {
  return ["start"].concat(sectionOrder(), ["end"]);
}

/* ---------------- utilities ---------------- */

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function setStatus(key, cls, suffix) {
  state.statusKey = key || "";
  state.statusSuffix = suffix || "";
  state.statusClass = cls || "";
  renderStatus();
}

function renderStatus() {
  const el = $("#status");
  if (!el) return;
  el.textContent = state.statusKey
    ? t(state.statusKey) + (state.statusSuffix ? " " + state.statusSuffix : "")
    : "";
  el.dataset.status = state.statusClass || "";
}

function toast(message) {
  const el = $("#toasts");
  el.textContent = message;
  el.hidden = false;
  clearTimeout(state._toastTimer);
  state._toastTimer = setTimeout(() => (el.hidden = true), 3500);
}

let _confirmAccept = null;
let _confirmCancel = null;

function resetConfirmLabels() {
  $("#confirm-accept").textContent = t("confirm_ok");
  $("#confirm-cancel").textContent = t("cancel");
  $("#confirm-accept").hidden = false;
  $("#confirm-exit").hidden = true;
  $("#confirm-cancel").hidden = false;
}

function closeModal(modal) {
  if (!modal) return;
  modal.hidden = true;
  if (modal.id === "modal-confirm") {
    _confirmAccept = null;
    _confirmCancel = null;
    resetConfirmLabels();
  }
}

function askConfirm(message, onAccept, onCancel, acceptLabel, cancelLabel) {
  $("#confirm-message").textContent = message;
  _confirmAccept = onAccept || null;
  _confirmCancel = onCancel || null;
  $("#confirm-accept").textContent = acceptLabel || t("confirm_ok");
  $("#confirm-cancel").textContent = cancelLabel || t("cancel");
  $("#confirm-accept").hidden = false;
  $("#confirm-exit").hidden = true;
  $("#confirm-cancel").hidden = false;
  $("#modal-confirm").hidden = false;
}

function showAlert(message) {
  $("#confirm-message").textContent = message;
  _confirmAccept = null;
  _confirmCancel = null;
  resetConfirmLabels();
  $("#confirm-cancel").hidden = true;
  $("#modal-confirm").hidden = false;
}

function formatBytes(bytes) {
  return (bytes / 1048576).toFixed(1) + " MB";
}

/* ---------------- menus ---------------- */

function closeMenus() {
  $$(".menu.open").forEach((menu) => menu.classList.remove("open"));
}

function updateMarks() {
  const menus = $("#menus");
  const mark = (selector) => menus.querySelector(selector);
  // The auto-compile mark lived in the removed preview menu; #auto-button
  // below still reflects the same pref.
  const latexLink = menus.querySelector('[data-accion="toggle:latex"]');
  if (latexLink) latexLink.classList.toggle("active", state.mode === "latex");
  const activeTheme = document.documentElement.getAttribute("data-theme") || "system";
  THEMES.forEach((theme) => {
    const m = mark('[data-marca="theme-' + theme + '"]');
    if (m) m.textContent = theme === activeTheme ? "✓" : "";
  });
  const activeTemplate = state.data && state.data.template ? state.data.template : "classic";
  TEMPLATES_CV.forEach((tpl) => {
    const m = mark('[data-marca="template-' + tpl.value + '"]');
    if (m) m.textContent = tpl.value === activeTemplate ? "✓" : "";
  });
  const button = $("#auto-button");
  if (button) button.classList.toggle("active", !!(state.prefs && state.prefs.auto_compile));
}

$$(".menu-btn").forEach((button) => {
  button.addEventListener("click", (e) => {
    e.stopPropagation();
    const menu = button.closest(".menu");
    const wasOpen = menu.classList.contains("open");
    closeMenus();
    if (!wasOpen) menu.classList.add("open");
  });
});
document.addEventListener("click", closeMenus);

/* ---------------- theme (light / dark / system) ---------------- */

function applyTheme(theme) {
  const value = THEMES.indexOf(theme) >= 0 ? theme : "system";
  document.documentElement.dataset.theme = value;
}

function changeTheme(theme) {
  state.prefs.theme = theme;
  api.set_prefs("theme", theme);
  applyTheme(theme);
  updateMarks();
}

/* ---------------- actions ---------------- */

document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-accion]");
  if (el) runAction(el.dataset.accion, e);
});

function runAction(action, e) {
  if (action.startsWith("paper:")) applyPaper(action.split(":")[1]);
  else if (action.startsWith("margins:")) applyMargins(action.split(":")[1]);
  else if (action.startsWith("font:")) applyFontSize(Number(action.split(":")[1]));
  else if (action.startsWith("theme:")) changeTheme(action.split(":")[1]);
  else if (action.startsWith("template:")) applyTemplate(action.split(":")[1]);
  else if (action.startsWith("zoom:")) applyZoom(Number(action.split(":")[1]));
  else if (action.startsWith("toggle:")) toggleOption(action.split(":")[1]);
  else if (action.startsWith("add:columns:")) {
    openListBlockModal("columns", null, Number(action.split(":")[2]));
  }
  else {
    switch (action) {
      case "undo": undo(); break;
      case "redo": redo(); break;
      case "new": newCv(); break;
      case "open": openCv(); break;
      case "save": saveCurrentCv(); break;
      case "export-pdf": exportPdf(); break;
      case "export-tex": exportTex(); break;
      case "export-docx": exportDocx(); break;
      case "import-tex": importTex(); break;
      case "load-sample": loadSample(); break;
      case "reset-all": newCv(); break;
      case "settings": case "setup-engine": openPrefs(); break;
      case "recompile": clearTimeout(state.timer); compileNow(); break;
      case "open-preview": openPreview(); break;
      case "add:block-line": createSeparatorBlock("line"); break;
      case "add:block-band": createSeparatorBlock("band"); break;
      case "add:block-space": createSeparatorBlock("space"); break;
      case "add:section": openCustomSectionModal(null); break;
      case "add:period": openListBlockModal("period", null); break;
      case "manage-blocks": openBlocksModal(); break;
      case "help": $("#modal-help").hidden = false; break;
      case "credits": $("#modal-credits").hidden = false; break;
      case "exit-without-saving": if (api) api.quit_app(); break;
      case "close-modal": {
        const modal = e && e.target && e.target.closest ? e.target.closest(".modal") : null;
        if (modal) closeModal(modal);
        break;
      }
    }
  }
}

function dataHasContent(data) {
  if (!emptyData || !data) return false;
  return Object.keys(emptyData).some(
    (key) => key !== "template" && JSON.stringify(data[key]) !== JSON.stringify(emptyData[key])
  );
}

function hasContent() {
  return dataHasContent(state.data);
}

async function newCv() {
  askConfirm(t("confirm_new"), () => {
    if (state.mode === "latex") exitLatexMode(false);
    state.data = JSON.parse(JSON.stringify(emptyData));
    state.filePath = null;
    clearHistory();
    renderForm();
    updateMarks();
    markDirty(false);
    clearAutosave();
    scheduleCompile();
    toast(t("toast_new"));
  });
}

async function openCv() {
  const r = await api.open_cv();
  if (r.ok && r.datos) {
    const apply = () => {
      if (state.mode === "latex") exitLatexMode(false);
      state.data = r.datos;
      state.filePath = r.ruta || null;
      clearHistory();
      renderForm();
      updateMarks();
      markDirty(false);
      clearAutosave();
      scheduleCompile();
      toast(t("toast_opened").replace("{path}", r.ruta));
    };
    if (hasContent()) {
      askConfirm(t("confirm_open_replace"), apply);
    } else {
      apply();
    }
  } else if (r.errores) {
    toast(r.errores[0]);
  }
}

async function saveCurrentCv() {
  const r = await api.export_cv(state.data);
  if (r.ok) {
    state.filePath = r.ruta;
    markDirty(false);
    await clearAutosave();
    toast(t("toast_saved").replace("{path}", r.ruta));
  } else if (r.errores) {
    toast(r.errores[0]);
  }
}

/* Close guard: Save / Exit without saving / Cancel. Saving writes to the
   current .cvjson when known, otherwise it opens the save dialog. On any
   failure (or a cancelled dialog) the guard is shown again so the window is
   never closed with unsaved changes by accident. */
async function saveAndExit() {
  try {
    if (state.filePath) {
      const r = await api.export_cv(state.data, state.filePath);
      if (r.ok) {
        markDirty(false);
        await clearAutosave();
        api.quit_app();
      } else {
        toast((r.errores && r.errores[0]) || t("close_guard_save_failed"));
        window.__onCloseRequest();
      }
    } else {
      const r = await api.export_cv(state.data);
      if (r.ok) {
        state.filePath = r.ruta;
        markDirty(false);
        await clearAutosave();
        api.quit_app();
      } else if (r.cancelado) {
        // The user cancelled the save dialog: stay in the app, guard usable.
        window.__onCloseRequest();
      } else {
        toast((r.errores && r.errores[0]) || t("close_guard_save_failed"));
        window.__onCloseRequest();
      }
    }
  } catch (e) {
    console.error(e);
    window.__onCloseRequest();
  }
}

async function exportPdf() {
  const manualTex = state.mode === "latex" ? state.texManual : null;
  const r = await api.export_pdf(state.data, manualTex);
  if (r.ok) toast(t("toast_pdf_exported").replace("{path}", r.ruta));
  else if (r.errores) toast(r.errores[0]);
}

async function exportTex() {
  const manualTex = state.mode === "latex" ? state.texManual : null;
  const r = await api.export_tex(state.data, manualTex);
  if (r.ok) toast(t("toast_tex_exported").replace("{path}", r.ruta));
  else if (r.errores) toast(r.errores[0]);
}

async function exportDocx() {
  const r = await api.export_docx(state.data);
  if (r.ok) toast(t("toast_docx_exported").replace("{path}", r.ruta));
  else if (r.errores) toast(r.errores[0]);
}

async function importTex() {
  const r = await api.import_tex();
  if (r.ok && r.datos) {
    const apply = () => {
      if (state.mode === "latex") exitLatexMode(false);
      state.data = r.datos;
      state.filePath = null;
      clearHistory();
      renderForm();
      updateMarks();
      markDirty(false);
      clearAutosave();
      scheduleCompile();
      toast(t("toast_tex_imported").replace("{path}", r.ruta));
    };
    if (hasContent()) {
      askConfirm(t("confirm_import_replace"), apply);
    } else {
      apply();
    }
  } else if (r.errores) {
    showAlert(r.errores[0]);
  }
}

async function loadSample() {
  const apply = async () => {
    const r = await api.load_sample(state.data.template);
    if (!r.ok) {
      toast((r.errores && r.errores[0]) || t("toast_sample_error"));
      return;
    }
    if (state.mode === "latex") exitLatexMode(false);
    state.data = r.datos;
    state.filePath = null;
    clearHistory();
    renderForm();
    updateMarks();
    markDirty(false);
    clearAutosave();
    scheduleCompile();
    toast(t("toast_sample_loaded"));
  };
  if (hasContent()) {
    askConfirm(t("confirm_sample_replace"), apply);
  } else {
    apply();
  }
}

function applyPaper(paper) {
  state.prefs.paper = paper;
  api.set_prefs("paper", paper);
  markDirty(true);
}

function applyMargins(value) {
  if (value === "custom") {
    openMarginsModal();
    return;
  }
  const margins = value === "normal"
    ? { top: 2, bottom: 2, left: 2, right: 2 }
    : { top: 1, bottom: 1, left: 1, right: 1 };
  state.prefs.margins = margins;
  api.set_prefs("margins", margins);
  markDirty(true);
}

function applyFontSize(size) {
  state.prefs.font_size = size;
  api.set_prefs("font_size", size);
  markDirty(true);
}

function applyTemplate(value) {
  const valid = TEMPLATES_CV.some((tpl) => tpl.value === value);
  recordHistory(true);
  state.data.template = valid ? value : "classic";
  markDirty(true);
  updateMarks();
}

function toggleOption(option) {
  if (option === "auto-compile") {
    state.prefs.auto_compile = !state.prefs.auto_compile;
    api.set_prefs("auto_compile", state.prefs.auto_compile);
    updateMarks();
    if (state.prefs.auto_compile) scheduleCompile();
  } else if (option === "latex") {
    if (state.mode === "latex") {
      const edited = state.texEdited;
      askConfirm(
        edited ? t("confirm_exit_latex_edited") : t("confirm_back_to_form"),
        () => exitLatexMode(true)
      );
    } else {
      enterLatexMode();
    }
  }
}

/* ---------------- compilation ---------------- */

function scheduleCompile() {
  if (!state.prefs || !state.prefs.auto_compile) return;
  clearTimeout(state.timer);
  state.timer = setTimeout(compileNow, 400);
}

async function compileNow() {
  if (!api || (state.mode === "latex" && state.texManual == null && !state.tex)) return;
  const id = ++state.compileId;
  state.preview = { state: "compiling" };
  renderPreviewStatus();
  if (state.mode === "latex") {
    await api.compile_tex(state.texManual !== null ? state.texManual : state.tex, id, state.data);
  } else {
    await api.compile(state.data, id);
  }
}

function renderPreviewStatus() {
  const el = $("#preview-status");
  if (!el) return;
  const preview = state.preview || { state: "idle" };
  el.className = preview.state === "idle" ? "" : preview.state;
  if (preview.state === "compiling") el.textContent = t("compiling");
  else if (preview.state === "ok") el.textContent = t("preview_ready");
  else if (preview.state === "error") el.textContent = t("compile_errors").replace("{n}", preview.errors || 0);
  else el.textContent = t("waiting");
}

/* Linux webviews cannot render PDFs inline: show the notice with the button
   that opens the last compiled PDF with the system viewer. Hidden elsewhere. */
function setupPreviewFallback(platform) {
  const notice = $("#preview-notice");
  if (!notice) return;
  notice.hidden = platform !== "linux";
}

async function openPreview() {
  const r = await api.open_preview();
  if (r && r.ok) return;
  const message = r && r.errores && r.errores.length ? r.errores[0] : t("preview_linux_notice");
  toast(message);
}

/* ---------------- preview zoom ---------------- */

// The #zoom=<pct>&view=FitH fragment is interpreted by the PDF viewer. If the
// embedded WebView2 viewer ignores it, the fallback is the page-sized PDF: the
// zoom is only a visual setting and never affects the .tex nor the PDF.
function applyZoom(pct) {
  const values = [75, 100, 125];
  const value = values.indexOf(Number(pct)) >= 0 ? Number(pct) : (state.zoom || 100);
  state.zoom = value;
  values.forEach((v) => {
    const button = $("#zoom-" + v);
    if (button) button.classList.toggle("active", v === value);
  });
  const pdf = $("#pdf");
  if (pdf) pdf.src = "/preview/main.pdf?v=" + Date.now() + "#zoom=" + value + "&view=FitH";
}

window.__onCompile = function (res) {
  if (res.id !== state.compileId) return;
  if (res.ok) {
    $("#errors").hidden = true;
    $("#engine-warning").hidden = true;
    applyZoom(state.zoom);
    state.preview = { state: "ok" };
    renderPreviewStatus();
    setStatus("");
  } else {
    state.preview = { state: "error", errors: res.errores.length };
    renderPreviewStatus();
    const box = $("#errors");
    box.innerHTML = "<ul>" + res.errores.map((e) => "<li>" + escapeHtml(e) + "</li>").join("") + "</ul>";
    box.hidden = false;
    setStatus("compile_failed", "error");
  }
  if (res.tex) state.tex = res.tex;
  if (state.mode === "latex" && state.texManual === null && res.tex) {
    const area = $("#latex-text");
    if (area) area.value = res.tex;
  }
};

/* ---------------- autosave and dirty tracking ---------------- */

let _autosaveTimer = null;

// Close guard: keep the backend dirty flag in sync with the form. Any
// document-changing edit sets it; a successful save/open/new/import clears it.
function markDirty(flag) {
  state.dirty = !!flag;
  if (api) api.set_dirty(state.dirty);
  if (flag) {
    clearTimeout(_autosaveTimer);
    _autosaveTimer = setTimeout(autosaveNow, 5000);
    scheduleCompile();
  }
}

async function autosaveNow() {
  if (!api || !state.dirty || !state.data) return;
  try {
    await api.autosave(state.data);
  } catch (e) {
    console.error(e);
  }
}

async function clearAutosave() {
  if (!api) return;
  try {
    await api.autosave_clear();
  } catch (e) {
    console.error(e);
  }
}

window.__onCloseRequest = function () {
  _confirmAccept = saveAndExit;
  _confirmCancel = null;
  $("#confirm-message").textContent = t("close_guard_message");
  $("#confirm-accept").hidden = false;
  $("#confirm-accept").textContent = t("save");
  $("#confirm-exit").hidden = false;
  $("#confirm-exit").textContent = t("exit_without_saving");
  $("#confirm-cancel").hidden = false;
  $("#confirm-cancel").textContent = t("cancel");
  $("#modal-confirm").hidden = false;
};

/* ---------------- undo / redo ---------------- */

const HISTORY_LIMIT = 50;
const HISTORY_COALESCE_MS = 600;

let _historyTs = 0;
let _historyStructural = false;

function deepCopy(o) {
  return JSON.parse(JSON.stringify(o));
}

function clearHistory() {
  state.undoStack = [];
  state.redoStack = [];
  _historyTs = 0;
  _historyStructural = false;
  updateHistoryButtons();
}

/* Store a snapshot of state.data before mutating it. Consecutive non
   structural changes (e.g. typing) are grouped during 600 ms: only the
   snapshot of the first change of the burst is kept. Structural actions
   (blocks, entries, template, columns, language) always push a new entry. */
function recordHistory(structural) {
  if (!state.data) return;
  const now = Date.now();
  const recent = now - _historyTs < HISTORY_COALESCE_MS;
  _historyTs = now;
  if (!structural && recent && !_historyStructural && state.undoStack.length) {
    state.redoStack = [];
    updateHistoryButtons();
    return;
  }
  state.undoStack.push(deepCopy(state.data));
  if (state.undoStack.length > HISTORY_LIMIT) state.undoStack.shift();
  state.redoStack = [];
  _historyStructural = !!structural;
  updateHistoryButtons();
}

function updateHistoryButtons() {
  const setEnabled = (action, enabled) => {
    const link = $("#menus [data-accion='" + action + "']");
    if (!link) return;
    link.classList.toggle("disabled", !enabled);
    link.setAttribute("aria-disabled", enabled ? "false" : "true");
  };
  setEnabled("undo", !!(state.undoStack && state.undoStack.length));
  setEnabled("redo", !!(state.redoStack && state.redoStack.length));
}

function applyHistorySnapshot() {
  _historyTs = 0;
  _historyStructural = false;
  renderForm();
  updateMarks();
  updateHistoryButtons();
  markDirty(true);
}

function undo() {
  if (!state.data || !state.undoStack.length) return;
  if (state.mode === "latex") return; // in LaTeX mode the textarea undo wins
  state.redoStack.push(deepCopy(state.data));
  state.data = state.undoStack.pop();
  applyHistorySnapshot();
}

function redo() {
  if (!state.data || !state.redoStack.length) return;
  if (state.mode === "latex") return;
  state.undoStack.push(deepCopy(state.data));
  state.data = state.redoStack.pop();
  applyHistorySnapshot();
}

function offerRecovery(data) {
  askConfirm(
    t("confirm_recover"),
    () => {
      if (state.mode === "latex") exitLatexMode(false);
      const base = JSON.parse(JSON.stringify(emptyData || {}));
      Object.keys(data).forEach((key) => { base[key] = data[key]; });
      state.data = base;
      clearHistory();
      renderForm();
      updateMarks();
      markDirty(true);
      compileNow();
      toast(t("toast_recovered"));
    },
    () => {
      clearAutosave();
      markDirty(false);
      toast(t("toast_discarded"));
    },
    t("recover"),
    t("discard")
  );
}

/* ---------------- form ---------------- */

/* Collapse state of cards and entries. It is UI-only state: it lives in this
   in-memory map, is applied on every render and is NEVER saved into the
   .cvjson nor the autosave (it is not part of state.data). */
const collapseUI = { sections: {}, entries: {}, blocks: {} };

function isCollapsed(type, key) {
  return !!collapseUI[type][key];
}

function applyCollapse(type, key, el) {
  if (el) el.classList.toggle("collapsed", isCollapsed(type, key));
}

function toggleCollapse(type, key, el) {
  collapseUI[type][key] = !collapseUI[type][key];
  if (el) el.classList.toggle("collapsed", collapseUI[type][key]);
}

function sectionCard(text, key, standard) {
  const card = document.createElement("div");
  card.className = "section-card";
  const header = document.createElement("div");
  header.className = "section-header";
  const chevron = document.createElement("span");
  chevron.className = "chevron";
  chevron.textContent = "▾";
  header.appendChild(chevron);
  if (standard) {
    // Inline title: writes/removes state.data.section_titles[key]; empty falls
    // back to the default name (the placeholder shows that name).
    const input = document.createElement("input");
    input.type = "text";
    input.className = "section-title-input";
    input.dataset.key = key;
    input.value = savedSectionTitle(key);
    input.placeholder = text;
    input.title = t("rename_section_tip");
    input.addEventListener("click", (e) => e.stopPropagation());
    input.addEventListener("input", () => {
      recordHistory(true);
      if (!state.data.section_titles || typeof state.data.section_titles !== "object") {
        state.data.section_titles = {};
      }
      const value = input.value.trim();
      if (value) state.data.section_titles[key] = value;
      else delete state.data.section_titles[key];
      markDirty(true);
    });
    // The repaint is delayed to the next turn so the input blur does not
    // destroy the header buttons before their click.
    input.addEventListener("change", () => setTimeout(renderForm, 0));
    header.appendChild(input);
  } else {
    const heading = document.createElement("h3");
    heading.textContent = text;
    header.appendChild(heading);
  }
  if (key && DYNAMIC_SECTIONS[key] && DYNAMIC_SECTIONS[key].columns) {
    if (!state.data.columns) state.data.columns = {};
    const label = document.createElement("label");
    label.className = "column-label";
    label.textContent = t("columns_label");
    const select = document.createElement("select");
    select.className = "column-select";
    [1, 2, 3].forEach((n) => {
      const option = document.createElement("option");
      option.value = n;
      option.textContent = n;
      select.appendChild(option);
    });
    select.value = String(state.data.columns[key] || 1);
    select.title = t("columns_tip");
    select.addEventListener("click", (e) => e.stopPropagation());
    select.addEventListener("change", () => {
      recordHistory(true);
      state.data.columns[key] = Number(select.value);
      markDirty(true);
    });
    label.appendChild(select);
    header.appendChild(label);
  }
  if (standard) {
    const hidden = isSectionHidden(key);
    const order = sectionOrder();
    const position = order.indexOf(key);

    const controls = document.createElement("span");
    controls.className = "section-controls";

    const visibility = document.createElement("button");
    visibility.className = "section-hide-button" + (hidden ? " hidden-section" : "");
    visibility.textContent = hidden ? "○" : "◉";
    visibility.title = hidden ? t("show_section") : t("hide_section");
    visibility.addEventListener("click", (e) => {
      e.stopPropagation();
      recordHistory(true);
      if (!Array.isArray(state.data.hidden_sections)) state.data.hidden_sections = [];
      const i = state.data.hidden_sections.indexOf(key);
      if (i >= 0) state.data.hidden_sections.splice(i, 1);
      else state.data.hidden_sections.push(key);
      markDirty(true);
      renderForm();
    });

    const up = document.createElement("button");
    up.className = "section-up-button";
    up.textContent = "↑";
    up.title = t("move_section_up");
    up.disabled = position <= 0;
    up.addEventListener("click", (e) => {
      e.stopPropagation();
      const current = sectionOrder();
      const j = current.indexOf(key);
      if (j <= 0) return;
      recordHistory(true);
      const tmp = current[j - 1];
      current[j - 1] = current[j];
      current[j] = tmp;
      state.data.section_order = current;
      markDirty(true);
      renderForm();
    });

    const down = document.createElement("button");
    down.className = "section-down-button";
    down.textContent = "↓";
    down.title = t("move_section_down");
    down.disabled = position < 0 || position >= order.length - 1;
    down.addEventListener("click", (e) => {
      e.stopPropagation();
      const current = sectionOrder();
      const j = current.indexOf(key);
      if (j < 0 || j >= current.length - 1) return;
      recordHistory(true);
      const tmp = current[j + 1];
      current[j + 1] = current[j];
      current[j] = tmp;
      state.data.section_order = current;
      markDirty(true);
      renderForm();
    });

    controls.append(visibility, up, down);
    header.appendChild(controls);
  }
  const content = document.createElement("div");
  content.className = "section-content";
  card.appendChild(header);
  card.appendChild(content);
  card.content = content;
  const collapseKey = key || text;
  applyCollapse("sections", collapseKey, card);
  header.addEventListener("click", (e) => {
    if (e.target.closest("select, button, input")) return;
    toggleCollapse("sections", collapseKey, card);
  });
  return card;
}

function basicField(key, label, area) {
  const div = document.createElement("div");
  div.className = "field" + (area ? " wide" : "");
  const lb = document.createElement("label");
  lb.textContent = label;
  const input = document.createElement(area ? "textarea" : "input");
  input.value = state.data[key] || "";
  input.addEventListener("input", () => {
    recordHistory(false);
    state.data[key] = input.value;
    markDirty(true);
  });
  div.append(lb, input);
  return div;
}

/* Scale the longest side of an image served from /media/ down to maxSide
   (never upscales) and return a data URL (JPEG/PNG) to send to save_image.
   The canvas is readable because the image is same-origin; if the image fails
   to load or the canvas cannot be read (e.g. tainted), it rejects: the caller
   then keeps the original path. */
function normalizeImage(sourceUrl, maxSide, mime, quality) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      try {
        const longest = Math.max(img.naturalWidth, img.naturalHeight);
        const scale = longest > maxSide ? maxSide / longest : 1;
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(img.naturalWidth * scale));
        canvas.height = Math.max(1, Math.round(img.naturalHeight * scale));
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL(mime, quality));
      } catch (e) {
        reject(e);
      }
    };
    img.onerror = () => reject(new Error("Could not load the image"));
    img.src = sourceUrl;
  });
}

function paintPhoto() {
  const view = $("#photo-preview");
  if (!view) return;
  if (!state.data.photo) {
    view.textContent = t("no_photo");
    view.style.width = "64px";
    view.style.height = "80px";
    view.style.padding = "0 4px";
    const button = $("#photo-adjust-button");
    if (button) button.hidden = true;
    return;
  }
  view.innerHTML = "";
  view.style.padding = "0";
  const width = Number(state.data.photo_width_cm) || 4;
  const height = Number(state.data.photo_height_cm) || 5;
  view.style.width = "64px";
  view.style.height = Math.min(96, Math.max(50, Math.round((64 * height) / width))) + "px";
  const img = document.createElement("img");
  img.src = "/media/" + encodeURIComponent(state.data.photo.split(/[\\/]/).pop());
  view.appendChild(img);
  const button = $("#photo-adjust-button");
  if (button) button.hidden = false;
}

function photoRow() {
  const row = document.createElement("div");
  row.className = "photo-row";
  const view = document.createElement("div");
  view.className = "photo-preview";
  view.id = "photo-preview";
  const controls = document.createElement("div");
  controls.className = "field";
  const label = document.createElement("label");
  label.textContent = t("field_photo");
  const buttons = document.createElement("div");
  const choose = document.createElement("button");
  choose.className = "small";
  choose.textContent = t("choose_photo");
  const adjust = document.createElement("button");
  adjust.className = "small";
  adjust.id = "photo-adjust-button";
  adjust.textContent = t("adjust_area");
  adjust.hidden = true;
  const remove = document.createElement("button");
  remove.className = "small";
  remove.textContent = t("remove");
  buttons.append(choose, adjust, remove);
  buttons.style.display = "flex";
  buttons.style.gap = "8px";
  buttons.style.flexWrap = "wrap";

  const size = document.createElement("div");
  size.className = "photo-size";
  const widthLabel = document.createElement("label");
  widthLabel.textContent = t("width_cm");
  const widthInput = document.createElement("input");
  widthInput.type = "number";
  widthInput.min = "1";
  widthInput.max = "12";
  widthInput.step = "0.5";
  const heightLabel = document.createElement("label");
  heightLabel.textContent = t("height_cm");
  const heightInput = document.createElement("input");
  heightInput.type = "number";
  heightInput.min = "1";
  heightInput.max = "15";
  heightInput.step = "0.5";
  size.append(widthLabel, widthInput, heightLabel, heightInput);

  controls.append(label, buttons, size);
  row.append(view, controls);

  const updateSize = () => {
    widthInput.value = Number(state.data.photo_width_cm) || 4;
    heightInput.value = Number(state.data.photo_height_cm) || 5;
  };
  const applySize = () => {
    recordHistory(false);
    state.data.photo_width_cm = Number(widthInput.value) || 4;
    state.data.photo_height_cm = Number(heightInput.value) || 5;
    markDirty(true);
  };
  widthInput.addEventListener("change", () => { applySize(); paintPhoto(); });
  heightInput.addEventListener("change", () => { applySize(); paintPhoto(); });
  choose.onclick = async () => {
    const r = await api.choose_photo("foto");
    if (!r.ok) {
      if (r.error) toast(r.error);
      return;
    }
    recordHistory(false);
    let path = r.path;
    let normalized = false;
    try {
      const dataUrl = await normalizeImage(r.url, 1600, "image/jpeg", 0.9);
      const saved = await api.save_image(dataUrl, "foto");
      if (saved.ok && saved.path) {
        path = saved.path;
        normalized = true;
      } else {
        toast((saved.errores && saved.errores[0]) || t("toast_photo_normalize_error"));
      }
    } catch (e) {
      toast(t("toast_photo_normalize_error"));
    }
    state.data.photo = path;
    state.data.photo_original = path;
    state.data.photo_crop = { x: 0, y: 0, w: 1, h: 1 };
    updateSize();
    paintPhoto();
    markDirty(true);
    // Automatic crop over the full normalized image; if the user cancels, the
    // whole normalized image stays saved.
    if (normalized) openCrop();
  };
  adjust.onclick = () => openCrop();
  remove.onclick = () => {
    recordHistory(false);
    state.data.photo = "";
    state.data.photo_original = "";
    state.data.photo_crop = null;
    paintPhoto();
    markDirty(true);
  };
  updateSize();
  return row;
}

/* ---------------- photo crop ---------------- */

let _crop = { img: null, container: null, box: null };

function openCrop() {
  const source = state.data.photo_original || state.data.photo;
  if (!source) return;
  const img = new Image();
  img.onload = () => {
    _crop.img = img;
    $("#modal-crop").hidden = false;
    mountCrop();
  };
  img.onerror = () => toast(t("toast_crop_load_error"));
  img.src = "/media/" + encodeURIComponent(source.split(/[\\/]/).pop());
}

function placeCropBox(x, y, w, h) {
  const box = _crop.box;
  if (!box) return;
  box.style.left = x + "px";
  box.style.top = y + "px";
  box.style.width = w + "px";
  box.style.height = h + "px";
}

function mountCrop() {
  const container = $("#crop-container");
  container.innerHTML = "";
  const img = _crop.img;
  const maxW = 480;
  const maxH = 400;
  const scale = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight);
  const w = Math.round(img.naturalWidth * scale);
  const h = Math.round(img.naturalHeight * scale);
  container.style.width = w + "px";
  container.style.height = h + "px";
  const im = document.createElement("img");
  im.src = img.src;
  container.appendChild(im);
  const box = document.createElement("div");
  box.className = "crop-box";
  ["nw", "ne", "sw", "se"].forEach((corner) => {
    const handle = document.createElement("div");
    handle.className = "crop-handle crop-" + corner;
    handle.dataset.corner = corner;
    box.appendChild(handle);
  });
  container.appendChild(box);
  _crop.container = container;
  _crop.box = box;

  const rect = state.data.photo_crop || { x: 0, y: 0, w: 1, h: 1 };
  placeCropBox(rect.x * w, rect.y * h, Math.max(24, rect.w * w), Math.max(24, rect.h * h));
  bindCrop();
}

function bindCrop() {
  const container = _crop.container;
  const box = _crop.box;
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

  box.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    const handle = e.target.closest(".crop-handle");
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    const startX = e.clientX;
    const startY = e.clientY;
    const rect = {
      x: parseFloat(box.style.left) || 0,
      y: parseFloat(box.style.top) || 0,
      w: parseFloat(box.style.width) || containerWidth,
      h: parseFloat(box.style.height) || containerHeight,
    };
    const onMove = (ev) => {
      const dx = ev.clientX - startX;
      const dy = ev.clientY - startY;
      if (!handle) {
        placeCropBox(
          clamp(rect.x + dx, 0, containerWidth - rect.w),
          clamp(rect.y + dy, 0, containerHeight - rect.h),
          rect.w,
          rect.h
        );
      } else {
        let nx = rect.x, ny = rect.y, nw = rect.w, nh = rect.h;
        if (handle.dataset.corner.includes("e")) nw = clamp(rect.w + dx, 24, containerWidth - rect.x);
        if (handle.dataset.corner.includes("s")) nh = clamp(rect.h + dy, 24, containerHeight - rect.y);
        if (handle.dataset.corner.includes("w")) {
          nw = clamp(rect.w - dx, 24, rect.x + rect.w);
          nx = rect.x + rect.w - nw;
        }
        if (handle.dataset.corner.includes("n")) {
          nh = clamp(rect.h - dy, 24, rect.y + rect.h);
          ny = rect.y + rect.h - nh;
        }
        placeCropBox(nx, ny, nw, nh);
      }
    };
    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
  });
}

function setupCrop() {
  $("#crop-cancel").addEventListener("click", () => {
    $("#modal-crop").hidden = true;
  });
  $("#crop-apply").addEventListener("click", async () => {
    const container = _crop.container;
    const img = _crop.img;
    const box = _crop.box;
    if (!container || !img || !box) return;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    const x = parseFloat(box.style.left) / containerWidth;
    const y = parseFloat(box.style.top) / containerHeight;
    const w = parseFloat(box.style.width) / containerWidth;
    const h = parseFloat(box.style.height) / containerHeight;
    const round = (v) => Math.round(v * 1000) / 1000;
    recordHistory(false);
    state.data.photo_crop = { x: round(x), y: round(y), w: round(w), h: round(h) };
    const sx = x * img.naturalWidth;
    const sy = y * img.naturalHeight;
    const sw = w * img.naturalWidth;
    const sh = h * img.naturalHeight;
    const maxPixels = 1600;
    const longest = Math.max(sw, sh);
    const scale = longest > maxPixels ? maxPixels / longest : 1;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(sw * scale);
    canvas.height = Math.round(sh * scale);
    canvas.getContext("2d").drawImage(img, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
    const r = await api.save_image(dataUrl, "recorte");
    if (r.ok) {
      state.data.photo = r.path;
      $("#modal-crop").hidden = true;
      paintPhoto();
      markDirty(true);
      toast(t("toast_crop_applied"));
    } else {
      toast((r.errores && r.errores[0]) || t("toast_crop_save_error"));
    }
  });
}

function renderDynamicList(key) {
  const def = DYNAMIC_SECTIONS[key];
  const wrap = document.createElement("div");

  const paint = () => {
    wrap.innerHTML = "";
    const list = state.data[key];
    if (!list.length) {
      const p = document.createElement("p");
      p.className = "no-entries";
      p.textContent = t("no_entries");
      wrap.appendChild(p);
    }
    list.forEach((entry, idx) => {
      const div = document.createElement("div");
      div.className = "entry";
      const entryKey = key + ":" + idx;
      applyCollapse("entries", entryKey, div);
      const header = document.createElement("div");
      header.className = "entry-header";
      const label = document.createElement("span");
      label.className = "entry-label";
      const chevron = document.createElement("span");
      chevron.className = "chevron";
      chevron.textContent = "▾";
      label.append(chevron, document.createTextNode(" " + t(def.titleKey).replace(/s$/, "") + " " + (idx + 1)));
      const actions = document.createElement("span");
      actions.className = "entry-actions";

      const duplicate = document.createElement("button");
      duplicate.className = "small";
      duplicate.textContent = "⧉";
      duplicate.title = t("entry_duplicate");
      duplicate.onclick = (e) => {
        e.stopPropagation();
        recordHistory(true);
        const copy = JSON.parse(JSON.stringify(entry));
        state.data[key].splice(idx + 1, 0, copy);
        paint();
        markDirty(true);
      };

      const up = document.createElement("button");
      up.className = "small";
      up.textContent = "↑";
      up.title = t("entry_up");
      up.disabled = idx === 0;
      up.onclick = (e) => {
        e.stopPropagation();
        const l = state.data[key];
        if (idx <= 0) return;
        recordHistory(true);
        const tmp = l[idx - 1];
        l[idx - 1] = l[idx];
        l[idx] = tmp;
        paint();
        markDirty(true);
      };

      const down = document.createElement("button");
      down.className = "small";
      down.textContent = "↓";
      down.title = t("entry_down");
      down.disabled = idx >= list.length - 1;
      down.onclick = (e) => {
        e.stopPropagation();
        const l = state.data[key];
        if (idx >= l.length - 1) return;
        recordHistory(true);
        const tmp = l[idx + 1];
        l[idx + 1] = l[idx];
        l[idx] = tmp;
        paint();
        markDirty(true);
      };

      const remove = document.createElement("button");
      remove.className = "remove-button";
      remove.textContent = "✕";
      remove.title = t("entry_delete");
      remove.onclick = (e) => {
        e.stopPropagation();
        recordHistory(true);
        state.data[key].splice(idx, 1);
        paint();
        markDirty(true);
      };

      actions.append(duplicate, up, down, remove);
      header.append(label, actions);
      header.addEventListener("click", (e) => {
        if (e.target.closest("button")) return;
        toggleCollapse("entries", entryKey, div);
      });
      div.appendChild(header);
      const fields = document.createElement("div");
      fields.className = "fields";
      def.fields.forEach((field) => {
        const fieldDiv = document.createElement("div");
        fieldDiv.className = "field" + (field.area ? " wide" : "");
        const lb = document.createElement("label");
        lb.textContent = t(field.labelKey);
        fieldDiv.appendChild(lb);
        if (field.type === "select") {
          const select = document.createElement("select");
          const empty = document.createElement("option");
          empty.value = "";
          empty.textContent = "—";
          select.appendChild(empty);
          (field.options || []).forEach((value) => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = field.optionKind ? optionLabel(field.optionKind, value) : value;
            select.appendChild(option);
          });
          select.value = entry[field.k] || "";
          select.addEventListener("change", () => {
            recordHistory(true);
            entry[field.k] = select.value;
            markDirty(true);
          });
          fieldDiv.appendChild(select);
        } else if (field.type === "logo") {
          const row = document.createElement("div");
          row.className = "logo-row";
          const status = document.createElement("span");
          status.className = "logo-status";
          const paintLogo = () => {
            const name = entry[field.k] ? entry[field.k].split(/[\\/]/).pop() : "";
            status.textContent = name ? "✓ " + name : t("no_logo");
            status.style.color = name ? "var(--ok)" : "";
          };
          const button = document.createElement("button");
          button.className = "small";
          button.textContent = t("choose_logo");
          button.onclick = async () => {
            const r = await api.choose_photo("logo");
            if (!r.ok) {
              if (r.error) toast(r.error);
              return;
            }
            recordHistory(true);
            let path = r.path;
            try {
              const dataUrl = await normalizeImage(r.url, 512, "image/png");
              const saved = await api.save_image(dataUrl, "logo");
              if (saved.ok && saved.path) path = saved.path;
              else toast((saved.errores && saved.errores[0]) || t("toast_logo_normalize_error"));
            } catch (e) {
              toast(t("toast_logo_normalize_error"));
            }
            entry[field.k] = path;
            paintLogo();
            markDirty(true);
          };
          const remove = document.createElement("button");
          remove.className = "remove-button";
          remove.textContent = "✕";
          remove.title = t("remove_logo");
          remove.onclick = () => {
            recordHistory(true);
            entry[field.k] = "";
            paintLogo();
            markDirty(true);
          };
          paintLogo();
          row.append(button, remove, status);
          fieldDiv.appendChild(row);
        } else {
          const input = document.createElement(field.area ? "textarea" : "input");
          input.value = entry[field.k] || "";
          input.addEventListener("input", () => {
            recordHistory(true);
            entry[field.k] = input.value;
            markDirty(true);
          });
          fieldDiv.appendChild(input);
        }
        fields.appendChild(fieldDiv);
      });
      div.appendChild(fields);
      wrap.appendChild(div);
    });
    const button = document.createElement("button");
    button.className = "add-entry-button";
    button.textContent = t("add");
    button.onclick = () => {
      const empty = {};
      def.fields.forEach((field) => (empty[field.k] = ""));
      recordHistory(true);
      state.data[key].push(empty);
      paint();
      markDirty(true);
    };
    wrap.appendChild(button);
  };
  paint();
  return wrap;
}

/* ---------------- social networks card ---------------- */

function socialNetworkLabel(value) {
  const network = SOCIAL_NETWORKS.find((n) => n.value === value);
  if (!network) return String(value || "");
  return network.labelKey ? t(network.labelKey) : network.label;
}

function socialsList() {
  if (!state.data) return [];
  if (!Array.isArray(state.data.socials)) state.data.socials = [];
  return state.data.socials;
}

/* "Social networks" card: a dynamic list that is not a standard section, so
   it has no inline rename/visibility controls. Every row is a network select,
   an optional custom name (only visible for "other") and the URL/handle. */
function renderSocials() {
  const wrap = document.createElement("div");
  wrap.id = "socials-list";

  const paint = () => {
    wrap.innerHTML = "";
    socialsList().forEach((social) => {
      const row = document.createElement("div");
      row.className = "entry social-row";
      const header = document.createElement("div");
      header.className = "entry-header";
      const name = document.createElement("span");
      name.className = "entry-label";
      const remove = document.createElement("button");
      remove.className = "remove-button";
      remove.textContent = "✕";
      remove.title = t("social_remove");
      header.append(name, remove);

      const fields = document.createElement("div");
      fields.className = "fields";

      const networkField = document.createElement("div");
      networkField.className = "field";
      const networkLabel = document.createElement("label");
      networkLabel.textContent = t("social_network");
      const select = document.createElement("select");
      select.className = "social-network";
      select.title = t("social_network");
      SOCIAL_NETWORKS.forEach((network) => {
        const option = document.createElement("option");
        option.value = network.value;
        option.textContent = socialNetworkLabel(network.value);
        select.appendChild(option);
      });
      if (!SOCIAL_NETWORKS.some((n) => n.value === social.network)) social.network = "github";
      select.value = social.network;
      networkField.append(networkLabel, select);

      const customField = document.createElement("div");
      customField.className = "field social-label-field";
      const customLabel = document.createElement("label");
      customLabel.textContent = t("social_label");
      const customInput = document.createElement("input");
      customInput.type = "text";
      customInput.className = "social-label";
      customInput.value = social.label || "";
      customInput.placeholder = t("social_label");
      customField.append(customLabel, customInput);
      customField.hidden = social.network !== "other";

      const valueField = document.createElement("div");
      valueField.className = "field wide";
      const valueLabel = document.createElement("label");
      valueLabel.textContent = t("social_value");
      const valueInput = document.createElement("input");
      valueInput.type = "text";
      valueInput.className = "social-value";
      valueInput.value = social.value || "";
      valueInput.placeholder = t("social_value");
      valueField.append(valueLabel, valueInput);

      name.textContent = socialNetworkLabel(social.network);

      select.addEventListener("change", () => {
        recordHistory(false);
        social.network = select.value;
        customField.hidden = social.network !== "other";
        name.textContent = socialNetworkLabel(social.network);
        markDirty(true);
      });
      customInput.addEventListener("input", () => {
        recordHistory(false);
        social.label = customInput.value;
        markDirty(true);
      });
      valueInput.addEventListener("input", () => {
        recordHistory(false);
        social.value = valueInput.value;
        markDirty(true);
      });
      remove.addEventListener("click", () => {
        recordHistory(true);
        const list = socialsList();
        const i = list.indexOf(social);
        if (i >= 0) list.splice(i, 1);
        markDirty(true);
        paint();
      });

      fields.append(networkField, customField, valueField);
      row.append(header, fields);
      wrap.appendChild(row);
    });
  };

  paint();

  const add = document.createElement("button");
  add.id = "social-add";
  add.className = "add-entry-button";
  add.textContent = t("social_add");
  add.addEventListener("click", () => {
    recordHistory(true);
    socialsList().push({ network: "github", label: "", value: "" });
    markDirty(true);
    paint();
  });

  const cont = document.createElement("div");
  cont.className = "socials";
  cont.append(wrap, add);
  return cont;
}

function personalLogoField(key, label) {
  const fieldDiv = document.createElement("div");
  fieldDiv.className = "field";
  const lb = document.createElement("label");
  lb.textContent = label;
  const row = document.createElement("div");
  row.className = "logo-row";
  const status = document.createElement("span");
  status.className = "logo-status";
  const paint = () => {
    const name = state.data[key] ? state.data[key].split(/[\\/]/).pop() : "";
    status.textContent = name ? "✓ " + name : t("no_logo");
    status.style.color = name ? "var(--ok)" : "";
  };
  const button = document.createElement("button");
  button.className = "small";
  button.textContent = t("choose_logo");
  button.onclick = async () => {
    const r = await api.choose_photo("logo");
    if (!r.ok) {
      if (r.error) toast(r.error);
      return;
    }
    recordHistory(false);
    let path = r.path;
    try {
      const dataUrl = await normalizeImage(r.url, 512, "image/png");
      const saved = await api.save_image(dataUrl, "logo");
      if (saved.ok && saved.path) path = saved.path;
      else toast((saved.errores && saved.errores[0]) || t("toast_logo_normalize_error"));
    } catch (e) {
      toast(t("toast_logo_normalize_error"));
    }
    state.data[key] = path;
    paint();
    markDirty(true);
  };
  const remove = document.createElement("button");
  remove.className = "remove-button";
  remove.textContent = "✕";
  remove.title = t("remove_logo");
  remove.onclick = () => {
    recordHistory(false);
    state.data[key] = "";
    paint();
    markDirty(true);
  };
  paint();
  row.append(button, remove, status);

  const size = document.createElement("div");
  size.className = "photo-size";
  const widthLabel = document.createElement("label");
  widthLabel.textContent = t("width_cm");
  const widthInput = document.createElement("input");
  widthInput.type = "number";
  widthInput.min = "0.5";
  widthInput.max = "6";
  widthInput.step = "0.1";
  const heightLabel = document.createElement("label");
  heightLabel.textContent = t("height_cm");
  const heightInput = document.createElement("input");
  heightInput.type = "number";
  heightInput.min = "0.3";
  heightInput.max = "4";
  heightInput.step = "0.1";
  const fillSize = () => {
    widthInput.value = Number(state.data.school_logo_width_cm) || 2.4;
    heightInput.value = Number(state.data.school_logo_height_cm) || 0.85;
  };
  widthInput.addEventListener("change", () => {
    recordHistory(false);
    state.data.school_logo_width_cm = Number(widthInput.value) || 2.4;
    markDirty(true);
  });
  heightInput.addEventListener("change", () => {
    recordHistory(false);
    state.data.school_logo_height_cm = Number(heightInput.value) || 0.85;
    markDirty(true);
  });
  size.append(widthLabel, widthInput, heightLabel, heightInput);
  fillSize();

  fieldDiv.append(lb, row, size);
  return fieldDiv;
}

function cvLanguageField() {
  const fieldDiv = document.createElement("div");
  fieldDiv.className = "field";
  const lb = document.createElement("label");
  lb.textContent = t("cv_language_label");
  const select = document.createElement("select");
  CV_LANGUAGES.forEach((language) => {
    const option = document.createElement("option");
    option.value = language.value;
    option.textContent = t(language.labelKey);
    select.appendChild(option);
  });
  select.value = state.data.cv_language || "zh";
  select.addEventListener("change", () => {
    recordHistory(true);
    state.data.cv_language = select.value;
    markDirty(true);
  });
  fieldDiv.append(lb, select);
  return fieldDiv;
}

function renderForm() {
  let cont = $("#form-panel");
  if (!cont) {
    // Recovery: if #form-panel disappeared from the DOM, recreate it empty.
    const host = $("#form-area") || document.body;
    host.innerHTML = "";
    cont = document.createElement("div");
    cont.id = "form-panel";
    host.appendChild(cont);
  }
  cont.innerHTML = "";

  const personal = sectionCard(t("section_personal"));
  const fields = document.createElement("div");
  fields.className = "fields";
  fields.append(
    cvLanguageField(),
    basicField("name", t("field_name")),
    basicField("profession", t("field_profession")),
    basicField("email", t("field_email")),
    basicField("phone", t("field_phone")),
    basicField("address", t("field_address")),
    basicField("school_name", t("field_school_name")),
    personalLogoField("school_logo", t("field_school_logo"))
  );
  fields.appendChild(photoRow());
  personal.content.appendChild(fields);
  cont.appendChild(personal);
  paintPhoto(); // now #photo-preview is in the DOM

  const socials = sectionCard(t("socials_title"));
  socials.content.appendChild(renderSocials());
  cont.appendChild(socials);

  const extra = sectionCard(t("section_extra"));
  extra.title = t("extra_fields_tip");
  extra.content.appendChild(renderDynamicList("extra_fields"));
  cont.appendChild(extra);

  // Standard sections in the order chosen by the user; each header allows
  // renaming, hiding and reordering. "Personal details", "Social networks" and
  // "Extra details" stay fixed at the top and the "Blocks" card at the end.
  sectionOrder().forEach((key) => {
    const card = sectionCard(sectionName(key), key, true);
    if (isSectionHidden(key)) {
      card.classList.add("section-hidden");
      card.content.hidden = true;
    }
    if (key === "summary") {
      card.content.appendChild(basicField("summary", t("field_summary"), true));
    } else {
      card.content.appendChild(renderDynamicList(key));
    }
    cont.appendChild(card);
  });

  const blocksCard = sectionCard(t("section_blocks"));
  blocksCard.title = t("blocks_tip");
  const blockList = document.createElement("div");
  blockList.id = "blocks-inline";
  blocksCard.content.appendChild(blockList);
  cont.appendChild(blocksCard);
  paintBlocksList(blockList);
}

/* ---------------- free blocks (Add menu) ---------------- */

let _editingBlock = null;

function currentBlocks() {
  if (!state.data) return [];
  if (!Array.isArray(state.data.blocks)) state.data.blocks = [];
  return state.data.blocks;
}

function newBlockId() {
  try {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID().replace(/-/g, "");
    }
  } catch (e) {
    /* crypto.randomUUID unavailable: the hexadecimal fallback is used */
  }
  let id = "";
  const hex = "0123456789abcdef";
  for (let i = 0; i < 32; i++) id += hex[Math.floor(Math.random() * 16)];
  return id;
}

function normalizeBlockPosition(pos) {
  const value = String(pos || "").trim();
  return blockAnchorsUI().indexOf(value) >= 0 ? value : "end";
}

function blockPositionLabel(pos) {
  const value = normalizeBlockPosition(pos);
  if (value === "start") return t("position_start");
  if (value === "end") return t("position_end");
  return t("position_after") + sectionName(value);
}

function trimText(s, max) {
  const text = String(s);
  return text.length > max ? text.slice(0, max - 1).replace(/\s+$/, "") + "…" : text;
}

function blockLabel(block) {
  if (!block || typeof block !== "object") return t("block_label");
  if (block.type === "section") {
    const title = String(block.title || "").trim();
    if (title) return t("block_section_prefix") + title;
    const line = String(block.content || "").split(/\r?\n/).find((l) => l.trim());
    return t("block_section_prefix") + (line ? trimText(line.trim(), 48) : t("block_no_content"));
  }
  if (block.type === "separator") {
    const styles = {
      line: t("separator_line"),
      band: t("separator_band"),
      space: t("separator_space"),
    };
    return t("block_separator_prefix") + (styles[block.style] || styles.line);
  }
  if (block.type === "list") {
    const base = listName(block.mode, block.columns);
    const title = String(block.title || "").trim();
    return title ? base + ": " + trimText(title, 40) : base;
  }
  return t("block_label");
}

/* SINGLE mutation point for state.data.blocks: creations, edits, movements and
   deletions of blocks all go through here. markDirty() leaves the CV dirty and
   schedules autosave and recompilation. Undo/redo hooks into this single point:
   state.data.blocks is never mutated anywhere else. `structural` repaints the
   visible lists (form card and modal) unless false is passed. */
function mutateBlocks(fn, structural) {
  if (!state.data) return null;
  // Undo/redo hook: snapshot before mutating. Block actions are structural and
  // are not grouped with text changes.
  recordHistory(structural !== false);
  const blocks = currentBlocks();
  const result = fn(blocks);
  markDirty(true);
  if (structural !== false) refreshBlockLists();
  return result;
}

function createSeparatorBlock(style) {
  if (["line", "band", "space"].indexOf(style) < 0) style = "line";
  mutateBlocks((blocks) => {
    blocks.push({ id: newBlockId(), type: "separator", style, position: "end" });
  });
}

function moveBlock(block, step) {
  mutateBlocks((blocks) => {
    if (blocks.indexOf(block) < 0) return;
    const anchors = blockAnchorsUI();
    const j = anchors.indexOf(normalizeBlockPosition(block.position)) + step;
    if (j < 0 || j >= anchors.length) return;
    block.position = anchors[j];
  });
}

function deleteBlock(block) {
  mutateBlocks((blocks) => {
    const i = blocks.indexOf(block);
    if (i >= 0) blocks.splice(i, 1);
  });
}

function refreshBlockLists() {
  const inline = $("#blocks-inline");
  if (inline) paintBlocksList(inline);
  const modal = $("#blocks-list");
  if (modal) paintBlocksList(modal);
}

function paintBlocksList(cont) {
  if (!cont) return;
  cont.innerHTML = "";
  const blocks = currentBlocks();
  if (!blocks.length) {
    const p = document.createElement("p");
    p.className = "no-entries";
    p.textContent = t("no_blocks");
    cont.appendChild(p);
    return;
  }
  blocks.forEach((block) => cont.appendChild(blockRow(block)));
}

function blockRow(block) {
  const div = document.createElement("div");
  div.className = "entry";
  const blockKey = block && block.id ? String(block.id) : "";
  applyCollapse("blocks", blockKey, div);
  const header = document.createElement("div");
  header.className = "entry-header";
  const label = document.createElement("span");
  label.className = "entry-label";
  const name = document.createElement("span");
  name.textContent = blockLabel(block);
  const position = document.createElement("span");
  position.className = "block-position";
  position.textContent = blockPositionLabel(block && block.position);
  position.title = t("block_position_tip");
  label.append(name, position);

  const actions = document.createElement("span");
  actions.className = "block-actions";
  actions.style.display = "flex";
  actions.style.alignItems = "center";
  actions.style.gap = "6px";
  const anchors = blockAnchorsUI();
  const anchorIndex = anchors.indexOf(normalizeBlockPosition(block && block.position));

  const up = document.createElement("button");
  up.className = "small";
  up.textContent = "↑";
  up.title = t("move_block_up");
  up.disabled = anchorIndex <= 0;
  up.addEventListener("click", (e) => {
    e.stopPropagation();
    moveBlock(block, -1);
  });

  const down = document.createElement("button");
  down.className = "small";
  down.textContent = "↓";
  down.title = t("move_block_down");
  down.disabled = anchorIndex >= anchors.length - 1;
  down.addEventListener("click", (e) => {
    e.stopPropagation();
    moveBlock(block, 1);
  });

  actions.append(up, down);

  if (block && (block.type === "section" || block.type === "list")) {
    const edit = document.createElement("button");
    edit.className = "small";
    edit.textContent = t("edit");
    edit.title = block.type === "list" ? t("edit_list_block_tip") : t("edit_section_block_tip");
    edit.addEventListener("click", (e) => {
      e.stopPropagation();
      if (block.type === "list") openListBlockModal(block.mode, block);
      else openCustomSectionModal(block);
    });
    actions.appendChild(edit);
  }

  const remove = document.createElement("button");
  remove.className = "remove-button";
  remove.textContent = "✕";
  remove.title = t("delete_block");
  remove.addEventListener("click", (e) => {
    e.stopPropagation();
    deleteBlock(block);
  });
  actions.appendChild(remove);

  header.append(label, actions);
  header.addEventListener("click", (e) => {
    if (e.target.closest("button")) return;
    toggleCollapse("blocks", blockKey, div);
  });
  div.appendChild(header);
  return div;
}

function openCustomSectionModal(block) {
  _editingBlock = block || null;
  $("#custom-section-title").value = _editingBlock ? String(_editingBlock.title || "") : "";
  $("#custom-section-content").value = _editingBlock ? String(_editingBlock.content || "") : "";
  $("#modal-custom-section").hidden = false;
  $("#custom-section-title").focus();
}

function acceptCustomSection() {
  const title = $("#custom-section-title").value.trim();
  const content = $("#custom-section-content").value.trim();
  if (!title && !content) {
    toast(t("toast_section_empty"));
    return;
  }
  const editing = _editingBlock;
  _editingBlock = null;
  mutateBlocks((blocks) => {
    if (editing && blocks.indexOf(editing) >= 0) {
      editing.title = title;
      editing.content = content;
    } else {
      blocks.push({ id: newBlockId(), type: "section", title, content, position: "end" });
    }
  });
  closeModal($("#modal-custom-section"));
}

/* Generic list templates ("list" block type): title+detail pairs in 1-3
   columns or period+description. The backend sanitizes them and renders them
   the same way in LaTeX and Word. */

const LIST_MODES = {
  columns: {
    nameKey: "list_block_columns_title",
    helpKey: "list_columns_help",
  },
  period: {
    nameKey: "list_block_period_title",
    helpKey: "list_period_help",
  },
};

let _listMode = "columns";
let _listEditing = null;

function listName(mode, columns) {
  if (mode === "period") return t("list_block_period_title");
  const n = Math.min(Math.max(Number(columns) || 1, 1), 3);
  return n === 1 ? t("list_name_1") : t("list_name_n").replace("{n}", n);
}

function listField(field, label, area) {
  const div = document.createElement("div");
  div.className = "field" + (area ? " wide" : "");
  const lb = document.createElement("label");
  lb.textContent = label;
  const input = document.createElement(area ? "textarea" : "input");
  if (!area) input.type = "text";
  if (area) input.rows = 3;
  input.dataset.field = field;
  div.append(lb, input);
  return div;
}

function renumberList() {
  $$("#list-block-entries .entry-number").forEach((el, i) => {
    el.textContent = t("entry_number").replace("{n}", i + 1);
  });
}

function listRow(entry) {
  const data = entry || {};
  const div = document.createElement("div");
  div.className = "entry";
  const header = document.createElement("div");
  header.className = "entry-header";
  const number = document.createElement("span");
  number.className = "entry-label entry-number";
  const remove = document.createElement("button");
  remove.className = "remove-button";
  remove.textContent = "✕";
  remove.title = t("entry_delete");
  remove.addEventListener("click", () => {
    div.remove();
    renumberList();
  });
  header.append(number, remove);
  const fields = document.createElement("div");
  fields.className = "fields";
  const text = (v) => (v == null ? "" : String(v));
  if (_listMode === "period") {
    const period = listField("period", t("period_dates"));
    period.querySelector("input").value = text(data.period);
    const description = listField("description", t("description"), true);
    description.querySelector("textarea").value = text(data.description);
    fields.append(period, description);
  } else {
    const title = listField("title", t("title_field"));
    title.querySelector("input").value = text(data.title);
    const detail = listField("detail", t("detail_optional"), true);
    detail.querySelector("textarea").value = text(data.detail);
    fields.append(title, detail);
  }
  div.append(header, fields);
  return div;
}

function addListEntry(entry) {
  const cont = $("#list-block-entries");
  if (!cont) return;
  const row = listRow(entry);
  cont.appendChild(row);
  renumberList();
  cont.scrollTop = cont.scrollHeight;
  const first = row.querySelector("input, textarea");
  if (first) first.focus();
}

function readListEntries() {
  const entries = [];
  $$("#list-block-entries .entry").forEach((row) => {
    const entry = {};
    let empty = true;
    $$("[data-field]", row).forEach((input) => {
      const value = String(input.value || "").trim();
      entry[input.dataset.field] = value;
      if (value) empty = false;
    });
    if (!empty) entries.push(entry);
  });
  return entries;
}

function openListBlockModal(mode, block, columns) {
  _listMode = mode === "period" ? "period" : "columns";
  _listEditing = block || null;
  const editing = _listEditing;
  $("#list-block-heading").textContent = t(LIST_MODES[_listMode].nameKey);
  $("#list-block-title").value = editing ? String(editing.title || "") : "";
  const col = editing ? Number(editing.columns) || 1 : Number(columns) || 1;
  $("#list-block-columns").value = String(Math.min(Math.max(col, 1), 3));
  $("#list-block-columns-field").hidden = _listMode !== "columns";
  $("#list-block-help").textContent = t(LIST_MODES[_listMode].helpKey);
  const cont = $("#list-block-entries");
  cont.innerHTML = "";
  const previous = editing && Array.isArray(editing.entries) ? editing.entries : [];
  if (previous.length) previous.forEach((entry) => cont.appendChild(listRow(entry)));
  else cont.appendChild(listRow({}));
  renumberList();
  $("#modal-list-block").hidden = false;
  $("#list-block-title").focus();
}

function acceptListBlock() {
  const title = $("#list-block-title").value.trim();
  const mode = _listMode;
  const columns = mode === "columns" ? Number($("#list-block-columns").value) || 1 : 1;
  const entries = readListEntries();
  if (!title && !entries.length) {
    toast(t("toast_list_empty"));
    return;
  }
  const editing = _listEditing;
  _listEditing = null;
  mutateBlocks((blocks) => {
    if (editing && blocks.indexOf(editing) >= 0) {
      editing.mode = mode;
      editing.title = title;
      editing.columns = columns;
      editing.entries = entries;
    } else {
      blocks.push({
        id: newBlockId(), type: "list", mode, title, columns, entries,
        position: "end",
      });
    }
  });
  closeModal($("#modal-list-block"));
}

function openBlocksModal() {
  paintBlocksList($("#blocks-list"));
  $("#modal-blocks").hidden = false;
}

function setupBlocks() {
  $("#custom-section-cancel").addEventListener("click", () => {
    _editingBlock = null;
    closeModal($("#modal-custom-section"));
  });
  $("#custom-section-accept").addEventListener("click", acceptCustomSection);
  $("#list-block-cancel").addEventListener("click", () => {
    _listEditing = null;
    closeModal($("#modal-list-block"));
  });
  $("#list-block-accept").addEventListener("click", acceptListBlock);
  $("#list-block-add").addEventListener("click", () => addListEntry({}));
  $("#blocks-close").addEventListener("click", () => closeModal($("#modal-blocks")));
}

/* ---------------- LaTeX mode ---------------- */

function enterLatexMode() {
  state.mode = "latex";
  const host = $("#form-area") || document.body;
  const panelForm = $("#form-panel");
  if (panelForm) panelForm.hidden = true;
  const existing = $("#latex-panel");
  if (existing) existing.remove();

  const cont = document.createElement("div");
  cont.id = "latex-panel";

  const bar = document.createElement("div");
  bar.id = "latex-bar";
  const label = document.createElement("span");
  label.textContent = t("latex_bar");
  const back = document.createElement("button");
  back.className = "small";
  back.id = "back-to-form";
  back.textContent = t("back_to_form");
  back.onclick = () => toggleOption("latex");
  bar.append(label, back);

  const area = document.createElement("textarea");
  area.id = "latex-text";
  area.spellcheck = false;
  area.value = state.texManual !== null ? state.texManual : (state.tex || "");
  state.texEdited = false;
  area.addEventListener("input", () => {
    state.texManual = area.value;
    state.texEdited = true;
    scheduleCompile();
  });

  cont.append(bar, area);
  host.appendChild(cont);
  updateMarks();
}

function exitLatexMode(recompile) {
  state.mode = "form";
  state.texManual = null;
  state.texEdited = false;
  const pl = $("#latex-panel");
  if (pl) pl.remove();
  const panelForm = $("#form-panel");
  if (panelForm) panelForm.hidden = false;
  renderForm();
  updateMarks();
  if (recompile) scheduleCompile();
}

/* ---------------- LaTeX engine wizard ---------------- */

function openWizard() {
  $("#wz-progress").hidden = true;
  $("#wz-status").textContent = "";
  $("#wz-bar").style.width = "0%";
  $("#install-cancel").hidden = true;
  $("#install-cancel").disabled = false;
  $("#wz-install").disabled = false;
  $("#modal-wizard").hidden = false;
}

function closeWizard(ok) {
  $("#modal-wizard").hidden = true;
  state.latexOk = ok;
  $("#engine-warning").hidden = ok;
  if (ok) compileNow();
}

function setupWizard() {
  $("#wz-install").addEventListener("click", async () => {
    const button = $("#wz-install");
    button.disabled = true;
    $("#install-cancel").hidden = false;
    $("#install-cancel").disabled = false;
    $("#wz-progress").hidden = false;
    $("#wz-status").textContent = "";
    $("#wz-bar").style.width = "0%";
    try {
      await api.install_latex();
    } catch (e) {
      button.disabled = false;
      $("#install-cancel").hidden = true;
      $("#wz-status").textContent = t("wizard_install_start_error");
      console.error(e);
    }
  });

  $("#install-cancel").addEventListener("click", async () => {
    $("#install-cancel").disabled = true;
    try {
      await api.cancel_install();
    } catch (e) {
      console.error(e);
    }
  });

  $("#wz-have").addEventListener("click", async () => {
    const r = await api.check_latex();
    if (r.ok) closeWizard(true);
    else $("#wz-status").textContent = t("wizard_not_found");
  });

  $("#wz-manual").addEventListener("click", async () => {
    const r = await api.choose_latex_path();
    if (r.ok) closeWizard(true);
    else if (r.error) $("#wz-status").textContent = r.error;
  });

  $("#wz-later").addEventListener("click", async (e) => {
    e.preventDefault();
    await api.dismiss_setup();
    closeWizard(false);
    $("#engine-warning").hidden = false;
  });
}

window.__onInstallProgress = function (p) {
  if (p.warning) {
    // Non-fatal backend warning (e.g. checksum unavailable): keep the bar
    // where it is and show the localized message.
    $("#wz-progress-text").textContent = p.warning;
    return;
  }
  if (p.total) {
    const percent = Math.min(100, Math.round((100 * p.hecho) / p.total));
    $("#wz-bar").style.width = percent + "%";
    $("#wz-progress-text").textContent = t("install_progress")
      .replace("{pct}", percent)
      .replace("{done}", formatBytes(p.hecho))
      .replace("{total}", formatBytes(p.total));
  } else {
    $("#wz-bar").style.width = "100%";
    $("#wz-progress-text").textContent = t("install_working");
  }
};

window.__onInstallDone = function (r) {
  $("#wz-install").disabled = false;
  $("#install-cancel").hidden = true;
  $("#install-cancel").disabled = false;
  $("#wz-bar").style.width = "100%";
  if (r.ok) {
    $("#wz-progress").hidden = true;
    toast(r.warning ? r.msg + " " + r.warning : r.msg);
    closeWizard(true);
  } else {
    $("#wz-progress").hidden = true;
    $("#wz-status").textContent = r.msg;
  }
};

/* ---------------- settings ---------------- */

// Returns "" if the value is empty, "#RRGGBB" in uppercase if it is a valid
// color (#RGB or #RRGGBB) and null if it is not valid hexadecimal.
function parseHex(value) {
  const text = String(value == null ? "" : value).trim();
  if (!text) return "";
  if (/^#[0-9a-fA-F]{3}$/.test(text)) {
    const c = text.slice(1).toUpperCase();
    return "#" + c[0] + c[0] + c[1] + c[1] + c[2] + c[2];
  }
  if (/^#[0-9a-fA-F]{6}$/.test(text)) return text.toUpperCase();
  return null;
}

function readColorPrefs() {
  const colors = {};
  COLOR_FIELDS.forEach((field) => {
    const value = parseHex($("#pf-color-" + field).value);
    colors[field] = value === null ? "" : value;
  });
  return colors;
}

// If the empty field has a valid placeholder, the wheel shows it; otherwise it
// keeps its last value.
function syncColorWheel(field) {
  const text = $("#pf-color-" + field);
  const wheel = $("#pf-color-" + field + "-wheel");
  const value = parseHex(text.value) || parseHex(text.placeholder);
  if (value) wheel.value = value;
}

async function loadTemplateColors() {
  let colors = {};
  try {
    const r = await api.template_colors(state.data.template);
    if (r && r.ok && r.colores) colors = r.colores;
  } catch (e) {
    console.error(e);
  }
  const perField = {
    primary: colors.accent,
    secondary: colors.acento2,
    text: "#000000",
    gray: colors.gris,
  };
  COLOR_FIELDS.forEach((field) => {
    const placeholder = parseHex(perField[field]);
    $("#pf-color-" + field).placeholder = placeholder === null ? "" : placeholder;
  });
}

function saveColorPrefs() {
  state.prefs.colors = readColorPrefs();
  api.set_prefs("colors", state.prefs.colors);
  markDirty(true);
}

function setupColorPrefs() {
  COLOR_FIELDS.forEach((field) => {
    const text = $("#pf-color-" + field);
    const wheel = $("#pf-color-" + field + "-wheel");
    const reset = $("#pf-color-" + field + "-reset");
    text.addEventListener("change", () => {
      const value = parseHex(text.value);
      if (value === null) {
        const previous = parseHex((state.prefs.colors || {})[field]);
        text.value = previous === null ? "" : previous;
        return;
      }
      text.value = value;
      syncColorWheel(field);
      saveColorPrefs();
    });
    wheel.addEventListener("input", () => {
      text.value = parseHex(wheel.value) || "";
      saveColorPrefs();
    });
    reset.addEventListener("click", () => {
      text.value = "";
      const placeholder = parseHex(text.placeholder);
      if (placeholder) wheel.value = placeholder;
      saveColorPrefs();
    });
  });
}

async function openPrefs() {
  $("#pf-message").textContent = "";
  $("#pf-paper").value = state.prefs.paper;
  $("#pf-font-size").value = String(state.prefs.font_size);
  $("#pf-auto-compile").checked = !!state.prefs.auto_compile;
  $("#pf-breakpoint").value = state.prefs.breakpoint;
  $("#pf-margin-top").value = state.prefs.margins.top;
  $("#pf-margin-bottom").value = state.prefs.margins.bottom;
  $("#pf-margin-left").value = state.prefs.margins.left;
  $("#pf-margin-right").value = state.prefs.margins.right;
  $("#ui-language").value = getLang();
  const colors = state.prefs.colors || {};
  COLOR_FIELDS.forEach((field) => {
    const value = parseHex(colors[field]);
    $("#pf-color-" + field).value = value === null ? "" : value;
  });
  $("#modal-settings").hidden = false;
  checkEnginePrefs();
  await loadTemplateColors();
  COLOR_FIELDS.forEach(syncColorWheel);
}

async function checkEnginePrefs() {
  const r = await api.check_latex();
  $("#pf-engine-status").textContent = r.ok
    ? t("engine_ready").replace("{path}", r.path)
    : t("engine_missing");
  $("#engine-warning").hidden = r.ok;
  state.latexOk = r.ok;
}

function onLanguageChange(event) {
  setLang(event.target.value);
  applyI18n(document);
  document.title = t("app_title");
  if (api) api.set_prefs("ui_language", event.target.value);
  renderForm();
  updateMarks();
  refreshBlockLists();
  renderPreviewStatus();
  renderStatus();
  scheduleCompile();
}

function setupPrefs() {
  $("#pf-paper").addEventListener("change", (e) => {
    state.prefs.paper = e.target.value;
    api.set_prefs("paper", e.target.value);
    markDirty(true);
  });
  $("#pf-font-size").addEventListener("change", (e) => {
    state.prefs.font_size = Number(e.target.value);
    api.set_prefs("font_size", Number(e.target.value));
    markDirty(true);
  });
  $("#pf-auto-compile").addEventListener("change", (e) => {
    state.prefs.auto_compile = e.target.checked;
    api.set_prefs("auto_compile", e.target.checked);
    updateMarks();
    if (e.target.checked) scheduleCompile();
  });
  $("#pf-breakpoint").addEventListener("change", (e) => {
    state.prefs.breakpoint = Number(e.target.value);
    api.set_prefs("breakpoint", Number(e.target.value));
    applyResponsive();
  });
  ["top", "bottom", "left", "right"].forEach((side) => {
    $("#pf-margin-" + side).addEventListener("change", () => {
      const margins = {
        top: Number($("#pf-margin-top").value) || 0,
        bottom: Number($("#pf-margin-bottom").value) || 0,
        left: Number($("#pf-margin-left").value) || 0,
        right: Number($("#pf-margin-right").value) || 0,
      };
      state.prefs.margins = margins;
      api.set_prefs("margins", margins);
      markDirty(true);
    });
  });
  $("#pf-engine-check").addEventListener("click", checkEnginePrefs);
  $("#pf-engine-path").addEventListener("click", async () => {
    const r = await api.choose_latex_path();
    if (r.ok) {
      $("#pf-message").textContent = t("path_saved");
      await checkEnginePrefs();
      scheduleCompile();
    }
  });
  $("#pf-engine-install").addEventListener("click", () => {
    $("#modal-settings").hidden = true;
    openWizard();
    $("#wz-install").click();
  });
  $("#pf-close").addEventListener("click", () => {
    $("#modal-settings").hidden = true;
    $("#pf-message").textContent = "";
  });
  $("#ui-language").addEventListener("change", onLanguageChange);
  setupColorPrefs();
}

/* ---------------- custom margins ---------------- */

function openMarginsModal() {
  $("#mg-top").value = state.prefs.margins.top;
  $("#mg-bottom").value = state.prefs.margins.bottom;
  $("#mg-left").value = state.prefs.margins.left;
  $("#mg-right").value = state.prefs.margins.right;
  $("#modal-margins").hidden = false;
}

function setupMargins() {
  $("#mg-apply").addEventListener("click", () => {
    const margins = {
      top: Number($("#mg-top").value) || 0,
      bottom: Number($("#mg-bottom").value) || 0,
      left: Number($("#mg-left").value) || 0,
      right: Number($("#mg-right").value) || 0,
    };
    state.prefs.margins = margins;
    api.set_prefs("margins", margins);
    $("#modal-margins").hidden = true;
    markDirty(true);
  });
  $("#mg-cancel").addEventListener("click", () => {
    $("#modal-margins").hidden = true;
  });
}

/* ---------------- confirm dialog and modals ---------------- */

function setupConfirm() {
  $("#confirm-accept").addEventListener("click", () => {
    const accept = _confirmAccept;
    closeModal($("#modal-confirm"));
    if (accept) accept();
  });
  $("#confirm-cancel").addEventListener("click", () => {
    const cancel = _confirmCancel;
    closeModal($("#modal-confirm"));
    if (cancel) cancel();
  });
}

function setupModals() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      $$(".modal").forEach((modal) => {
        if (!modal.hidden) closeModal(modal);
      });
    }
  });
  $$(".modal").forEach((modal) => {
    modal.addEventListener("click", (e) => {
      if (e.target.classList.contains("modal")) closeModal(e.target);
    });
  });
}

/* ---------------- keyboard shortcuts ---------------- */

function anyModalOpen() {
  return $$(".modal").some((modal) => !modal.hidden);
}

function setupShortcuts() {
  document.addEventListener("keydown", (e) => {
    // While typing (including IME composition) normal text is not intercepted:
    // only Ctrl combinations act.
    if (!(e.ctrlKey || e.metaKey) || e.altKey || e.isComposing) return;
    // With a modal open the global shortcuts do not act (Escape closes them).
    if (anyModalOpen()) return;
    const key = String(e.key || "").toLowerCase();
    if (key === "z" && !e.shiftKey) {
      // The LaTeX editor keeps the native textarea undo.
      if (state.mode === "latex") return;
      e.preventDefault();
      undo();
      return;
    }
    if (key === "y" || (key === "z" && e.shiftKey)) {
      if (state.mode === "latex") return;
      e.preventDefault();
      redo();
      return;
    }
    if (key === "s") {
      if (e.repeat) return; // do not repeat the dialog while held down
      e.preventDefault();
      saveCurrentCv();
      return;
    }
    if (key === "o") {
      if (e.repeat) return;
      e.preventDefault();
      openCv();
      return;
    }
    if (key === "n") {
      if (e.repeat) return;
      e.preventDefault();
      newCv();
      return;
    }
    if (key === "enter") {
      // Ctrl+Enter recompiles; plain Enter keeps typing in the fields.
      e.preventDefault();
      clearTimeout(state.timer);
      compileNow();
      return;
    }
  });
}

/* ---------------- center splitter ---------------- */

// Minimum width of the form and the preview while dragging the splitter. The
// chosen position is stored in prefs ("split", in %); it is UI only and never
// affects the .tex nor the PDF. Double-click resets to 50 %.
const SPLITTER_MIN_FORM = 300;
const SPLITTER_MIN_PREVIEW = 320;

function applySplit(pct) {
  const container = $("#content");
  if (!container) return;
  const value = Number(pct);
  if (!(value > 0) || document.body.classList.contains("stacked")) {
    container.style.removeProperty("--form-width");
    return;
  }
  container.style.setProperty("--form-width", value + "%");
}

function setupSplitter() {
  const splitter = $("#splitter");
  const container = $("#content");
  const form = $("#form-area");
  if (!splitter || !container || !form) return;
  let dragging = false;
  let startX = 0;
  let startWidth = 0;

  const clamp = (px) => {
    const total = container.getBoundingClientRect().width || 1;
    const min = Math.min(SPLITTER_MIN_FORM, total * 0.35);
    const max = Math.max(min, total - SPLITTER_MIN_PREVIEW);
    return Math.min(Math.max(px, min), max);
  };

  splitter.addEventListener("pointerdown", (e) => {
    if (document.body.classList.contains("stacked")) return;
    dragging = true;
    startX = e.clientX;
    startWidth = form.getBoundingClientRect().width;
    document.body.classList.add("resizing");
    e.preventDefault();
  });

  document.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const width = clamp(startWidth + (e.clientX - startX));
    container.style.setProperty("--form-width", width + "px");
  });

  const release = () => {
    if (!dragging) return;
    dragging = false;
    document.body.classList.remove("resizing");
    const total = container.getBoundingClientRect().width;
    if (total > 0) {
      const pct = Math.round((form.getBoundingClientRect().width / total) * 1000) / 10;
      state.prefs.split = pct;
      api.set_prefs("split", pct);
    }
  };
  document.addEventListener("pointerup", release);
  document.addEventListener("pointercancel", release);

  splitter.addEventListener("dblclick", () => {
    if (state.prefs) state.prefs.split = 50;
    api.set_prefs("split", 50);
    applySplit(50);
  });
}

/* ---------------- responsive ---------------- */

function applyResponsive() {
  const breakpoint = Number(state.prefs && state.prefs.breakpoint) || 960;
  document.body.classList.toggle("stacked", window.innerWidth < breakpoint);
  applySplit(state.prefs && state.prefs.split);
}

/* ---------------- startup ---------------- */

async function startApp() {
  try {
    api = await waitForApi();
    if (!api) {
      setStatus("status_pywebview_missing", "error");
      return;
    }
    const info = await api.init();
    state.prefs = info.prefs;
    try {
      const stored = await api.get_prefs();
      if (stored && typeof stored === "object") state.prefs = stored;
    } catch (e) {
      console.error(e);
    }
    setLang((state.prefs && state.prefs.ui_language) || "en");
    applyI18n(document);
    document.title = t("app_title");
    applyTheme(state.prefs.theme);
    emptyData = await api.empty_data();
    state.data = JSON.parse(JSON.stringify(emptyData));
    state.latexOk = info.latex_ok;

    let pendingAutosave = null;
    try {
      const a = await api.autosave_read();
      if (a && typeof a === "object" && !Array.isArray(a)) pendingAutosave = a;
    } catch (e) {
      console.error(e);
    }

    renderForm();
    updateMarks();
    updateHistoryButtons();
    applyResponsive();
    window.addEventListener("resize", applyResponsive);
    $("#engine-warning").hidden = info.latex_ok;
    renderPreviewStatus();
    setupPreviewFallback(info.platform);

    setupWizard();
    setupPrefs();
    setupMargins();
    setupConfirm();
    setupModals();
    setupCrop();
    setupBlocks();
    setupSplitter();
    setupShortcuts();
    setInterval(autosaveNow, 30000);

    if (pendingAutosave && dataHasContent(pendingAutosave)) offerRecovery(pendingAutosave);
    else if (pendingAutosave) clearAutosave();
    if (info.needs_setup) openWizard();
    else compileNow();
  } catch (e) {
    setStatus("status_start_error", "error", (e && e.message ? e.message : e));
    console.error(e);
  }
}

startApp();
