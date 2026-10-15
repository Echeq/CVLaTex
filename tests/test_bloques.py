# -*- coding: utf-8 -*-
"""Bloques libres: round-trip LaTeX, orden por anclas, separadores, compilacion
PDF y preservacion en .cvjson v2.

El round-trip, el orden y el .cvjson corren siempre (sin LaTeX). Las
compilaciones se saltan con el mismo patron skipif de test_roundtrip_tex.py
cuando no hay motor LaTeX (pdflatex / xelatex) instalado.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_engine  # noqa: E402
import latex_gen  # noqa: E402
import main  # noqa: E402
import prefs  # noqa: E402
import tex_datos  # noqa: E402

TEMPLATES = latex_gen.TEMPLATES
IDIOMAS = ("es", "zh")

MOTOR_PDF = latex_engine.find_pdflatex()
MOTOR_CJK = latex_engine.find_xelatex()

# Orden de las secciones estandar en el cuerpo de todas las plantillas.
CLAVES_SECCIONES = (
    "summary", "education", "projects", "university_projects", "internships",
    "work", "skills", "languages", "references",
)


@pytest.fixture()
def prefs_tmp(tmp_path, monkeypatch):
    """Aisla prefs (dirs y cache) del equipo del usuario."""
    app = tmp_path / "app"
    monkeypatch.setattr(prefs, "APP_DIR", str(app))
    monkeypatch.setattr(prefs, "CACHE_DIR", str(app / "cache"))
    monkeypatch.setattr(prefs, "BUILD_DIR", str(app / "cache" / "build"))
    monkeypatch.setattr(prefs, "PREFS_FILE", str(app / "prefs.json"))
    monkeypatch.setattr(prefs, "_CACHE", None)
    return tmp_path


def datos_bloques(idioma):
    """CV completo con bloques en inicio/educacion/final y un ancla invalida."""
    d = latex_gen.empty_data()
    d["cv_language"] = idioma
    if idioma == "zh":
        d["name"] = "张伟"
        d["profession"] = "后端开发工程师"
        d["email"] = "zhangwei@example.com"
        d["summary"] = "五年后端开发经验，熟悉 Python 与分布式系统。"
        d["education"] = [{
            "degree_type": "bachelor", "degree": "计算机科学与技术",
            "institution": "清华大学",
            "start": "2012", "end": "2016", "grade": "3.8/4.0",
        }]
        d["work"] = [{
            "position": "高级后端工程师", "company": "字节跳动", "start": "2020",
            "end": "至今", "achievements": "主导支付网关重构。",
        }]
        d["internships"] = [{
            "position": "后端实习生", "company": "腾讯", "start": "2015", "end": "2016",
            "achievements": "参与内部工具开发。",
        }]
        d["projects"] = [{
            "name": "开源简历工具", "organization": "个人项目", "start": "2023",
            "end": "2024", "description": "基于 Python 的简历生成器。",
        }]
        d["university_projects"] = [{
            "name": "校园导航", "course": "软件工程", "organization": "清华大学",
            "start": "2015", "end": "2015", "description": "课程项目。",
        }]
        d["skills"] = [{"category": "编程语言", "values": "Python, Go"}]
        d["languages"] = [{"language": "中文", "level": "母语"}]
        d["references"] = [{"name": "李雷", "contact": "lilei@example.com"}]
    else:
        d["name"] = "Ana García López"
        d["profession"] = "Ingeniera de software"
        d["email"] = "ana.garcia@example.com"
        d["summary"] = "Cinco años de experiencia en Python y sistemas distribuidos."
        d["education"] = [{
            "degree_type": "bachelor", "degree": "Ingeniería Informática",
            "institution": "Universidad de Madrid", "start": "2012", "end": "2016",
            "grade": "8.5/10",
        }]
        d["work"] = [{
            "position": "Ingeniera backend", "company": "Fintech Nova", "start": "2020",
            "end": "Actualidad", "achievements": "Lideré la migración a microservicios.",
        }]
        d["internships"] = [{
            "position": "Becaria de desarrollo", "company": "Telecom Ibérica",
            "start": "2015", "end": "2016", "achievements": "Automaticé informes semanales.",
        }]
        d["projects"] = [{
            "name": "Rutas verdes", "organization": "Hackathon Climate", "start": "2023",
            "end": "2023", "description": "App de rutas sostenibles.",
        }]
        d["university_projects"] = [{
            "name": "Gestor de biblioteca", "course": "Ingeniería del Software",
            "organization": "Universidad de Madrid", "start": "2015", "end": "2015",
            "description": "Proyecto de asignatura.",
        }]
        d["skills"] = [{"category": "Lenguajes", "values": "Python, Java"}]
        d["languages"] = [{"language": "Español", "level": "Nativo"}]
        d["references"] = [{"name": "Luis Pérez", "contact": "luis@example.com"}]
    d["blocks"] = [
        {"id": "bloque-linea", "type": "separator", "style": "line",
         "position": "start"},
        {"id": "bloque-banda", "type": "separator", "style": "band",
         "position": "education"},
        {"id": "bloque-seccion", "type": "section", "title": "Mi sección 100%",
         "content": "Primera línea.\nSegunda línea.", "position": "education"},
        {"id": "bloque-espacio", "type": "separator", "style": "space",
         "position": "end"},
    ]
    return d


def _indice(tex, aguja):
    """Indice de `aguja` dentro del cuerpo (ignora las definiciones del preambulo)."""
    return tex.index(aguja, tex.index("\\begin{document}"))


def _titulo(idioma, clave):
    """Titulo de seccion emitido por build_tex para el idioma y la clave dados."""
    return "\\cvsection{" + latex_gen.LANG[idioma][clave] + "}"


def _ultima_seccion(tex, idioma):
    """Indice del ultimo titulo de seccion estandar del cuerpo."""
    return max(_indice(tex, _titulo(idioma, c)) for c in CLAVES_SECCIONES)


@pytest.mark.parametrize("plantilla", TEMPLATES)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_build_tex_bloques_roundtrip_orden_y_separadores(plantilla, idioma, prefs_tmp):
    datos = datos_bloques(idioma)
    datos["template"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())

    # Sin marcadores pendientes y round-trip exacto (los bloques sobreviven).
    assert "{{" not in tex
    assert tex_datos.extract(tex) == datos

    # El bloque de "inicio" va antes del primer titulo de seccion (perfil).
    assert _indice(tex, "\\cvblockline") < _indice(tex, _titulo(idioma, "summary"))

    # Los bloques de "educacion" van despues del titulo de educacion y antes
    # del siguiente bloque de la misma ancla (se respeta el orden de la lista).
    edu = _indice(tex, _titulo(idioma, "education"))
    banda = _indice(tex, "\\cvblockband")
    custom = _indice(tex, "\\cvsection{Mi sección 100\\%}")
    assert edu < banda < custom

    # El bloque de "final" cierra el cuerpo, despues de la ultima seccion.
    ultima = _ultima_seccion(tex, idioma)
    espacio = _indice(tex, "\\cvblockspace")
    assert espacio > ultima
    assert espacio > _indice(tex, _titulo(idioma, "references"))
    assert espacio < tex.index("\\end{document}")

    # Los tres estilos de separador emiten su macro y el titulo personalizado
    # pasa por esc() (el '%' del titulo sale escapado).
    for macro in ("\\cvblockline", "\\cvblockband", "\\cvblockspace"):
        assert _indice(tex, macro) < tex.index("\\end{document}")
    assert "\\%" in tex


@pytest.mark.parametrize("plantilla", TEMPLATES)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_bloque_con_posicion_invalida_cae_al_final(plantilla, idioma, prefs_tmp):
    datos = datos_bloques(idioma)
    datos["template"] = plantilla
    datos["blocks"] = [
        {"id": "sin-ancla", "type": "section", "title": "Ancla desconocida",
         "content": "Primero.", "position": "marte"},
        {"id": "tras-refs", "type": "section", "title": "Tras referencias",
         "content": "Segundo.", "position": "references"},
    ]
    tex = latex_gen.build_tex(datos, prefs.load())
    assert tex_datos.extract(tex) == datos
    # El ancla invalida acaba despues de la ancla "referencias", es decir, al final.
    assert _indice(tex, "\\cvsection{Ancla desconocida}") > _indice(
        tex, "\\cvsection{Tras referencias}"
    )
    assert _indice(tex, "\\cvsection{Ancla desconocida}") > _ultima_seccion(tex, idioma)


def test_build_tex_bloques_listado_columnas_y_periodo(prefs_tmp):
    datos = latex_gen.empty_data()
    datos["cv_language"] = "es"
    datos["blocks"] = [
        {"id": "lista-2", "type": "list", "mode": "columns",
         "title": "Enlaces", "columns": 2, "position": "start",
         "entries": [
             {"title": "Web", "detail": "example.com"},
             {"title": "Github", "detail": "github.com/ana"},
         ]},
        {"id": "crono", "type": "list", "mode": "period",
         "title": "Cronología", "columns": 1, "position": "end",
         "entries": [{"period": "2020 -- 2024",
                      "description": "Etapa uno.\nLínea dos."}]},
    ]
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "{{" not in tex
    assert tex_datos.extract(tex) == datos
    assert "\\cvsection{Enlaces}" in tex
    assert "\\cvsection{Cronología}" in tex
    assert "\\textbf{Web}" in tex and "example.com" in tex
    assert "\\itshape 2020 -- 2024" in tex
    assert "Etapa uno." in tex and "Línea dos." in tex
    # Las dos entradas de la lista en 2 columnas comparten fila (2 minipages)
    # y el bloque de cronología va despues del de enlaces.
    assert _indice(tex, "\\cvsection{Enlaces}") < _indice(tex, "\\cvsection{Cronología}")
    cuerpo = tex[tex.index("\\begin{document}"):]
    fila = cuerpo[cuerpo.index("\\cvsection{Enlaces}"):cuerpo.index("\\cvsection{Cronología}")]
    assert fila.count("\\begin{minipage}") == 2
    assert "\\hfill" in fila


@pytest.mark.skipif(MOTOR_PDF is None, reason="Sin motor LaTeX (pdflatex) instalado")
@pytest.mark.parametrize("plantilla", TEMPLATES)
def test_compila_pdf_bloques_es(plantilla, prefs_tmp):
    datos = datos_bloques("es")
    datos["template"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])


@pytest.mark.skipif(
    MOTOR_PDF is None or MOTOR_CJK is None,
    reason="Sin motores LaTeX (pdflatex/xelatex) para compilar texto CJK",
)
@pytest.mark.parametrize("plantilla", TEMPLATES)
def test_compila_pdf_bloques_zh(plantilla, prefs_tmp):
    datos = datos_bloques("zh")
    datos["template"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])


@pytest.mark.parametrize("plantilla", TEMPLATES)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_cvjson_v3_conserva_bloques_intactos(plantilla, idioma, prefs_tmp, monkeypatch):
    datos = datos_bloques(idioma)
    datos["template"] = plantilla
    ruta = prefs_tmp / "bloques.cvjson"

    api = main.Api(None)
    monkeypatch.setattr(api, "choose_file", lambda *a, **k: str(ruta))

    salida = api.export_cv(datos)
    assert salida == {"ok": True, "ruta": str(ruta)}
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    assert contenido["version"] == 3
    assert contenido["data"]["blocks"] == datos["blocks"]

    abierto = api.open_cv()
    assert abierto["ok"] is True
    assert abierto["datos"]["blocks"] == datos["blocks"]
