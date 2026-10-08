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
  idCompilacion: 0,
  timer: null,
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
function confirmar(msj, alAceptar) {
  $("#confirmar-msj").textContent = msj;
  _confirmarAceptar = alAceptar;
  $("#confirmar-no").hidden = false;
  $("#modal-confirmar").hidden = false;
}

function alerta(msj) {
  $("#confirmar-msj").textContent = msj;
  _confirmarAceptar = null;
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
  if (el) ejecutarAccion(el.dataset.accion);
});

function ejecutarAccion(accion) {
  if (accion.startsWith("papel:")) aplicarPapel(accion.split(":")[1]);
  else if (accion.startsWith("margenes:")) aplicarMargenes(accion.split(":")[1]);
  else if (accion.startsWith("fuente:")) aplicarFuente(Number(accion.split(":")[1]));
  else if (accion.startsWith("tema:")) cambiarTema(accion.split(":")[1]);
  else if (accion.startsWith("plantilla:")) aplicarPlantilla(accion.split(":")[1]);
  else if (accion.startsWith("toggle:")) alternarToggle(accion.split(":")[1]);
  else {
    switch (accion) {
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
      case "recompilar": compilar(); break;
      case "ayuda": $("#modal-ayuda").hidden = false; break;
      case "creditos": $("#modal-creditos").hidden = false; break;
      case "cerrar-modal": e.target.closest(".modal").hidden = true; break;
    }
  }
}

async function accionNuevo() {
  confirmar("¿Descartar el CV actual y comenzar uno nuevo?", () => {
    if (state.modo === "latex") salirModoLatex(false);
    state.datos = JSON.parse(JSON.stringify(datosVacios));
    renderFormulario();
    actualizarMarcas();
    programarCompilacion();
    toast("CV nuevo creado");
  });
}

async function accionAbrir() {
  const r = await api.abrir_cv();
  if (r.ok && r.datos) {
    if (state.modo === "latex") salirModoLatex(false);
    state.datos = r.datos;
    renderFormulario();
    actualizarMarcas();
    programarCompilacion();
    toast("Abierto: " + r.ruta);
  } else if (r.errores) {
    toast(r.errores[0]);
  }
}

async function accionGuardar() {
  const r = await api.exportar_cv(state.datos);
  if (r.ok) toast("Guardado: " + r.ruta);
  else if (r.errores) toast(r.errores[0]);
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
    if (state.modo === "latex") salirModoLatex(false);
    state.datos = r.datos;
    renderFormulario();
    actualizarMarcas();
    programarCompilacion();
    toast("LaTeX importado: " + r.ruta);
  } else if (r.errores) {
    alerta(r.errores[0]);
  }
}

async function accionCargarEjemplo() {
  const hayContenido = Object.keys(datosVacios).some(
    (k) => k !== "plantilla" && JSON.stringify(state.datos[k]) !== JSON.stringify(datosVacios[k])
  );
  const aplicar = async () => {
    const r = await api.cargar_ejemplo(state.datos.plantilla);
    if (!r.ok) {
      toast((r.errores && r.errores[0]) || "No se pudo cargar el ejemplo");
      return;
    }
    if (state.modo === "latex") salirModoLatex(false);
    state.datos = r.datos;
    renderFormulario();
    actualizarMarcas();
    programarCompilacion();
    toast("Ejemplo cargado: sustituye estos datos por los tuyos");
  };
  if (hayContenido) {
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
  state.datos.plantilla = esValida ? v : "clasico";
  programarCompilacion();
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
      const editado = state.texManual !== null && state.textoLatexDirty();
      confirmar(
        editado
          ? "El código LaTeX se editó a mano. Al volver al formulario se regenerará desde los datos y se perderán los cambios manuales. ¿Continuar?"
          : "¿Volver al formulario?",
        () => { state.texManual = null; salirModoLatex(true); }
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
    await api.compilar_tex(state.texManual !== null ? state.texManual : state.tex, id);
  } else {
    await api.compile(state.datos, id);
  }
}

window.__onCompile = function (res) {
  if (res.id !== state.idCompilacion) return;
  const ep = $("#estado-preview");
  if (res.ok) {
    $("#errores").hidden = true;
    $("#aviso-motor").hidden = true;
    $("#pdf").src = "/preview/main.pdf?v=" + Date.now();
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

/* ---------------- formulario ---------------- */

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
      state.datos.columnas[clave] = Number(sel.value);
      programarCompilacion();
    });
    rot.appendChild(sel);
    cab.appendChild(rot);
  }
  const contenido = document.createElement("div");
  contenido.className = "sec-contenido";
  t.appendChild(cab);
  t.appendChild(contenido);
  t.contenido = contenido;
  cab.addEventListener("click", (e) => {
    if (e.target.closest("select")) return;
    t.classList.toggle("colapsada");
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
    state.datos[k] = inp.value;
    programarCompilacion();
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
  img.src = "/media/" + state.datos.foto.split(/[\\/]/).pop();
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
    state.datos.foto_ancho_cm = Number(inpA.value) || 4;
    state.datos.foto_alto_cm = Number(inpAl.value) || 5;
    programarCompilacion();
  };
  inpA.addEventListener("change", () => { aplicarTam(); pintarFoto(); });
  inpAl.addEventListener("change", () => { aplicarTam(); pintarFoto(); });
  elegir.onclick = async () => {
    const r = await api.elegir_foto();
    if (r.ok) {
      state.datos.foto = r.path;
      state.datos.foto_original = r.path;
      state.datos.foto_recorte = null;
      actualizarTam();
      pintarFoto();
      programarCompilacion();
    } else if (r.error) toast(r.error);
  };
  ajustar.onclick = () => abrirRecorte();
  quitar.onclick = () => {
    state.datos.foto = "";
    state.datos.foto_original = "";
    state.datos.foto_recorte = null;
    pintarFoto();
    programarCompilacion();
  };
  actualizarTam();
  pintarFoto();
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
  img.src = "/media/" + origen.split(/[\\/]/).pop();
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
      programarCompilacion();
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
      const cab = document.createElement("div");
      cab.className = "cab-entrada";
      const rot = document.createElement("span");
      rot.className = "cab-txt";
      const chev = document.createElement("span");
      chev.className = "chevron";
      chev.textContent = "▾";
      rot.append(chev, document.createTextNode(" " + def.titulo.replace(/s$/, "") + " " + (idx + 1)));
      const quitar = document.createElement("button");
      quitar.className = "btn-quitar";
      quitar.textContent = "✕";
      quitar.title = "Eliminar entrada";
      quitar.onclick = (e) => {
        e.stopPropagation();
        state.datos[key].splice(idx, 1);
        pintar();
        programarCompilacion();
      };
      cab.append(rot, quitar);
      cab.addEventListener("click", (e) => {
        if (e.target.closest(".btn-quitar")) return;
        div.classList.toggle("colapsada");
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
            ent[c.k] = sel.value;
            programarCompilacion();
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
            const r = await api.elegir_foto();
            if (r.ok) {
              ent[c.k] = r.path;
              pintarLogo();
              programarCompilacion();
            } else if (r.error) toast(r.error);
          };
          const quitar = document.createElement("button");
          quitar.className = "btn-quitar";
          quitar.textContent = "✕";
          quitar.title = "Quitar logo";
          quitar.onclick = () => {
            ent[c.k] = "";
            pintarLogo();
            programarCompilacion();
          };
          pintarLogo();
          fila.append(boton, quitar, estadoSpan);
          camp.appendChild(fila);
        } else {
          const inp = document.createElement(c.area ? "textarea" : "input");
          inp.value = ent[c.k] || "";
          inp.addEventListener("input", () => {
            ent[c.k] = inp.value;
            programarCompilacion();
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
      state.datos[key].push(vacio);
      pintar();
      programarCompilacion();
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
    const r = await api.elegir_foto();
    if (r.ok) {
      state.datos[k] = r.path;
      pintar();
      programarCompilacion();
    } else if (r.error) toast(r.error);
  };
  const quitar = document.createElement("button");
  quitar.className = "btn-quitar";
  quitar.textContent = "✕";
  quitar.title = "Quitar logo";
  quitar.onclick = () => {
    state.datos[k] = "";
    pintar();
    programarCompilacion();
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
    state.datos.logo_egresado_ancho_cm = Number(inpA.value) || 2.4;
    programarCompilacion();
  });
  inpAl.addEventListener("change", () => {
    state.datos.logo_egresado_alto_cm = Number(inpAl.value) || 0.85;
    programarCompilacion();
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
    state.datos.idioma_cv = sel.value;
    programarCompilacion();
  });
  camp.append(lb, sel);
  return camp;
}

function renderFormulario() {
  const cont = $("#form-panel");
  cont.innerHTML = "";
  cont.id = "form-panel";

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
}

/* ---------------- modo LaTeX ---------------- */

function entrarModoLatex() {
  state.modo = "latex";
  const form = $("#panel-formulario");
  form.innerHTML = "";

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
  ta.addEventListener("input", () => {
    state.texManual = ta.value;
    programarCompilacion();
  });

  cont.append(barra, ta);
  form.appendChild(cont);
  state.textoLatexDirty = () => ta.value !== (state.tex || "");
  actualizarMarcas();
}

function salirModoLatex(recompilar) {
  state.modo = "formulario";
  state.textoLatexDirty = null;
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
    $("#wz-progreso").hidden = false;
    $("#wz-estado").textContent = "";
    $("#wz-barra").style.width = "0%";
    await api.install_latex();
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
    $("#modal-confirmar").hidden = true;
    if (_confirmarAceptar) _confirmarAceptar();
    _confirmarAceptar = null;
  });
  $("#confirmar-no").addEventListener("click", () => {
    $("#modal-confirmar").hidden = true;
    _confirmarAceptar = null;
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

    renderFormulario();
    actualizarMarcas();
    aplicarResponsive();
    window.addEventListener("resize", aplicarResponsive);
    $("#aviso-motor").hidden = info.latex_ok;

    configurarWizard();
    configurarPrefs();
    configurarMargenes();
    configurarConfirmar();
    configurarRecorte();

    if (info.needs_setup) abrirWizard();
    else compilar();
  } catch (e) {
    estado("Error al iniciar: " + (e && e.message ? e.message : e), "error");
    console.error(e);
  }
}

iniciar();