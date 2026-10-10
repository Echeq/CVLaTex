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

PLANTILLAS = latex_gen.PLANTILLAS
IDIOMAS = ("es", "zh")

MOTOR_PDF = latex_engine.find_pdflatex()
MOTOR_CJK = latex_engine.find_xelatex()

# Orden de las secciones estandar en el cuerpo de todas las plantillas.
CLAVES_SECCIONES = (
    "perfil", "educacion", "proyectos", "proyectosu", "pasantia", "trabajo",
    "habilidades", "idiomas", "referencias",
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
    d = latex_gen.datos_vacios()
    d["idioma_cv"] = idioma
    if idioma == "zh":
        d["nombre"] = "张伟"
        d["profesion"] = "后端开发工程师"
        d["email"] = "zhangwei@example.com"
        d["perfil"] = "五年后端开发经验，熟悉 Python 与分布式系统。"
        d["educacion"] = [{
            "tipo": "本科", "titulo": "计算机科学与技术", "institucion": "清华大学",
            "desde": "2012", "hasta": "2016", "nota": "3.8/4.0",
        }]
        d["trabajo"] = [{
            "puesto": "高级后端工程师", "empresa": "字节跳动", "desde": "2020",
            "hasta": "至今", "logros": "主导支付网关重构。",
        }]
        d["pasantia"] = [{
            "puesto": "后端实习生", "empresa": "腾讯", "desde": "2015", "hasta": "2016",
            "logros": "参与内部工具开发。",
        }]
        d["proyectos"] = [{
            "nombre": "开源简历工具", "organizacion": "个人项目", "desde": "2023",
            "hasta": "2024", "descripcion": "基于 Python 的简历生成器。",
        }]
        d["proyectosu"] = [{
            "nombre": "校园导航", "asignatura": "软件工程", "organizacion": "清华大学",
            "desde": "2015", "hasta": "2015", "descripcion": "课程项目。",
        }]
        d["habilidades"] = [{"categoria": "编程语言", "valores": "Python, Go"}]
        d["idiomas"] = [{"idioma": "中文", "nivel": "母语"}]
        d["referencias"] = [{"nombre": "李雷", "contacto": "lilei@example.com"}]
    else:
        d["nombre"] = "Ana García López"
        d["profesion"] = "Ingeniera de software"
        d["email"] = "ana.garcia@example.com"
        d["perfil"] = "Cinco años de experiencia en Python y sistemas distribuidos."
        d["educacion"] = [{
            "tipo": "Grado", "titulo": "Ingeniería Informática",
            "institucion": "Universidad de Madrid", "desde": "2012", "hasta": "2016",
            "nota": "8.5/10",
        }]
        d["trabajo"] = [{
            "puesto": "Ingeniera backend", "empresa": "Fintech Nova", "desde": "2020",
            "hasta": "Actualidad", "logros": "Lideré la migración a microservicios.",
        }]
        d["pasantia"] = [{
            "puesto": "Becaria de desarrollo", "empresa": "Telecom Ibérica",
            "desde": "2015", "hasta": "2016", "logros": "Automaticé informes semanales.",
        }]
        d["proyectos"] = [{
            "nombre": "Rutas verdes", "organizacion": "Hackathon Climate", "desde": "2023",
            "hasta": "2023", "descripcion": "App de rutas sostenibles.",
        }]
        d["proyectosu"] = [{
            "nombre": "Gestor de biblioteca", "asignatura": "Ingeniería del Software",
            "organizacion": "Universidad de Madrid", "desde": "2015", "hasta": "2015",
            "descripcion": "Proyecto de asignatura.",
        }]
        d["habilidades"] = [{"categoria": "Lenguajes", "valores": "Python, Java"}]
        d["idiomas"] = [{"idioma": "Español", "nivel": "Nativo"}]
        d["referencias"] = [{"nombre": "Luis Pérez", "contacto": "luis@example.com"}]
    d["bloques"] = [
        {"id": "bloque-linea", "tipo": "separador", "estilo": "linea",
         "posicion": "inicio"},
        {"id": "bloque-banda", "tipo": "separador", "estilo": "banda",
         "posicion": "educacion"},
        {"id": "bloque-seccion", "tipo": "seccion", "titulo": "Mi sección 100%",
         "contenido": "Primera línea.\nSegunda línea.", "posicion": "educacion"},
        {"id": "bloque-espacio", "tipo": "separador", "estilo": "espacio",
         "posicion": "final"},
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


@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_build_tex_bloques_roundtrip_orden_y_separadores(plantilla, idioma, prefs_tmp):
    datos = datos_bloques(idioma)
    datos["plantilla"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())

    # Sin marcadores pendientes y round-trip exacto (los bloques sobreviven).
    assert "{{" not in tex
    assert tex_datos.extraer(tex) == datos

    # El bloque de "inicio" va antes del primer titulo de seccion (perfil).
    assert _indice(tex, "\\cvbloquelinea") < _indice(tex, _titulo(idioma, "perfil"))

    # Los bloques de "educacion" van despues del titulo de educacion y antes
    # del siguiente bloque de la misma ancla (se respeta el orden de la lista).
    edu = _indice(tex, _titulo(idioma, "educacion"))
    banda = _indice(tex, "\\cvbloquebanda")
    custom = _indice(tex, "\\cvsection{Mi sección 100\\%}")
    assert edu < banda < custom

    # El bloque de "final" cierra el cuerpo, despues de la ultima seccion.
    ultima = _ultima_seccion(tex, idioma)
    espacio = _indice(tex, "\\cvbloqueespacio")
    assert espacio > ultima
    assert espacio > _indice(tex, _titulo(idioma, "referencias"))
    assert espacio < tex.index("\\end{document}")

    # Los tres estilos de separador emiten su macro y el titulo personalizado
    # pasa por esc() (el '%' del titulo sale escapado).
    for macro in ("\\cvbloquelinea", "\\cvbloquebanda", "\\cvbloqueespacio"):
        assert _indice(tex, macro) < tex.index("\\end{document}")
    assert "\\%" in tex


@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_bloque_con_posicion_invalida_cae_al_final(plantilla, idioma, prefs_tmp):
    datos = datos_bloques(idioma)
    datos["plantilla"] = plantilla
    datos["bloques"] = [
        {"id": "sin-ancla", "tipo": "seccion", "titulo": "Ancla desconocida",
         "contenido": "Primero.", "posicion": "marte"},
        {"id": "tras-refs", "tipo": "seccion", "titulo": "Tras referencias",
         "contenido": "Segundo.", "posicion": "referencias"},
    ]
    tex = latex_gen.build_tex(datos, prefs.load())
    assert tex_datos.extraer(tex) == datos
    # El ancla invalida acaba despues de la ancla "referencias", es decir, al final.
    assert _indice(tex, "\\cvsection{Ancla desconocida}") > _indice(
        tex, "\\cvsection{Tras referencias}"
    )
    assert _indice(tex, "\\cvsection{Ancla desconocida}") > _ultima_seccion(tex, idioma)


def test_build_tex_bloques_listado_columnas_y_periodo(prefs_tmp):
    datos = latex_gen.datos_vacios()
    datos["idioma_cv"] = "es"
    datos["bloques"] = [
        {"id": "lista-2", "tipo": "listado", "modo": "columnas",
         "titulo": "Enlaces", "columnas": 2, "posicion": "inicio",
         "entradas": [
             {"titulo": "Web", "detalle": "example.com"},
             {"titulo": "Github", "detalle": "github.com/ana"},
         ]},
        {"id": "crono", "tipo": "listado", "modo": "periodo",
         "titulo": "Cronología", "columnas": 1, "posicion": "final",
         "entradas": [{"periodo": "2020 -- 2024",
                       "descripcion": "Etapa uno.\nLínea dos."}]},
    ]
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "{{" not in tex
    assert tex_datos.extraer(tex) == datos
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
@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_compila_pdf_bloques_es(plantilla, prefs_tmp):
    datos = datos_bloques("es")
    datos["plantilla"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])


@pytest.mark.skipif(
    MOTOR_PDF is None or MOTOR_CJK is None,
    reason="Sin motores LaTeX (pdflatex/xelatex) para compilar texto CJK",
)
@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_compila_pdf_bloques_zh(plantilla, prefs_tmp):
    datos = datos_bloques("zh")
    datos["plantilla"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])


@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_cvjson_v2_conserva_bloques_intactos(plantilla, idioma, prefs_tmp, monkeypatch):
    datos = datos_bloques(idioma)
    datos["plantilla"] = plantilla
    ruta = prefs_tmp / "bloques.cvjson"

    api = main.Api(None)
    monkeypatch.setattr(api, "elegir_archivo", lambda *a, **k: str(ruta))

    salida = api.exportar_cv(datos)
    assert salida == {"ok": True, "ruta": str(ruta)}
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    assert contenido["version"] == 2
    assert contenido["datos"]["bloques"] == datos["bloques"]

    abierto = api.abrir_cv()
    assert abierto["ok"] is True
    assert abierto["datos"]["bloques"] == datos["bloques"]
