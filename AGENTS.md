# AGENTS.md

CVLaTeX: editor de currículums de escritorio para Windows (pywebview + JS vanilla) que genera LaTeX y compila PDF. Backend en Python, frontend en `web/`, sin tests, lint ni CI.

## Comandos

- Ejecutar la app (abre GUI, bloquea): `.venv\Scripts\python.exe main.py`
- Compilar exe de un solo fichero: `build.bat` (activa `.venv`, PyInstaller `--onefile --windowed`, empaqueta `web;web` y `templates;templates` con `--add-data`) -> `dist\CVLaTeX.exe`
- Instalar dependencias: `.venv\Scripts\pip install -r requirements.txt` (pywebview + pyinstaller + python-docx)
- Smoke check del backend (sin GUI ni LaTeX): `.venv\Scripts\python.exe -c "import latex_gen, prefs; print(latex_gen.build_tex(latex_gen.datos_vacios(), prefs.load())[:120])"`
- Verificar el round-trip LaTeX (build_tex + extraer, sin GUI ni LaTeX): `.venv\Scripts\python.exe -c "import latex_gen, prefs, tex_datos; d=latex_gen.datos_vacios(); t=tex_datos.incrustar(latex_gen.build_tex(d, prefs.load()), d); assert tex_datos.extraer(t)==d; print('round-trip OK')"`
- Validar el frontend sin navegador (si hay Node): `node --check web/app.js`
- La compilación PDF necesita `pdflatex`, resuelto en este orden: prefs `latex_path` -> TinyTeX empaquetado en `%LOCALAPPDATA%\CVLaTeX\tinytex` -> `PATH`. El texto CJK cambia automáticamente a `xelatex`.
- Exportar Word (.docx) NO requiere LaTeX: usa python-docx.

## Arquitectura

- `main.py`: shell pywebview más un servidor HTTP local en un puerto aleatorio `127.0.0.1` que sirve `web/` en `/`, PDFs compilados en `/preview/` y medios subidos en `/media/`. Los métodos de `Api` son el puente JS (`window.pywebview.api.*`); cualquier cambio de API necesita el cambio correspondiente en `web/app.js`.
- `latex_gen.py`: `datos_vacios()` es el esquema de datos canónico; `build_tex()` rellena los marcadores de la plantilla. La clave `plantilla` del CV (se elige en "Editar -> Plantilla del CV") admite `clasico|harvard|moderno|creativo|chino` (etiqueta UI "Chino (estándar)") y mapea a subcarpetas de `templates/` (`clasico` -> `clasico/plantilla.tex`, `harvard` -> `harvard/harvard.tex`, `moderno` -> `moderno/moderno.tex`, `creativo` -> `creativo/creativo.tex`, `chino` -> `chino/chino.tex`); `templates/` se empaqueta con `--add-data` y se resuelve vía `BASE_DIR`. Todas las etiquetas de sección viven en `LANG` (zh/es/en); `idioma_cv` por defecto es `"zh"`, que selecciona las fuentes Microsoft YaHei y XeLaTeX.
- `docx_gen.py`: exportación Word con python-docx, independiente de LaTeX y pywebview.
- `ejemplo.py`: `datos_ejemplo()` genera el ejemplo común en español y sin imágenes; `datos_ejemplo_cn()` genera el ejemplo ficticio en chino que "Editar -> Cargar CV de ejemplo" carga en el formulario cuando la plantilla es `chino`.
- `tex_datos.py`: incrusta y extrae el bloque de datos del .tex. Todo .tex generado o exportado lleva un bloque `% CVLaTeX-DATA-BEGIN` / `% CVLaTeX-DATA-END` con los datos en base64 (son comentarios LaTeX, así que el documento compila igual). La acción "Importar LaTeX (.tex)" reconstruye el formulario desde ese bloque; los .tex ajenos se rechazan con una alerta de incompatibilidad (no hay parser heurístico).
- `latex_engine.py`: las compilaciones se serializan con un lock y borran primero `%LOCALAPPDATA%\CVLaTeX\cache\build`; los errores se extraen de `main.log`. La URL de descarga de TinyTeX está fijada en `TINYTEX_URLS`.
- `prefs.py`: prefs JSON en `%LOCALAPPDATA%\CVLaTeX\prefs.json` con caché a nivel de módulo; `save`/`set` la refrescan. La preferencia `tema` (`claro|oscuro|sistema`, por defecto `sistema`) solo afecta a la UI, nunca al PDF ni al .tex.
- Formato de guardado `.cvjson` v1. Al añadir campos de datos, actualiza `datos_vacios()` y `_migrar_datos()` en `main.py`.
- Los builds congelados deben conservar el fallback `sys._MEIPASS` en `BASE_DIR` (`main.py`, `latex_gen.py`) o el exe no encuentra `web/` ni `templates/`.

## Convenciones

- Código, comentarios, textos de UI y claves de datos en español (`puesto`, `logros`, `elegir_foto`, ...). Mantén los identificadores en español.
- Todo texto de usuario inyectado en TeX debe pasar por `esc()` en `latex_gen.py`.
- Las claves de sección `trabajo`, `pasantia`, `proyectos`, `proyectosu`, `educacion` admiten 1-3 columnas vía `columnas`.
- Cada plantilla vive en su propia subcarpeta de `templates/`; al añadir una hay que registrarla en `PLANTILLAS`/`ARCHIVOS` de `latex_gen.py` y en `PLANTILLAS_CV` de `web/app.js`. `templates/chino/Elvis Chen CV.docx` es la referencia del estándar chino y se empaqueta con `--add-data` (el usuario lo acepta).
- Sin paso de build del frontend: edita `web/index.html`, `web/app.js`, `web/style.css` directamente.

## Pipeline opencode

- `.opencode/agents/` contiene el pipeline planner/orchestrator/worker/evaluator-optimizer; `opencode.json` fija el modelo por defecto y `subagent_depth: 2`. Ejecuta `/smoke` tras cambiar agentes o reiniciar opencode.
- `.opencode/node_modules` es tooling del pipeline de agentes, no dependencias de la app; las dependencias de la app viven en `requirements.txt`.
