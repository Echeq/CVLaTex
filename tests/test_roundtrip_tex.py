# -*- coding: utf-8 -*-
"""Round-trip LaTeX: build_tex -> tex_datos.extraer y compilacion PDF.

El round-trip corre siempre (sin LaTeX). Las compilaciones se saltan con
pytest.mark.skipif cuando no hay motor LaTeX instalado.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_engine  # noqa: E402
import latex_gen  # noqa: E402
import prefs  # noqa: E402
import tex_datos  # noqa: E402

PLANTILLAS = latex_gen.PLANTILLAS
IDIOMAS = ("zh", "es")

MOTOR_PDF = latex_engine.find_pdflatex()
MOTOR_CJK = latex_engine.find_xelatex()


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


def datos_minimos(idioma):
    """CV minimo y realista, con todas las secciones con contenido."""
    d = latex_gen.datos_vacios()
    d["idioma_cv"] = idioma
    if idioma == "zh":
        d["nombre"] = "张伟"
        d["profesion"] = "后端开发工程师"
        d["email"] = "zhangwei@example.com"
        d["telefono"] = "13800000000"
        d["direccion"] = "北京市朝阳区"
        d["nacimiento"] = "1994年5月"
        d["nacionalidad"] = "中国"
        d["institucion_egresado"] = "清华大学"
        d["perfil"] = "五年后端开发经验，熟悉 Python 与分布式系统。"
        d["datos_extra"] = [{"etiqueta": "城市", "valor": "北京"}]
        d["educacion"] = [{
            "tipo": "本科", "titulo": "计算机科学与技术", "institucion": "清华大学",
            "desde": "2012", "hasta": "2016", "nota": "3.8/4.0",
        }]
        d["trabajo"] = [{
            "puesto": "高级后端工程师", "empresa": "字节跳动", "modalidad": "全职",
            "desde": "2020", "hasta": "至今",
            "logros": "主导支付网关重构，延迟下降 40%。\n维护核心调度服务。",
        }]
        d["pasantia"] = [{
            "puesto": "后端实习生", "empresa": "腾讯", "desde": "2015", "hasta": "2016",
            "logros": "参与内部工具开发。",
        }]
        d["proyectos"] = [{
            "nombre": "开源简历工具", "organizacion": "个人项目", "desde": "2023",
            "hasta": "2024", "descripcion": "基于 Python 的简历生成器。",
            "resultado": "GitHub 两千星", "enlace": "github.com/example/cv",
        }]
        d["proyectosu"] = [{
            "nombre": "校园导航", "asignatura": "软件工程", "organizacion": "清华大学",
            "desde": "2015", "hasta": "2015", "descripcion": "课程项目。",
        }]
        d["habilidades"] = [{"categoria": "编程语言", "valores": "Python, Go"}]
        d["idiomas"] = [{"idioma": "中文", "nivel": "母语"}, {"idioma": "英语", "nivel": "CET-6"}]
        d["referencias"] = [{"nombre": "李雷", "contacto": "lilei@example.com"}]
    else:
        d["nombre"] = "Ana García López"
        d["profesion"] = "Ingeniera de software"
        d["email"] = "ana.garcia@example.com"
        d["telefono"] = "+34 600 000 000"
        d["direccion"] = "Calle Mayor 1, Madrid"
        d["nacimiento"] = "12/05/1994"
        d["nacionalidad"] = "Española"
        d["web"] = "https://anagarcia.dev"
        d["github"] = "github.com/anagarcia"
        d["linkedin"] = "linkedin.com/in/anagarcia"
        d["institucion_egresado"] = "Universidad de Madrid"
        d["perfil"] = "Cinco años de experiencia en Python y sistemas distribuidos."
        d["datos_extra"] = [{"etiqueta": "Ciudad", "valor": "Madrid"}]
        d["educacion"] = [{
            "tipo": "Grado", "titulo": "Ingeniería Informática",
            "institucion": "Universidad de Madrid", "desde": "2012", "hasta": "2016",
            "nota": "8.5/10",
        }]
        d["trabajo"] = [{
            "puesto": "Ingeniera backend", "empresa": "Fintech Nova", "modalidad": "Híbrido",
            "desde": "2020", "hasta": "Actualidad",
            "logros": "Lideré la migración a microservicios.\nOptimicé consultas SQL.",
        }]
        d["pasantia"] = [{
            "puesto": "Becaria de desarrollo", "empresa": "Telecom Ibérica",
            "desde": "2015", "hasta": "2016", "logros": "Automaticé informes semanales.",
        }]
        d["proyectos"] = [{
            "nombre": "Rutas verdes", "organizacion": "Hackathon Climate", "desde": "2023",
            "hasta": "2023", "descripcion": "App de rutas sostenibles.",
            "resultado": "Primer premio", "enlace": "github.com/anagarcia/rutas",
        }]
        d["proyectosu"] = [{
            "nombre": "Gestor de biblioteca", "asignatura": "Ingeniería del Software",
            "organizacion": "Universidad de Madrid", "desde": "2015", "hasta": "2015",
            "descripcion": "Proyecto de asignatura.",
        }]
        d["habilidades"] = [{"categoria": "Lenguajes", "valores": "Python, Java"}]
        d["idiomas"] = [{"idioma": "Español", "nivel": "Nativo"}, {"idioma": "Inglés", "nivel": "B2"}]
        d["referencias"] = [{"nombre": "Luis Pérez", "contacto": "luis@example.com"}]
    return d


@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_build_tex_sin_marcadores_y_roundtrip(plantilla, idioma, prefs_tmp):
    datos = datos_minimos(idioma)
    datos["plantilla"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "{{" not in tex
    assert tex_datos.extraer(tex) == datos


@pytest.mark.skipif(MOTOR_PDF is None, reason="Sin motor LaTeX (pdflatex) instalado")
@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_compila_pdf_es(plantilla, prefs_tmp):
    datos = datos_minimos("es")
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
def test_compila_pdf_zh(plantilla, prefs_tmp):
    datos = datos_minimos("zh")
    datos["plantilla"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])
