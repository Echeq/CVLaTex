"use strict";

let api = null;

function apiLista() {
  return new Promise((resolve) => {
    let hecho = false;
    const comprobar = () => {
      if (
        !hecho &&
        window.pywebview &&
        window.pywebview.api &&
        typeof window.pywebview.api.elegir_foto === "function"
      ) {
        hecho = true;
        clearInterval(intervalo);
        resolve(window.pywebview.api);
      }
    };
    const intervalo = setInterval(comprobar, 30);
    window.addEventListener("pywebviewready", comprobar);
    setTimeout(() => {
      if (!hecho) {
        hecho = true;
        clearInterval(intervalo);
        resolve((window.pywebview && window.pywebview.api) || null);
      }
    }, 5000);
  });
}
const $ = (sel, base) => (base || document).querySelector(sel);
const $$ = (sel, base) => Array.from((base || document).querySelectorAll(sel));

const state = {
  datos: null,
  prefs: null,
  latexOk: false,
  modo: "formulario",
  tex: null,
  texManual: null,
  texEditado: false,
  sucio: false,
  idCompilacion: 0,
  timer: null,
  zoom: 100,
  pilaDeshacer: [],
  pilaRehacer: [],
};

let datosVacios = null;

const TIPOS_EDUCACION = [
  "Primaria",
  "Secundaria (ESO)",
  "Bachillerato",
  "FP Grado Medio",
  "FP Grado Superior",
  "Grado Universitario",
  "Ingeniería",
  "Licenciatura",
  "Diplomatura",
  "Arquitectura",
  "Máster",
  "Doctorado (PhD)",
  "Posgrado / Especialización",
  "Curso / Certificación",
  "Otro",
];

const IDIOMAS_CV = [
  { v: "zh", l: "中文 (chino)" },
  { v: "es", l: "Español" },
  { v: "en", l: "English" },
];

const PLANTILLAS_CV = [
  { v: "clasico", l: "Clásico" },
  { v: "harvard", l: "Harvard (académica)" },
  { v: "moderno", l: "Moderno" },
  { v: "creativo", l: "Creativo" },
  { v: "chino", l: "Chino (estándar)" },
];

const TEMAS = ["claro", "oscuro", "sistema"];

const SECCIONES_DINAMICAS = {
  trabajo: {
    titulo: "Trabajo",
    columnas: true,
    campos: [
      { k: "modalidad", l: "Modalidad", tipo: "select", opciones: ["Presencial", "Híbrido", "Remoto"] },
      { k: "puesto", l: "Puesto / Cargo" },
      { k: "empresa", l: "Empresa / Compañía" },
      { k: "desde", l: "Desde (año)" },
      { k: "hasta", l: "Hasta (año)" },
      { k: "logros", l: "Logros (uno por línea)", area: true },
      { k: "logo", l: "Logo de la empresa", tipo: "logo" },
    ],
  },
  pasantia: {
    titulo: "Pasantías",
    columnas: true,
    campos: [
      { k: "modalidad", l: "Modalidad", tipo: "select", opciones: ["Presencial", "Híbrido", "Remoto"] },
      { k: "puesto", l: "Puesto / Cargo" },
      { k: "empresa", l: "Empresa / Compañía" },
      { k: "desde", l: "Desde (año)" },
      { k: "hasta", l: "Hasta (año)" },
      { k: "logros", l: "Logros (uno por línea)", area: true },
      { k: "logo", l: "Logo de la empresa", tipo: "logo" },
    ],
  },
  proyectos: {
    titulo: "Proyectos",
    columnas: true,
    campos: [
      { k: "nombre", l: "Nombre del proyecto" },
      { k: "organizacion", l: "Organización / Evento" },
      { k: "desde", l: "Desde (año)" },
      { k: "hasta", l: "Hasta (año)" },
      { k: "descripcion", l: "Descripción (uno por línea)", area: true },
      { k: "resultado", l: "Resultado (ej: 成果：获三等奖)" },
      { k: "enlace", l: "Enlace (Github)" },
    ],
  },
  proyectosu: {
    titulo: "Proyectos universitarios",
    columnas: true,
    campos: [
      { k: "nombre", l: "Nombre del proyecto" },
      { k: "asignatura", l: "Asignatura / Curso" },
      { k: "organizacion", l: "Universidad / Empresa" },
      { k: "desde", l: "Desde (año)" },
      { k: "hasta", l: "Hasta (año)" },
      { k: "descripcion", l: "Descripción (uno por línea)", area: true },
      { k: "resultado", l: "Resultado (ej: 成果：获三等奖)" },
      { k: "enlace", l: "Enlace (Github)" },
      { k: "logo", l: "Logo de la universidad", tipo: "logo" },
    ],
  },
  educacion: {
    titulo: "Educación",
    columnas: true,
    campos: [
      { k: "tipo", l: "Tipo de educación", tipo: "select", opciones: TIPOS_EDUCACION },
      { k: "titulo", l: "Título / Grado" },
      { k: "institucion", l: "Institución" },
      { k: "desde", l: "Desde (año)" },
      { k: "hasta", l: "Hasta (año)" },
      { k: "nota", l: "Nota / Mención" },
      { k: "logo", l: "Logo de la institución", tipo: "logo" },
    ],
  },
  habilidades: {
    titulo: "Habilidades (por categorías)",
    campos: [
      { k: "categoria", l: "Categoría (ej: 编程语言 / Lenguajes)" },
      { k: "valores", l: "Valores (separados por comas)" },
    ],
  },
  idiomas: {
    titulo: "Idiomas",
    campos: [
      { k: "idioma", l: "Idioma" },
      { k: "nivel", l: "Nivel" },
    ],
  },
  referencias: {
    titulo: "Referencias",
    campos: [
      { k: "nombre", l: "Nombre" },
      { k: "contacto", l: "Contacto" },
    ],
  },
  datos_extra: {
    titulo: "Datos adicionales",
    campos: [
      { k: "etiqueta", l: "Etiqueta (ej: Ciudad)" },
      { k: "valor", l: "Valor" },
    ],
  },
};

// Anclas de los bloques libres, en el mismo orden en que se insertan en el
// documento (sincronizado con ANCLAS_BLOQUE de latex_gen.py).
const ANCLAS_UI = [
  "inicio", "perfil", "educacion", "proyectos", "proyectosu", "pasantia",
  "trabajo", "habilidades", "idiomas", "referencias", "final",
];

// Nombre visible de cada ancla para el indicador de posición.
const NOMBRES_ANCLA = {
  inicio: "Inicio",
  perfil: "Perfil",
  educacion: "Educación",
  proyectos: "Proyectos",
  proyectosu: "Proyectos universitarios",
  pasantia: "Pasantías",
  trabajo: "Trabajo",
  habilidades: "Habilidades",
  idiomas: "Idiomas",
  referencias: "Referencias",
  final: "Final",
};

/* ---------------- utilidades ---------------- */

function escaparHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function estado(msj, clase) {
  const el = $("#estado");
  el.textContent = msj;
  el.dataset.estado = clase || "";
}

function toast(msj) {
  const t = $("#toast");
  t.textContent = msj;
  t.hidden = false;
  clearTimeout(state._toastTimer);
  state._toastTimer = setTimeout(() => (t.hidden = true), 3500);
}

let _confirmarAceptar = null;
let _confirmarCancelar = null;

function restaurarEtiquetasConfirmar() {
  $("#confirmar-si").textContent = "Aceptar";
  $("#confirmar-no").textContent = "Cancelar";
}

function cerrarModal(modal) {
  if (!modal) return;
  modal.hidden = true;
  if (modal.id === "modal-confirmar") {
    _confirmarAceptar = null;
    _confirmarCancelar = null;
    restaurarEtiquetasConfirmar();
  }
}

function confirmar(msj, alAceptar, alCancelar, etiquetaAceptar, etiquetaCancelar) {
  $("#confirmar-msj").textContent = msj;
  _confirmarAceptar = alAceptar || null;
  _confirmarCancelar = alCancelar || null;
  $("#confirmar-si").textContent = etiquetaAceptar || "Aceptar";
  $("#confirmar-no").textContent = etiquetaCancelar || "Cancelar";
  $("#confirmar-no").hidden = false;
  $("#modal-confirmar").hidden = false;
}

function alerta(msj) {
  $("#confirmar-msj").textContent = msj;
  _confirmarAceptar = null;
  _confirmarCancelar = null;
  restaurarEtiquetasConfirmar();
  $("#confirmar-no").hidden = true;
  $("#modal-confirmar").hidden = false;
}

function fmBytes(b) {
  return (b / 1048576).toFixed(1) + " MB";
}

/* ---------------- menús ---------------- */

function cerrarMenus() {
  $$(".menu.abierto").forEach((m) => m.classList.remove("abierto"));
}

function actualizarMarcas() {
  const mm = (sel) => ($("#menus").querySelector(sel));
  const ma = mm('[data-marca="autocompilar"]');
  const ml = mm('[data-marca="latex"]');
  if (ma) ma.textContent = state.prefs && state.prefs.autocompilar ? "✓" : "";
  if (ml) ml.textContent = state.modo === "latex" ? "✓" : "";
  const temaActivo = document.documentElement.getAttribute("data-tema") || "sistema";
  TEMAS.forEach((t) => {
    const m = mm('[data-marca="tema-' + t + '"]');
    if (m) m.textContent = t === temaActivo ? "✓" : "";
  });
  const plantillaActiva = state.datos && state.datos.plantilla ? state.datos.plantilla : "clasico";
  PLANTILLAS_CV.forEach((p) => {
    const m = mm('[data-marca="plantilla-' + p.v + '"]');
    if (m) m.textContent = p.v === plantillaActiva ? "✓" : "";
  });
  const btn = $("#btn-auto");
  if (btn) btn.classList.toggle("activo", !!(state.prefs && state.prefs.autocompilar));
}

$$(".menu-btn").forEach((btn) => {
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const menu = btn.closest(".menu");
    const abierto = menu.classList.contains("abierto");
    cerrarMenus();
    if (!abierto) menu.classList.add("abierto");
  });
});
document.addEventListener("click", cerrarMenus);

/* ---------------- tema (claro / oscuro / sistema) ---------------- */

function aplicarTema(t) {
  const tema = TEMAS.indexOf(t) >= 0 ? t : "sistema";
  document.documentElement.dataset.tema = tema;
}

function cambiarTema(t) {
  state.prefs.tema = t;
  api.set_prefs("tema", t);
  aplicarTema(t);
  actualizarMarcas();
}

/* ---------------- acciones ---------------- */

document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-accion]");
  if (el) ejecutarAccion(el.dataset.accion, e);
});

function ejecutarAccion(accion, e) {
  if (accion.startsWith("papel:")) aplicarPapel(accion.split(":")[1]);
  else if (accion.startsWith("margenes:")) aplicarMargenes(accion.split(":")[1]);
  else if (accion.startsWith("fuente:")) aplicarFuente(Number(accion.split(":")[1]));
  else if (accion.startsWith("tema:")) cambiarTema(accion.split(":")[1]);
  else if (accion.startsWith("plantilla:")) aplicarPlantilla(accion.split(":")[1]);
  else if (accion.startsWith("zoom:")) aplicarZoom(Number(accion.split(":")[1]));
  else if (accion.startsWith("toggle:")) alternarToggle(accion.split(":")[1]);
  else {
    switch (accion) {
      case "deshacer": deshacer(); break;
      case "rehacer": rehacer(); break;
      case "nuevo": accionNuevo(); break;
      case "abrir": accionAbrir(); break;
      case "importar": accionAbrir(); break;
      case "guardar": accionGuardar(); break;
      case "exportar-pdf": accionExportarPDF(); break;
      case "exportar-tex": accionExportarTex(); break;
      case "exportar-docx": accionExportarDocx(); break;
      case "importar-tex": accionImportarTex(); break;
      case "cargar-ejemplo": accionCargarEjemplo(); break;
      case "preferencias": case "preferencias-motor": abrirPrefs(); break;
      case "recompilar": clearTimeout(state.timer); compilar(); break;
      case "bloque:linea": crearBloqueSeparador("linea"); break;
      case "bloque:banda": crearBloqueSeparador("banda"); break;
      case "bloque:espacio": crearBloqueSeparador("espacio"); break;
      case "bloque:seccion": abrirModalBloqueSeccion(null); break;
      case "bloques:gestion": abrirModalBloques(); break;
      case "ayuda": $("#modal-ayuda").hidden = false; break;
      case "creditos": $("#modal-creditos").hidden = false; break;
      case "cerrar-modal": {
        const modal = e && e.target && e.target.closest ? e.target.closest(".modal") : null;
        if (modal) cerrarModal(modal);
        break;
      }
    }
  }
}

function hayContenido() {
  if (!datosVacios || !state.datos) return false;
  return Object.keys(datosVacios).some(
    (k) => k !== "plantilla" && JSON.stringify(state.datos[k]) !== JSON.stringify(datosVacios[k])
  );
}

async function accionNuevo() {
  confirmar("¿Descartar el CV actual y comenzar uno nuevo?", () => {
    if (state.modo === "latex") salirModoLatex(false);
    state.datos = JSON.parse(JSON.stringify(datosVacios));
    limpiarHistorial();
    renderFormulario();
    actualizarMarcas();
    programarCompilacion();
    state.sucio = false;
    borrarAutosave();
    toast("CV nuevo creado");
  });
}

async function accionAbrir() {
  const r = await api.abrir_cv();
  if (r.ok && r.datos) {
    const aplicar = () => {
      if (state.modo === "latex") salirModoLatex(false);
      state.datos = r.datos;
      limpiarHistorial();
      renderFormulario();
      actualizarMarcas();
      programarCompilacion();
      state.sucio = false;
      borrarAutosave();
      toast("Abierto: " + r.ruta);
    };
    if (hayContenido()) {
      confirmar("Se reemplazará el contenido actual por el del archivo que abras. ¿Continuar?", aplicar);
    } else {
      aplicar();
    }
  } else if (r.errores) {
    toast(r.errores[0]);
  }
}

async function accionGuardar() {
  const r = await api.exportar_cv(state.datos);
  if (r.ok) {
    state.sucio = false;
    await borrarAutosave();
    toast("Guardado: " + r.ruta);
  } else if (r.errores) {
    toast(r.errores[0]);
  }
}

async function accionExportarPDF() {
  const texManual = state.modo === "latex" ? state.texManual : null;
  const r = await api.exportar_pdf(state.datos, texManual);
  if (r.ok) toast("PDF exportado: " + r.ruta);
  else if (r.errores) toast(r.errores[0]);
}

async function accionExportarTex() {
  const texManual = state.modo === "latex" ? state.texManual : null;
  const r = await api.exportar_tex(state.datos, texManual);
  if (r.ok) toast("LaTeX exportado: " + r.ruta);
  else if (r.errores) toast(r.errores[0]);
}

async function accionExportarDocx() {
  const r = await api.exportar_docx(state.datos);
  if (r.ok) toast("Word exportado: " + r.ruta);
  else if (r.errores) toast(r.errores[0]);
}

async function accionImportarTex() {
  const r = await api.importar_tex();
  if (r.ok && r.datos) {
    const aplicar = () => {
      if (state.modo === "latex") salirModoLatex(false);
      state.datos = r.datos;
      limpiarHistorial();
      renderFormulario();
      actualizarMarcas();
      programarCompilacion();
      state.sucio = false;
      borrarAutosave();
      toast("LaTeX importado: " + r.ruta);
    };
    if (hayContenido()) {
      confirmar("Se reemplazará el contenido actual por el LaTeX importado. ¿Continuar?", aplicar);
    } else {
      aplicar();
    }
  } else if (r.errores) {
    alerta(r.errores[0]);
  }
}

async function accionCargarEjemplo() {
  const aplicar = async () => {
    const r = await api.cargar_ejemplo(state.datos.plantilla);
    if (!r.ok) {
      toast((r.errores && r.errores[0]) || "No se pudo cargar el ejemplo");
      return;
    }
    if (state.modo === "latex") salirModoLatex(false);
    state.datos = r.datos;
    limpiarHistorial();
    renderFormulario();
    actualizarMarcas();
    programarCompilacion();
    state.sucio = false;
    borrarAutosave();
    toast("Ejemplo cargado: sustituye estos datos por los tuyos");
  };
  if (hayContenido()) {
    confirmar("Se reemplazará el contenido actual por el CV de ejemplo. ¿Continuar?", aplicar);
  } else {
    aplicar();
  }
}

function aplicarPapel(papel) {
  state.prefs.papel = papel;
  api.set_prefs("papel", papel);
  programarCompilacion();
}

function aplicarMargenes(m) {
  if (m === "personalizado") {
    abrirModalMargenes();
    return;
  }
  const valores = m === "normal" ? { top: 2, bottom: 2, left: 2, right: 2 } : { top: 1, bottom: 1, left: 1, right: 1 };
  state.prefs.margenes = valores;
  api.set_prefs("margenes", valores);
  programarCompilacion();
}

function aplicarFuente(f) {
  state.prefs.fuente = f;
  api.set_prefs("fuente", f);
  programarCompilacion();
}

function aplicarPlantilla(v) {
  const esValida = PLANTILLAS_CV.some((o) => o.v === v);
  registrarHistorial(true);
  state.datos.plantilla = esValida ? v : "clasico";
  marcarSucio();
  actualizarMarcas();
}

function alternarToggle(t) {
  if (t === "autocompilar") {
    state.prefs.autocompilar = !state.prefs.autocompilar;
    api.set_prefs("autocompilar", state.prefs.autocompilar);
    actualizarMarcas();
    if (state.prefs.autocompilar) programarCompilacion();
  } else if (t === "latex") {
    if (state.modo === "latex") {
      const editado = state.texEditado;
      confirmar(
        editado
          ? "El código LaTeX se editó a mano. Al volver al formulario se regenerará desde los datos y se perderán los cambios manuales. ¿Continuar?"
          : "¿Volver al formulario?",
        () => salirModoLatex(true)
      );
    } else {
      entrarModoLatex();
    }
  }
}

/* ---------------- compilación ---------------- */

function programarCompilacion() {
  if (!state.prefs || !state.prefs.autocompilar) return;
  clearTimeout(state.timer);
  state.timer = setTimeout(compilar, 400);
}

async function compilar() {
  if (!api || state.modo === "latex" && state.texManual == null && !state.tex) return;
  const id = ++state.idCompilacion;
  const ep = $("#estado-preview");
  ep.className = "compilando";
  ep.textContent = "Compilando…";
  if (state.modo === "latex") {
    await api.compilar_tex(state.texManual !== null ? state.texManual : state.tex, id, state.datos);
  } else {
    await api.compile(state.datos, id);
  }
}

/* ---------------- zoom de la previsualización ---------------- */

// El fragmento #zoom=<pct>&view=FitH lo interpreta el visor de PDF. Si el
// visor integrado de WebView2 lo ignora, el respaldo es el PDF a tamaño de
// página: el zoom es solo un ajuste visual y nunca afecta al .tex ni al PDF.
function aplicarZoom(pct) {
  const valores = [75, 100, 125];
  const valor = valores.indexOf(Number(pct)) >= 0 ? Number(pct) : (state.zoom || 100);
  state.zoom = valor;
  valores.forEach((v) => {
    const b = $("#zoom-" + v);
    if (b) b.classList.toggle("activo", v === valor);
  });
  const pdf = $("#pdf");
  if (pdf) pdf.src = "/preview/main.pdf?v=" + Date.now() + "#zoom=" + valor + "&view=FitH";
}

window.__onCompile = function (res) {
  if (res.id !== state.idCompilacion) return;
  const ep = $("#estado-preview");
  if (res.ok) {
    $("#errores").hidden = true;
    $("#aviso-motor").hidden = true;
    aplicarZoom(state.zoom);
    ep.className = "ok";
    ep.textContent = "Previsualización lista";
    estado("");
  } else {
    ep.className = "error";
    ep.textContent = res.errores.length + " error(es)";
    const caja = $("#errores");
    caja.innerHTML = "<ul>" + res.errores.map((e) => "<li>" + escaparHtml(e) + "</li>").join("") + "</ul>";
    caja.hidden = false;
    estado("Falló la compilación", "error");
  }
  if (res.tex) state.tex = res.tex;
  if (state.modo === "latex" && state.texManual === null && res.tex) {
    const ta = $("#texto-latex");
    if (ta) ta.value = res.tex;
  }
};

/* ---------------- autosave ---------------- */

let _autosaveTimer = null;

function marcarSucio() {
  state.sucio = true;
  clearTimeout(_autosaveTimer);
  _autosaveTimer = setTimeout(autosaveYa, 5000);
  programarCompilacion();
}

async function autosaveYa() {
  if (!api || !state.sucio || !state.datos) return;
  try {
    await api.autosave(state.datos);
  } catch (e) {
    console.error(e);
  }
}

async function borrarAutosave() {
  if (!api) return;
  try {
    await api.autosave_borrar();
  } catch (e) {
    console.error(e);
  }
}

/* ---------------- deshacer / rehacer ---------------- */

const LIMITE_HISTORIAL = 50;
const COALESCENCIA_HISTORIAL = 600;

let _historialTs = 0;
let _historialEstructural = false;

function copiaProfunda(o) {
  return JSON.parse(JSON.stringify(o));
}

function limpiarHistorial() {
  state.pilaDeshacer = [];
  state.pilaRehacer = [];
  _historialTs = 0;
  _historialEstructural = false;
  actualizarBotonesHistorial();
}

/* Guarda un snapshot de state.datos antes de mutarlo. Los cambios no
   estructurales consecutivos (p. ej. teclear) se agrupan durante 600 ms: solo
   se conserva el snapshot del primer cambio del tirón. Las acciones
   estructurales (bloques, entradas, plantilla, columnas, idioma) siempre
   empujan una entrada nueva. */
function registrarHistorial(estructural) {
  if (!state.datos) return;
  const ahora = Date.now();
  const reciente = ahora - _historialTs < COALESCENCIA_HISTORIAL;
  _historialTs = ahora;
  if (!estructural && reciente && !_historialEstructural && state.pilaDeshacer.length) {
    state.pilaRehacer = [];
    actualizarBotonesHistorial();
    return;
  }
  state.pilaDeshacer.push(copiaProfunda(state.datos));
  if (state.pilaDeshacer.length > LIMITE_HISTORIAL) state.pilaDeshacer.shift();
  state.pilaRehacer = [];
  _historialEstructural = !!estructural;
  actualizarBotonesHistorial();
}

function actualizarBotonesHistorial() {
  const marcar = (accion, habilitado) => {
    const enlace = $("#menus [data-accion='" + accion + "']");
    if (enlace) {
      enlace.classList.toggle("deshabilitado", !habilitado);
      enlace.setAttribute("aria-disabled", habilitado ? "false" : "true");
    }
    const span = $("#menus [data-marca='" + accion + "']");
    if (span) span.classList.toggle("deshabilitado", !habilitado);
  };
  marcar("deshacer", !!(state.pilaDeshacer && state.pilaDeshacer.length));
  marcar("rehacer", !!(state.pilaRehacer && state.pilaRehacer.length));
}

function aplicarSnapshotHistorial() {
  _historialTs = 0;
  _historialEstructural = false;
  renderFormulario();
  actualizarMarcas();
  actualizarBotonesHistorial();
  marcarSucio(); // sucio + autosave + programarCompilacion, sin tocar el historial
}

function deshacer() {
  if (!state.datos || !state.pilaDeshacer.length) return;
  if (state.modo === "latex") return; // en modo LaTeX manda el deshacer del textarea
  state.pilaRehacer.push(copiaProfunda(state.datos));
  state.datos = state.pilaDeshacer.pop();
  aplicarSnapshotHistorial();
}

function rehacer() {
  if (!state.datos || !state.pilaRehacer.length) return;
  if (state.modo === "latex") return;
  state.pilaDeshacer.push(copiaProfunda(state.datos));
  state.datos = state.pilaRehacer.pop();
  aplicarSnapshotHistorial();
}

function ofrecerRecuperacion(datos) {
  confirmar(
    "Hay un CV sin guardar. ¿Recuperarlo?",
    () => {
      if (state.modo === "latex") salirModoLatex(false);
      const base = JSON.parse(JSON.stringify(datosVacios || {}));
      Object.keys(datos).forEach((k) => { base[k] = datos[k]; });
      state.datos = base;
      limpiarHistorial();
      renderFormulario();
      actualizarMarcas();
      marcarSucio();
      toast("CV sin guardar recuperado");
    },
    () => {
      borrarAutosave();
      toast("CV sin guardar descartado");
    },
    "Recuperar",
    "Descartar"
  );
}

/* ---------------- formulario ---------------- */

/* Plegado de tarjetas y entradas. Es estado solo de interfaz: vive en este
   mapa en memoria, se aplica en cada re-render y NUNCA se guarda en el
   .cvjson ni en el autosave (no forma parte de state.datos). */
const colapsoUI = { secciones: {}, entradas: {}, bloques: {} };

function estaColapsado(tipo, clave) {
  return !!colapsoUI[tipo][clave];
}

function aplicarColapso(tipo, clave, el) {
  if (el) el.classList.toggle("colapsada", estaColapsado(tipo, clave));
}

function alternarColapso(tipo, clave, el) {
  colapsoUI[tipo][clave] = !colapsoUI[tipo][clave];
  if (el) el.classList.toggle("colapsada", colapsoUI[tipo][clave]);
}

function seccionTitulo(texto, clave) {
  const t = document.createElement("div");
  t.className = "tarjeta-seccion";
  const cab = document.createElement("div");
  cab.className = "cab-seccion";
  const chev = document.createElement("span");
  chev.className = "chevron";
  chev.textContent = "▾";
  const h = document.createElement("h3");
  h.textContent = texto;
  cab.append(chev, h);
  if (clave && SECCIONES_DINAMICAS[clave].columnas) {
    if (!state.datos.columnas) state.datos.columnas = {};
    const rot = document.createElement("label");
    rot.className = "rot-col";
    rot.textContent = "Columnas:";
    const sel = document.createElement("select");
    sel.className = "sel-col";
    [1, 2, 3].forEach((n) => {
      const op = document.createElement("option");
      op.value = n;
      op.textContent = n;
      sel.appendChild(op);
    });
    sel.value = String(state.datos.columnas[clave] || 1);
    sel.title = "Muestra esta sección en 1, 2 o 3 columnas en el CV";
    sel.addEventListener("click", (e) => e.stopPropagation());
    sel.addEventListener("change", () => {
      registrarHistorial(true);
      state.datos.columnas[clave] = Number(sel.value);
      marcarSucio();
    });
    rot.appendChild(sel);
    cab.appendChild(rot);
  }
  const contenido = document.createElement("div");
  contenido.className = "sec-contenido";
  t.appendChild(cab);
  t.appendChild(contenido);
  t.contenido = contenido;
  const claveColapso = clave || texto;
  aplicarColapso("secciones", claveColapso, t);
  cab.addEventListener("click", (e) => {
    if (e.target.closest("select")) return;
    alternarColapso("secciones", claveColapso, t);
  });
  return t;
}

function campoBasico(k, label, area) {
  const div = document.createElement("div");
  div.className = "campo" + (area ? " ancho" : "");
  if (area) div.classList.add("ancho");
  const lb = document.createElement("label");
  lb.textContent = label;
  const inp = document.createElement(area ? "textarea" : "input");
  inp.value = state.datos[k] || "";
  inp.addEventListener("input", () => {
    registrarHistorial(false);
    state.datos[k] = inp.value;
    marcarSucio();
  });
  div.append(lb, inp);
  return div;
}

function pintarFoto() {
  const vista = $("#foto-vista");
  if (!vista) return;
  if (!state.datos.foto) {
    vista.textContent = "Sin foto";
    vista.style.width = "64px";
    vista.style.height = "80px";
    vista.style.padding = "0 4px";
    const b = $("#btn-ajustar-foto");
    if (b) b.hidden = true;
    return;
  }
  vista.innerHTML = "";
  vista.style.padding = "0";
  const a = Number(state.datos.foto_ancho_cm) || 4;
  const al = Number(state.datos.foto_alto_cm) || 5;
  vista.style.width = "64px";
  vista.style.height = Math.min(96, Math.max(50, Math.round((64 * al) / a))) + "px";
  const img = document.createElement("img");
  img.src = "/media/" + encodeURIComponent(state.datos.foto.split(/[\\/]/).pop());
  vista.appendChild(img);
  const b = $("#btn-ajustar-foto");
  if (b) b.hidden = false;
}

function fotoFila() {
  const fila = document.createElement("div");
  fila.className = "foto-fila";
  const vista = document.createElement("div");
  vista.className = "foto-vista";
  vista.id = "foto-vista";
  const controles = document.createElement("div");
  controles.className = "campo";
  const lb = document.createElement("label");
  lb.textContent = "Foto de perfil";
  const btns = document.createElement("div");
  const elegir = document.createElement("button");
  elegir.className = "pequeño";
  elegir.textContent = "Elegir foto…";
  const ajustar = document.createElement("button");
  ajustar.className = "pequeño";
  ajustar.id = "btn-ajustar-foto";
  ajustar.textContent = "Ajustar área…";
  ajustar.hidden = true;
  const quitar = document.createElement("button");
  quitar.className = "pequeño";
  quitar.textContent = "Quitar";
  btns.append(elegir, ajustar, quitar);
  btns.style.display = "flex";
  btns.style.gap = "8px";
  btns.style.flexWrap = "wrap";

  const tam = document.createElement("div");
  tam.className = "foto-tam";
  const lbA = document.createElement("label");
  lbA.textContent = "Ancho (cm)";
  const inpA = document.createElement("input");
  inpA.type = "number";
  inpA.min = "1";
  inpA.max = "12";
  inpA.step = "0.5";
  const lbAl = document.createElement("label");
  lbAl.textContent = "Alto (cm)";
  const inpAl = document.createElement("input");
  inpAl.type = "number";
  inpAl.min = "1";
  inpAl.max = "15";
  inpAl.step = "0.5";
  tam.append(lbA, inpA, lbAl, inpAl);

  controles.append(lb, btns, tam);
  fila.append(vista, controles);

  const actualizarTam = () => {
    inpA.value = Number(state.datos.foto_ancho_cm) || 4;
    inpAl.value = Number(state.datos.foto_alto_cm) || 5;
  };
  const aplicarTam = () => {
    registrarHistorial(false);
    state.datos.foto_ancho_cm = Number(inpA.value) || 4;
    state.datos.foto_alto_cm = Number(inpAl.value) || 5;
    marcarSucio();
  };
  inpA.addEventListener("change", () => { aplicarTam(); pintarFoto(); });
  inpAl.addEventListener("change", () => { aplicarTam(); pintarFoto(); });
  elegir.onclick = async () => {
    const r = await api.elegir_foto("foto");
    if (r.ok) {
      registrarHistorial(false);
      state.datos.foto = r.path;
      state.datos.foto_original = r.path;
      state.datos.foto_recorte = null;
      actualizarTam();
      pintarFoto();
      marcarSucio();
    } else if (r.error) toast(r.error);
  };
  ajustar.onclick = () => abrirRecorte();
  quitar.onclick = () => {
    registrarHistorial(false);
    state.datos.foto = "";
    state.datos.foto_original = "";
    state.datos.foto_recorte = null;
    pintarFoto();
    marcarSucio();
  };
  actualizarTam();
  return fila;
}

/* ---------------- recorte de foto ---------------- */

let _recorte = { img: null, cont: null, caja: null };

function abrirRecorte() {
  const origen = state.datos.foto_original || state.datos.foto;
  if (!origen) return;
  const img = new Image();
  img.onload = () => {
    _recorte.img = img;
    $("#modal-recorte").hidden = false;
    montarRecorte();
  };
  img.onerror = () => toast("No se pudo cargar la foto para ajustar el área");
  img.src = "/media/" + encodeURIComponent(origen.split(/[\\/]/).pop());
}

function ponerCaja(x, y, w, h) {
  const caja = _recorte.caja;
  if (!caja) return;
  caja.style.left = x + "px";
  caja.style.top = y + "px";
  caja.style.width = w + "px";
  caja.style.height = h + "px";
}

function montarRecorte() {
  const cont = $("#recorte-cont");
  cont.innerHTML = "";
  const img = _recorte.img;
  const maxW = 480;
  const maxH = 400;
  const escala = Math.min(maxW / img.naturalWidth, maxH / img.naturalHeight);
  const w = Math.round(img.naturalWidth * escala);
  const h = Math.round(img.naturalHeight * escala);
  cont.style.width = w + "px";
  cont.style.height = h + "px";
  const im = document.createElement("img");
  im.src = img.src;
  cont.appendChild(im);
  const caja = document.createElement("div");
  caja.className = "recorte-caja";
  ["nw", "ne", "sw", "se"].forEach((p) => {
    const hd = document.createElement("div");
    hd.className = "recorte-p recorte-" + p;
    hd.dataset.p = p;
    caja.appendChild(hd);
  });
  cont.appendChild(caja);
  _recorte.cont = cont;
  _recorte.caja = caja;

  const r = state.datos.foto_recorte || { x: 0, y: 0, w: 1, h: 1 };
  ponerCaja(r.x * w, r.y * h, Math.max(24, r.w * w), Math.max(24, r.h * h));
  engancharRecorte();
}

function engancharRecorte() {
  const cont = _recorte.cont;
  const caja = _recorte.caja;
  const cl = (v, m, M) => Math.min(M, Math.max(m, v));

  caja.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    const agarre = e.target.closest(".recorte-p");
    const anchoC = cont.clientWidth;
    const altoC = cont.clientHeight;
    const ax = e.clientX;
    const ay = e.clientY;
    const rect = {
      x: parseFloat(caja.style.left) || 0,
      y: parseFloat(caja.style.top) || 0,
      w: parseFloat(caja.style.width) || anchoC,
      h: parseFloat(caja.style.height) || altoC,
    };
    const onMove = (ev) => {
      const dx = ev.clientX - ax;
      const dy = ev.clientY - ay;
      if (!agarre) {
        ponerCaja(
          cl(rect.x + dx, 0, anchoC - rect.w),
          cl(rect.y + dy, 0, altoC - rect.h),
          rect.w,
          rect.h
        );
      } else {
        let nx = rect.x, ny = rect.y, nw = rect.w, nh = rect.h;
        if (agarre.dataset.p.includes("e")) nw = cl(rect.w + dx, 24, anchoC - rect.x);
        if (agarre.dataset.p.includes("s")) nh = cl(rect.h + dy, 24, altoC - rect.y);
        if (agarre.dataset.p.includes("w")) {
          nw = cl(rect.w - dx, 24, rect.x + rect.w);
          nx = rect.x + rect.w - nw;
        }
        if (agarre.dataset.p.includes("n")) {
          nh = cl(rect.h - dy, 24, rect.y + rect.h);
          ny = rect.y + rect.h - nh;
        }
        ponerCaja(nx, ny, nw, nh);
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

function configurarRecorte() {
  $("#recorte-cancelar").addEventListener("click", () => {
    $("#modal-recorte").hidden = true;
  });
  $("#recorte-aplicar").addEventListener("click", async () => {
    const cont = _recorte.cont;
    const img = _recorte.img;
    const caja = _recorte.caja;
    if (!cont || !img || !caja) return;
    const anchoC = cont.clientWidth;
    const altoC = cont.clientHeight;
    const x = parseFloat(caja.style.left) / anchoC;
    const y = parseFloat(caja.style.top) / altoC;
    const w = parseFloat(caja.style.width) / anchoC;
    const h = parseFloat(caja.style.height) / altoC;
    const red = (v) => Math.round(v * 1000) / 1000;
    registrarHistorial(false);
    state.datos.foto_recorte = { x: red(x), y: red(y), w: red(w), h: red(h) };
    const sx = x * img.naturalWidth;
    const sy = y * img.naturalHeight;
    const sw = w * img.naturalWidth;
    const sh = h * img.naturalHeight;
    const maxPix = 1600;
    const mayor = Math.max(sw, sh);
    const esc = mayor > maxPix ? maxPix / mayor : 1;
    const cv = document.createElement("canvas");
    cv.width = Math.round(sw * esc);
    cv.height = Math.round(sh * esc);
    cv.getContext("2d").drawImage(img, sx, sy, sw, sh, 0, 0, cv.width, cv.height);
    const dataUrl = cv.toDataURL("image/png");
    const r = await api.guardar_foto_recorte(dataUrl);
    if (r.ok) {
      state.datos.foto = r.path;
      $("#modal-recorte").hidden = true;
      pintarFoto();
      marcarSucio();
      toast("Área de la foto ajustada");
    } else {
      toast(r.error || "No se pudo guardar el recorte");
    }
  });
}

function listaDinamica(key) {
  const def = SECCIONES_DINAMICAS[key];
  const wrap = document.createElement("div");

  const pintar = () => {
    wrap.innerHTML = "";
    const lista = state.datos[key];
    if (!lista.length) {
      const p = document.createElement("p");
      p.className = "sin-entradas";
      p.textContent = "Sin entradas todavía.";
      wrap.appendChild(p);
    }
    lista.forEach((ent, idx) => {
      const div = document.createElement("div");
      div.className = "entrada";
      const claveEntrada = key + ":" + idx;
      aplicarColapso("entradas", claveEntrada, div);
      const cab = document.createElement("div");
      cab.className = "cab-entrada";
      const rot = document.createElement("span");
      rot.className = "cab-txt";
      const chev = document.createElement("span");
      chev.className = "chevron";
      chev.textContent = "▾";
      rot.append(chev, document.createTextNode(" " + def.titulo.replace(/s$/, "") + " " + (idx + 1)));
      const acciones = document.createElement("span");
      acciones.className = "entrada-acciones";

      const duplicar = document.createElement("button");
      duplicar.className = "pequeño";
      duplicar.textContent = "⧉";
      duplicar.title = "Duplicar entrada";
      duplicar.onclick = (e) => {
        e.stopPropagation();
        registrarHistorial(true);
        const copia = JSON.parse(JSON.stringify(ent));
        state.datos[key].splice(idx + 1, 0, copia);
        pintar();
        marcarSucio();
      };

      const subir = document.createElement("button");
      subir.className = "pequeño";
      subir.textContent = "↑";
      subir.title = "Subir entrada";
      subir.disabled = idx === 0;
      subir.onclick = (e) => {
        e.stopPropagation();
        const l = state.datos[key];
        if (idx <= 0) return;
        registrarHistorial(true);
        const tmp = l[idx - 1];
        l[idx - 1] = l[idx];
        l[idx] = tmp;
        pintar();
        marcarSucio();
      };

      const bajar = document.createElement("button");
      bajar.className = "pequeño";
      bajar.textContent = "↓";
      bajar.title = "Bajar entrada";
      bajar.disabled = idx >= lista.length - 1;
      bajar.onclick = (e) => {
        e.stopPropagation();
        const l = state.datos[key];
        if (idx >= l.length - 1) return;
        registrarHistorial(true);
        const tmp = l[idx + 1];
        l[idx + 1] = l[idx];
        l[idx] = tmp;
        pintar();
        marcarSucio();
      };

      const quitar = document.createElement("button");
      quitar.className = "btn-quitar";
      quitar.textContent = "✕";
      quitar.title = "Eliminar entrada";
      quitar.onclick = (e) => {
        e.stopPropagation();
        registrarHistorial(true);
        state.datos[key].splice(idx, 1);
        pintar();
        marcarSucio();
      };

      acciones.append(duplicar, subir, bajar, quitar);
      cab.append(rot, acciones);
      cab.addEventListener("click", (e) => {
        if (e.target.closest("button")) return;
        alternarColapso("entradas", claveEntrada, div);
      });
      div.appendChild(cab);
      const campos = document.createElement("div");
      campos.className = "campos";
      def.campos.forEach((c) => {
        const camp = document.createElement("div");
        camp.className = "campo" + (c.area ? " ancho" : "");
        const lb = document.createElement("label");
        lb.textContent = c.l;
        camp.appendChild(lb);
        if (c.tipo === "select") {
          const sel = document.createElement("select");
          const vacio = document.createElement("option");
          vacio.value = "";
          vacio.textContent = "—";
          sel.appendChild(vacio);
          (c.opciones || []).forEach((op) => {
            const o = document.createElement("option");
            o.value = op;
            o.textContent = op;
            sel.appendChild(o);
          });
          sel.value = ent[c.k] || "";
          sel.addEventListener("change", () => {
            registrarHistorial(true);
            ent[c.k] = sel.value;
            marcarSucio();
          });
          camp.appendChild(sel);
        } else if (c.tipo === "logo") {
          const fila = document.createElement("div");
          fila.className = "fila-logo";
          const estadoSpan = document.createElement("span");
          estadoSpan.className = "logo-estado";
          const pintarLogo = () => {
            const nombre = ent[c.k] ? ent[c.k].split(/[\\/]/).pop() : "";
            estadoSpan.textContent = nombre ? "✓ " + nombre : "Sin logo";
            estadoSpan.style.color = nombre ? "var(--ok)" : "";
          };
          const boton = document.createElement("button");
          boton.className = "pequeño";
          boton.textContent = "Elegir logo…";
          boton.onclick = async () => {
            const r = await api.elegir_foto("logo");
            if (r.ok) {
              registrarHistorial(true);
              ent[c.k] = r.path;
              pintarLogo();
              marcarSucio();
            } else if (r.error) toast(r.error);
          };
          const quitar = document.createElement("button");
          quitar.className = "btn-quitar";
          quitar.textContent = "✕";
          quitar.title = "Quitar logo";
          quitar.onclick = () => {
            registrarHistorial(true);
            ent[c.k] = "";
            pintarLogo();
            marcarSucio();
          };
          pintarLogo();
          fila.append(boton, quitar, estadoSpan);
          camp.appendChild(fila);
        } else {
          const inp = document.createElement(c.area ? "textarea" : "input");
          inp.value = ent[c.k] || "";
          inp.addEventListener("input", () => {
            registrarHistorial(true);
            ent[c.k] = inp.value;
            marcarSucio();
          });
          camp.appendChild(inp);
        }
        campos.appendChild(camp);
      });
      div.appendChild(campos);
      wrap.appendChild(div);
    });
    const boton = document.createElement("button");
    boton.className = "btn-anadir";
    boton.textContent = "+ Añadir";
    boton.onclick = () => {
      const vacio = {};
      def.campos.forEach((c) => (vacio[c.k] = ""));
      registrarHistorial(true);
      state.datos[key].push(vacio);
      pintar();
      marcarSucio();
    };
    wrap.appendChild(boton);
  };
  pintar();
  return wrap;
}

function campoLogoPersonal(k, label) {
  const camp = document.createElement("div");
  camp.className = "campo";
  const lb = document.createElement("label");
  lb.textContent = label;
  const fila = document.createElement("div");
  fila.className = "fila-logo";
  const estadoSpan = document.createElement("span");
  estadoSpan.className = "logo-estado";
  const pintar = () => {
    const nombre = state.datos[k] ? state.datos[k].split(/[\\/]/).pop() : "";
    estadoSpan.textContent = nombre ? "✓ " + nombre : "Sin logo";
    estadoSpan.style.color = nombre ? "var(--ok)" : "";
  };
  const boton = document.createElement("button");
  boton.className = "pequeño";
  boton.textContent = "Elegir logo…";
  boton.onclick = async () => {
    const r = await api.elegir_foto("logo");
    if (r.ok) {
      registrarHistorial(false);
      state.datos[k] = r.path;
      pintar();
      marcarSucio();
    } else if (r.error) toast(r.error);
  };
  const quitar = document.createElement("button");
  quitar.className = "btn-quitar";
  quitar.textContent = "✕";
  quitar.title = "Quitar logo";
  quitar.onclick = () => {
    registrarHistorial(false);
    state.datos[k] = "";
    pintar();
    marcarSucio();
  };
  pintar();
  fila.append(boton, quitar, estadoSpan);

  const tam = document.createElement("div");
  tam.className = "foto-tam";
  const lbA = document.createElement("label");
  lbA.textContent = "Ancho (cm)";
  const inpA = document.createElement("input");
  inpA.type = "number";
  inpA.min = "0.5";
  inpA.max = "6";
  inpA.step = "0.1";
  const lbAl = document.createElement("label");
  lbAl.textContent = "Alto (cm)";
  const inpAl = document.createElement("input");
  inpAl.type = "number";
  inpAl.min = "0.3";
  inpAl.max = "4";
  inpAl.step = "0.1";
  const llenarTam = () => {
    inpA.value = Number(state.datos.logo_egresado_ancho_cm) || 2.4;
    inpAl.value = Number(state.datos.logo_egresado_alto_cm) || 0.85;
  };
  inpA.addEventListener("change", () => {
    registrarHistorial(false);
    state.datos.logo_egresado_ancho_cm = Number(inpA.value) || 2.4;
    marcarSucio();
  });
  inpAl.addEventListener("change", () => {
    registrarHistorial(false);
    state.datos.logo_egresado_alto_cm = Number(inpAl.value) || 0.85;
    marcarSucio();
  });
  tam.append(lbA, inpA, lbAl, inpAl);
  llenarTam();

  camp.append(lb, fila, tam);
  return camp;
}

function campoSelectIdioma() {
  const camp = document.createElement("div");
  camp.className = "campo";
  const lb = document.createElement("label");
  lb.textContent = "Idioma de las etiquetas del CV";
  const sel = document.createElement("select");
  IDIOMAS_CV.forEach((o) => {
    const op = document.createElement("option");
    op.value = o.v;
    op.textContent = o.l;
    sel.appendChild(op);
  });
  sel.value = state.datos.idioma_cv || "zh";
  sel.addEventListener("change", () => {
    registrarHistorial(true);
    state.datos.idioma_cv = sel.value;
    marcarSucio();
  });
  camp.append(lb, sel);
  return camp;
}

function renderFormulario() {
  let cont = $("#form-panel");
  if (!cont) {
    // Recuperación: si #form-panel desapareció del DOM, se recrea vacío.
    const host = $("#panel-formulario") || document.body;
    host.innerHTML = "";
    cont = document.createElement("div");
    cont.id = "form-panel";
    host.appendChild(cont);
  }
  cont.innerHTML = "";

  const t1 = seccionTitulo("Datos personales");
  const c1 = document.createElement("div");
  c1.className = "campos";
  c1.append(
    campoSelectIdioma(),
    campoBasico("nombre", "Nombre completo"),
    campoBasico("profesion", "Puesto deseado (意向岗位)"),
    campoBasico("email", "Correo electrónico"),
    campoBasico("telefono", "Teléfono"),
    campoBasico("nacimiento", "Fecha de nacimiento"),
    campoBasico("nacionalidad", "Nacionalidad"),
    campoBasico("direccion", "Dirección"),
    campoBasico("web", "Web"),
    campoBasico("github", "Github"),
    campoBasico("linkedin", "Linkedin"),
    campoBasico("institucion_egresado", "Institución educativa (donde te graduaste)"),
    campoLogoPersonal("logo_egresado", "Logo de la institución")
  );
  c1.appendChild(fotoFila());
  t1.contenido.appendChild(c1);
  cont.appendChild(t1);
  pintarFoto(); // ahora #foto-vista ya está en el DOM

  const t2 = seccionTitulo("Perfil");
  t2.contenido.appendChild(campoBasico("perfil", "Resumen profesional", true));
  cont.appendChild(t2);

  const td = seccionTitulo("Datos adicionales");
  td.title = "Estos datos se muestran en el encabezado del CV junto a los datos personales";
  td.contenido.appendChild(listaDinamica("datos_extra"));
  cont.appendChild(td);

  Object.keys(SECCIONES_DINAMICAS).forEach((key) => {
    if (key === "datos_extra") return;
    const def = SECCIONES_DINAMICAS[key];
    const t = seccionTitulo(def.titulo, def.columnas ? key : null);
    t.contenido.appendChild(listaDinamica(key));
    cont.appendChild(t);
  });

  const tb = seccionTitulo("Bloques");
  tb.title = "Separadores y secciones personalizadas que se insertan en el CV";
  const listaB = document.createElement("div");
  listaB.id = "bloques-inline";
  tb.contenido.appendChild(listaB);
  cont.appendChild(tb);
  pintarListaBloques(listaB);
}

/* ---------------- bloques añadidos (menú Añadir) ---------------- */

let _bloqueEditando = null;

function bloquesActuales() {
  if (!state.datos) return [];
  if (!Array.isArray(state.datos.bloques)) state.datos.bloques = [];
  return state.datos.bloques;
}

function nuevoIdBloque() {
  try {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID().replace(/-/g, "");
    }
  } catch (e) {
    /* crypto.randomUUID no disponible: se usa el respaldo hexadecimal */
  }
  let id = "";
  const hex = "0123456789abcdef";
  for (let i = 0; i < 32; i++) id += hex[Math.floor(Math.random() * 16)];
  return id;
}

function normalizarPosicion(pos) {
  const p = String(pos || "").trim();
  return ANCLAS_UI.indexOf(p) >= 0 ? p : "final";
}

function etiquetaPosicion(pos) {
  const p = normalizarPosicion(pos);
  if (p === "inicio") return "Al inicio";
  if (p === "final") return "Al final";
  return "Después de " + (NOMBRES_ANCLA[p] || p);
}

function recortarTexto(s, max) {
  const t = String(s);
  return t.length > max ? t.slice(0, max - 1).replace(/\s+$/, "") + "…" : t;
}

function etiquetaBloque(b) {
  if (!b || typeof b !== "object") return "Bloque";
  if (b.tipo === "seccion") {
    const titulo = String(b.titulo || "").trim();
    if (titulo) return "Sección: " + titulo;
    const linea = String(b.contenido || "").split(/\r?\n/).find((l) => l.trim());
    return "Sección: " + (linea ? recortarTexto(linea.trim(), 48) : "sin contenido");
  }
  if (b.tipo === "separador") {
    const estilos = {
      linea: "Línea separadora",
      banda: "Banda de color",
      espacio: "Espacio en blanco",
    };
    return "Separador: " + (estilos[b.estilo] || estilos.linea);
  }
  return "Bloque";
}

/* Punto ÚNICO de mutación de state.datos.bloques: los altas, las ediciones,
   los movimientos y los borrados de bloques pasan todos por aquí.
   marcarSucio() deja el CV sucio y programa el autosave y la recompilación.
   t6 (deshacer/rehacer) debe engancharse en este único punto: no mutar
   state.datos.bloques desde ningún otro sitio. `estructural` repinta las
   listas visibles (tarjeta del formulario y modal) salvo que se pase false. */
function mutarBloques(fn, estructural) {
  if (!state.datos) return null;
  // Enganche de deshacer/rehacer: snapshot antes de mutar. Las acciones de
  // bloques son estructurales y no se agrupan con los cambios de texto.
  registrarHistorial(estructural !== false);
  const bloques = bloquesActuales();
  const resultado = fn(bloques);
  marcarSucio();
  if (estructural !== false) refrescarListasBloques();
  return resultado;
}

function crearBloqueSeparador(estilo) {
  if (["linea", "banda", "espacio"].indexOf(estilo) < 0) estilo = "linea";
  mutarBloques((bloques) => {
    bloques.push({ id: nuevoIdBloque(), tipo: "separador", estilo, posicion: "final" });
  });
}

function moverBloque(b, paso) {
  mutarBloques((bloques) => {
    if (bloques.indexOf(b) < 0) return;
    const j = ANCLAS_UI.indexOf(normalizarPosicion(b.posicion)) + paso;
    if (j < 0 || j >= ANCLAS_UI.length) return;
    b.posicion = ANCLAS_UI[j];
  });
}

function eliminarBloque(b) {
  mutarBloques((bloques) => {
    const i = bloques.indexOf(b);
    if (i >= 0) bloques.splice(i, 1);
  });
}

function refrescarListasBloques() {
  const inline = $("#bloques-inline");
  if (inline) pintarListaBloques(inline);
  const modal = $("#bloques-lista");
  if (modal) pintarListaBloques(modal);
}

function pintarListaBloques(cont) {
  if (!cont) return;
  cont.innerHTML = "";
  const bloques = bloquesActuales();
  if (!bloques.length) {
    const p = document.createElement("p");
    p.className = "sin-entradas";
    p.textContent = "Sin bloques todavía. Añádelos desde el menú «Añadir».";
    cont.appendChild(p);
    return;
  }
  bloques.forEach((b) => cont.appendChild(filaBloque(b)));
}

function filaBloque(b) {
  const div = document.createElement("div");
  div.className = "entrada";
  const claveBloque = b && b.id ? String(b.id) : "";
  aplicarColapso("bloques", claveBloque, div);
  const cab = document.createElement("div");
  cab.className = "cab-entrada";
  const rot = document.createElement("span");
  rot.className = "cab-txt";
  const nombre = document.createElement("span");
  nombre.textContent = etiquetaBloque(b);
  const pos = document.createElement("span");
  pos.className = "bloque-posicion";
  pos.textContent = etiquetaPosicion(b && b.posicion);
  pos.title = "Posición del bloque en el CV";
  rot.append(nombre, pos);

  const acciones = document.createElement("span");
  acciones.className = "bloque-acciones";
  acciones.style.display = "flex";
  acciones.style.alignItems = "center";
  acciones.style.gap = "6px";
  const ancla = ANCLAS_UI.indexOf(normalizarPosicion(b && b.posicion));

  const arriba = document.createElement("button");
  arriba.className = "pequeño";
  arriba.textContent = "↑";
  arriba.title = "Mover una posición antes en el CV";
  arriba.disabled = ancla <= 0;
  arriba.addEventListener("click", (e) => {
    e.stopPropagation();
    moverBloque(b, -1);
  });

  const abajo = document.createElement("button");
  abajo.className = "pequeño";
  abajo.textContent = "↓";
  abajo.title = "Mover una posición después en el CV";
  abajo.disabled = ancla >= ANCLAS_UI.length - 1;
  abajo.addEventListener("click", (e) => {
    e.stopPropagation();
    moverBloque(b, 1);
  });

  acciones.append(arriba, abajo);

  if (b && b.tipo === "seccion") {
    const editar = document.createElement("button");
    editar.className = "pequeño";
    editar.textContent = "Editar";
    editar.title = "Editar el título y el contenido";
    editar.addEventListener("click", (e) => {
      e.stopPropagation();
      abrirModalBloqueSeccion(b);
    });
    acciones.appendChild(editar);
  }

  const quitar = document.createElement("button");
  quitar.className = "btn-quitar";
  quitar.textContent = "✕";
  quitar.title = "Eliminar bloque";
  quitar.addEventListener("click", (e) => {
    e.stopPropagation();
    eliminarBloque(b);
  });
  acciones.appendChild(quitar);

  cab.append(rot, acciones);
  cab.addEventListener("click", (e) => {
    if (e.target.closest("button")) return;
    alternarColapso("bloques", claveBloque, div);
  });
  div.appendChild(cab);
  return div;
}

function abrirModalBloqueSeccion(bloque) {
  _bloqueEditando = bloque || null;
  $("#bs-titulo").value = _bloqueEditando ? String(_bloqueEditando.titulo || "") : "";
  $("#bs-contenido").value = _bloqueEditando ? String(_bloqueEditando.contenido || "") : "";
  $("#modal-bloque-seccion").hidden = false;
  $("#bs-titulo").focus();
}

function aceptarBloqueSeccion() {
  const titulo = $("#bs-titulo").value.trim();
  const contenido = $("#bs-contenido").value.trim();
  if (!titulo && !contenido) {
    toast("Escribe un título o un contenido para la sección");
    return;
  }
  const editando = _bloqueEditando;
  _bloqueEditando = null;
  mutarBloques((bloques) => {
    if (editando && bloques.indexOf(editando) >= 0) {
      editando.titulo = titulo;
      editando.contenido = contenido;
    } else {
      bloques.push({ id: nuevoIdBloque(), tipo: "seccion", titulo, contenido, posicion: "final" });
    }
  });
  cerrarModal($("#modal-bloque-seccion"));
}

function abrirModalBloques() {
  pintarListaBloques($("#bloques-lista"));
  $("#modal-bloques").hidden = false;
}

function configurarBloques() {
  $("#bs-cancelar").addEventListener("click", () => {
    _bloqueEditando = null;
    cerrarModal($("#modal-bloque-seccion"));
  });
  $("#bs-aceptar").addEventListener("click", aceptarBloqueSeccion);
  $("#bloques-cerrar").addEventListener("click", () => cerrarModal($("#modal-bloques")));
}

/* ---------------- modo LaTeX ---------------- */

function entrarModoLatex() {
  state.modo = "latex";
  const host = $("#panel-formulario") || document.body;
  const panelForm = $("#form-panel");
  if (panelForm) panelForm.hidden = true;
  const previo = $("#panel-latex");
  if (previo) previo.remove();

  const cont = document.createElement("div");
  cont.id = "panel-latex";

  const barra = document.createElement("div");
  barra.id = "barra-latex";
  const rotulo = document.createElement("span");
  rotulo.textContent = "Código LaTeX generado — puedes editarlo a mano";
  const volver = document.createElement("button");
  volver.className = "pequeño";
  volver.id = "volver-formulario";
  volver.textContent = "Volver al formulario";
  volver.onclick = () => alternarToggle("latex");
  barra.append(rotulo, volver);

  const ta = document.createElement("textarea");
  ta.id = "texto-latex";
  ta.spellcheck = false;
  ta.value = state.texManual !== null ? state.texManual : (state.tex || "");
  state.texEditado = false;
  ta.addEventListener("input", () => {
    state.texManual = ta.value;
    state.texEditado = true;
    programarCompilacion();
  });

  cont.append(barra, ta);
  host.appendChild(cont);
  actualizarMarcas();
}

function salirModoLatex(recompilar) {
  state.modo = "formulario";
  state.texManual = null;
  state.texEditado = false;
  const pl = $("#panel-latex");
  if (pl) pl.remove();
  const panelForm = $("#form-panel");
  if (panelForm) panelForm.hidden = false;
  renderFormulario();
  actualizarMarcas();
  if (recompilar) programarCompilacion();
}

/* ---------------- wizard motor LaTeX ---------------- */

function abrirWizard() {
  $("#wz-progreso").hidden = true;
  $("#wz-estado").textContent = "";
  $("#wz-barra").style.width = "0%";
  $("#modal-wizard").hidden = false;
}

function cerrarWizard(ok) {
  $("#modal-wizard").hidden = true;
  state.latexOk = ok;
  $("#aviso-motor").hidden = ok;
  if (ok) compilar();
}

function configurarWizard() {
  $("#wz-instalar").addEventListener("click", async () => {
    const boton = $("#wz-instalar");
    boton.disabled = true;
    $("#wz-progreso").hidden = false;
    $("#wz-estado").textContent = "";
    $("#wz-barra").style.width = "0%";
    try {
      await api.install_latex();
    } catch (e) {
      boton.disabled = false;
      $("#wz-estado").textContent = "No se pudo iniciar la instalación.";
      console.error(e);
    }
  });

  $("#wz-tengo").addEventListener("click", async () => {
    const r = await api.comprobar_latex();
    if (r.ok) cerrarWizard(true);
    else $("#wz-estado").textContent = "No se encontró LaTeX en el sistema. Indica la ruta manualmente o instala TinyTeX.";
  });

  $("#wz-manual").addEventListener("click", async () => {
    const r = await api.elegir_ruta_latex();
    if (r.ok) cerrarWizard(true);
    else if (r.error) $("#wz-estado").textContent = r.error;
  });

  $("#wz-ahora").addEventListener("click", async (e) => {
    e.preventDefault();
    await api.marcar_setup_ignorado();
    cerrarWizard(false);
    $("#aviso-motor").hidden = false;
  });
}

window.__onInstallProgress = function (p) {
  if (p.total) {
    const porc = Math.min(100, Math.round((100 * p.hecho) / p.total));
    $("#wz-barra").style.width = porc + "%";
    $("#wz-progreso-texto").textContent =
      "Descargando e instalando TinyTeX… " + porc + "% (" + fmBytes(p.hecho) + " de " + fmBytes(p.total) + ")";
  } else {
    $("#wz-barra").style.width = "100%";
    $("#wz-progreso-texto").textContent = "Trabajando…";
  }
};

window.__onInstallDone = function (r) {
  $("#wz-instalar").disabled = false;
  $("#wz-barra").style.width = "100%";
  if (r.ok) {
    $("#wz-progreso").hidden = true;
    toast(r.msg);
    cerrarWizard(true);
  } else {
    $("#wz-progreso").hidden = true;
    $("#wz-estado").textContent = r.msg;
  }
};

/* ---------------- preferencias ---------------- */

async function abrirPrefs() {
  $("#pf-msj").textContent = "";
  $("#pf-papel").value = state.prefs.papel;
  $("#pf-fuente").value = String(state.prefs.fuente);
  $("#pf-autocompilar").checked = state.prefs.autocompilar;
  $("#pf-breakpoint").value = state.prefs.breakpoint;
  $("#pf-m-sup").value = state.prefs.margenes.top;
  $("#pf-m-inf").value = state.prefs.margenes.bottom;
  $("#pf-m-izq").value = state.prefs.margenes.left;
  $("#pf-m-der").value = state.prefs.margenes.right;
  $("#modal-prefs").hidden = false;
  comprobarMotorPrefs();
}

async function comprobarMotorPrefs() {
  const r = await api.comprobar_latex();
  $("#pf-motor-estado").textContent = r.ok ? "Motor listo: " + r.path : "Motor LaTeX no configurado";
  $("#aviso-motor").hidden = r.ok;
  state.latexOk = r.ok;
}

function configurarPrefs() {
  $("#pf-papel").addEventListener("change", (e) => {
    state.prefs.papel = e.target.value;
    api.set_prefs("papel", e.target.value);
    programarCompilacion();
  });
  $("#pf-fuente").addEventListener("change", (e) => {
    state.prefs.fuente = Number(e.target.value);
    api.set_prefs("fuente", Number(e.target.value));
    programarCompilacion();
  });
  $("#pf-autocompilar").addEventListener("change", (e) => {
    state.prefs.autocompilar = e.target.checked;
    api.set_prefs("autocompilar", e.target.checked);
    actualizarMarcas();
    if (e.target.checked) programarCompilacion();
  });
  $("#pf-breakpoint").addEventListener("change", (e) => {
    state.prefs.breakpoint = Number(e.target.value);
    api.set_prefs("breakpoint", Number(e.target.value));
    aplicarResponsive();
  });
  ["m-sup", "m-inf", "m-izq", "m-der"].forEach((id) => {
    $("#pf-" + id).addEventListener("change", () => {
      const m = {
        top: Number($("#pf-m-sup").value) || 0,
        bottom: Number($("#pf-m-inf").value) || 0,
        left: Number($("#pf-m-izq").value) || 0,
        right: Number($("#pf-m-der").value) || 0,
      };
      state.prefs.margenes = m;
      api.set_prefs("margenes", m);
      programarCompilacion();
    });
  });
  $("#pf-motor-comprobar").addEventListener("click", comprobarMotorPrefs);
  $("#pf-motor-ruta").addEventListener("click", async () => {
    const r = await api.elegir_ruta_latex();
    if (r.ok) {
      $("#pf-msj").textContent = "Ruta guardada.";
      await comprobarMotorPrefs();
      programarCompilacion();
    }
  });
  $("#pf-motor-instalar").addEventListener("click", () => {
    $("#modal-prefs").hidden = true;
    abrirWizard();
    $("#wz-instalar").click();
  });
  $("#pf-cerrar").addEventListener("click", () => {
    $("#modal-prefs").hidden = true;
    $("#pf-msj").textContent = "";
  });
}

/* ---------------- márgenes personalizados ---------------- */

function abrirModalMargenes() {
  $("#mg-sup").value = state.prefs.margenes.top;
  $("#mg-inf").value = state.prefs.margenes.bottom;
  $("#mg-izq").value = state.prefs.margenes.left;
  $("#mg-der").value = state.prefs.margenes.right;
  $("#modal-margenes").hidden = false;
}

function configurarMargenes() {
  $("#mg-aplicar").addEventListener("click", () => {
    const m = {
      top: Number($("#mg-sup").value) || 0,
      bottom: Number($("#mg-inf").value) || 0,
      left: Number($("#mg-izq").value) || 0,
      right: Number($("#mg-der").value) || 0,
    };
    state.prefs.margenes = m;
    api.set_prefs("margenes", m);
    $("#modal-margenes").hidden = true;
    programarCompilacion();
  });
  $("#mg-cancelar").addEventListener("click", () => {
    $("#modal-margenes").hidden = true;
  });
}

/* ---------------- confirmar / varios ---------------- */

function configurarConfirmar() {
  $("#confirmar-si").addEventListener("click", () => {
    const aceptar = _confirmarAceptar;
    cerrarModal($("#modal-confirmar"));
    if (aceptar) aceptar();
  });
  $("#confirmar-no").addEventListener("click", () => {
    const cancelar = _confirmarCancelar;
    cerrarModal($("#modal-confirmar"));
    if (cancelar) cancelar();
  });
}

function configurarModales() {
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      $$(".modal").forEach((m) => {
        if (!m.hidden) cerrarModal(m);
      });
    }
  });
  $$(".modal").forEach((m) => {
    m.addEventListener("click", (e) => {
      if (e.target.classList.contains("modal")) cerrarModal(e.target);
    });
  });
}

/* ---------------- atajos de teclado ---------------- */

function hayModalAbierto() {
  return $$(".modal").some((m) => !m.hidden);
}

function configurarAtajos() {
  document.addEventListener("keydown", (e) => {
    // Mientras se teclea (incluida la composición IME) el texto normal no se
    // intercepta: solo actúan las combinaciones con Ctrl.
    if (!(e.ctrlKey || e.metaKey) || e.altKey || e.isComposing) return;
    // Con un modal abierto no actúan los atajos globales (Escape los cierra).
    if (hayModalAbierto()) return;
    const k = String(e.key || "").toLowerCase();
    if (k === "z" && !e.shiftKey) {
      // En el editor LaTeX se respeta el deshacer nativo del textarea.
      if (state.modo === "latex") return;
      e.preventDefault();
      deshacer();
      return;
    }
    if (k === "y" || (k === "z" && e.shiftKey)) {
      if (state.modo === "latex") return;
      e.preventDefault();
      rehacer();
      return;
    }
    if (k === "s") {
      if (e.repeat) return; // no repetir el diálogo al mantener pulsado
      e.preventDefault();
      accionGuardar();
      return;
    }
    if (k === "o") {
      if (e.repeat) return;
      e.preventDefault();
      accionAbrir();
      return;
    }
    if (k === "n") {
      if (e.repeat) return;
      e.preventDefault();
      accionNuevo();
      return;
    }
    if (k === "enter") {
      // Ctrl+Enter recompila; el Enter normal sigue escribiendo en los campos.
      e.preventDefault();
      clearTimeout(state.timer);
      compilar();
      return;
    }
  });
}

/* ---------------- responsive ---------------- */

function aplicarResponsive() {
  const bp = Number(state.prefs && state.prefs.breakpoint) || 960;
  document.body.classList.toggle("apilado", window.innerWidth < bp);
}

/* ---------------- inicio ---------------- */

async function iniciar() {
  try {
    api = await apiLista();
    if (!api) {
      estado("pywebview no disponible: ejecuta la app con main.py", "error");
      return;
    }
    const info = await api.init();
    state.prefs = info.prefs;
    aplicarTema(state.prefs.tema);
    datosVacios = await api.datos_vacios();
    state.datos = JSON.parse(JSON.stringify(datosVacios));
    state.latexOk = info.latex_ok;

    let autosavePendiente = null;
    try {
      const a = await api.autosave_leer();
      if (a && typeof a === "object" && !Array.isArray(a)) autosavePendiente = a;
    } catch (e) {
      console.error(e);
    }

    renderFormulario();
    actualizarMarcas();
    actualizarBotonesHistorial();
    aplicarResponsive();
    window.addEventListener("resize", aplicarResponsive);
    $("#aviso-motor").hidden = info.latex_ok;

    configurarWizard();
    configurarPrefs();
    configurarMargenes();
    configurarConfirmar();
    configurarModales();
    configurarRecorte();
    configurarBloques();
    configurarAtajos();
    setInterval(autosaveYa, 30000);

    if (autosavePendiente) ofrecerRecuperacion(autosavePendiente);
    if (info.needs_setup) abrirWizard();
    else compilar();
  } catch (e) {
    estado("Error al iniciar: " + (e && e.message ? e.message : e), "error");
    console.error(e);
  }
}

iniciar();