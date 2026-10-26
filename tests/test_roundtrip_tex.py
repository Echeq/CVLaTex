# -*- coding: utf-8 -*-
"""Round-trip LaTeX: build_tex -> tex_datos.extract y compilacion PDF.

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

TEMPLATES = latex_gen.TEMPLATES
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
    d = latex_gen.empty_data()
    d["cv_language"] = idioma
    if idioma == "zh":
        d["name"] = "张伟"
        d["profession"] = "后端开发工程师"
        d["email"] = "zhangwei@example.com"
        d["phone"] = "13800000000"
        d["address"] = "北京市朝阳区"
        d["socials"] = [
            {"network": "github", "label": "", "value": "github.com/zhangwei"},
            {"network": "linkedin", "label": "", "value": "linkedin.com/in/zhangwei"},
        ]
        d["school_name"] = "清华大学"
        d["summary"] = "五年后端开发经验，熟悉 Python 与分布式系统。"
        d["extra_fields"] = [
            {"label": "出生年月", "value": "1994年5月"},
            {"label": "国籍", "value": "中国"},
            {"label": "城市", "value": "北京"},
        ]
        d["education"] = [{
            "degree_type": "bachelor", "degree": "计算机科学与技术",
            "institution": "清华大学",
            "start": "2012", "end": "2016", "grade": "3.8/4.0",
        }]
        d["work"] = [{
            "position": "高级后端工程师", "company": "字节跳动", "work_mode": "onsite",
            "start": "2020", "end": "至今",
            "achievements": "主导支付网关重构，延迟下降 40%。\n维护核心调度服务。",
        }]
        d["internships"] = [{
            "position": "后端实习生", "company": "腾讯", "start": "2015", "end": "2016",
            "achievements": "参与内部工具开发。",
        }]
        d["projects"] = [{
            "name": "开源简历工具", "organization": "个人项目", "start": "2023",
            "end": "2024", "description": "基于 Python 的简历生成器。",
            "result": "GitHub 两千星", "link": "github.com/example/cv",
        }]
        d["university_projects"] = [{
            "name": "校园导航", "course": "软件工程", "organization": "清华大学",
            "start": "2015", "end": "2015", "description": "课程项目。",
        }]
        d["skills"] = [{"category": "编程语言", "values": "Python, Go"}]
        d["languages"] = [{"language": "中文", "level": "母语"}, {"language": "英语", "level": "CET-6"}]
        d["references"] = [{"name": "李雷", "contact": "lilei@example.com"}]
    else:
        d["name"] = "Ana García López"
        d["profession"] = "Ingeniera de software"
        d["email"] = "ana.garcia@example.com"
        d["phone"] = "+34 600 000 000"
        d["address"] = "Calle Mayor 1, Madrid"
        d["socials"] = [
            {"network": "github", "label": "", "value": "github.com/anagarcia"},
            {"network": "linkedin", "label": "", "value": "linkedin.com/in/anagarcia"},
            {"network": "website", "label": "", "value": "https://anagarcia.dev"},
        ]
        d["school_name"] = "Universidad de Madrid"
        d["summary"] = "Cinco años de experiencia en Python y sistemas distribuidos."
        d["extra_fields"] = [
            {"label": "Nacimiento", "value": "12/05/1994"},
            {"label": "Nacionalidad", "value": "Española"},
            {"label": "Ciudad", "value": "Madrid"},
        ]
        d["education"] = [{
            "degree_type": "bachelor", "degree": "Ingeniería Informática",
            "institution": "Universidad de Madrid", "start": "2012", "end": "2016",
            "grade": "8.5/10",
        }]
        d["work"] = [{
            "position": "Ingeniera backend", "company": "Fintech Nova", "work_mode": "hybrid",
            "start": "2020", "end": "Actualidad",
            "achievements": "Lideré la migración a microservicios.\nOptimicé consultas SQL.",
        }]
        d["internships"] = [{
            "position": "Becaria de desarrollo", "company": "Telecom Ibérica",
            "start": "2015", "end": "2016", "achievements": "Automaticé informes semanales.",
        }]
        d["projects"] = [{
            "name": "Rutas verdes", "organization": "Hackathon Climate", "start": "2023",
            "end": "2023", "description": "App de rutas sostenibles.",
            "result": "Primer premio", "link": "github.com/anagarcia/rutas",
        }]
        d["university_projects"] = [{
            "name": "Gestor de biblioteca", "course": "Ingeniería del Software",
            "organization": "Universidad de Madrid", "start": "2015", "end": "2015",
            "description": "Proyecto de asignatura.",
        }]
        d["skills"] = [{"category": "Lenguajes", "values": "Python, Java"}]
        d["languages"] = [{"language": "Español", "level": "Nativo"}, {"language": "Inglés", "level": "B2"}]
        d["references"] = [{"name": "Luis Pérez", "contact": "luis@example.com"}]
    return d


@pytest.mark.parametrize("plantilla", TEMPLATES)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_build_tex_sin_marcadores_y_roundtrip(plantilla, idioma, prefs_tmp):
    datos = datos_minimos(idioma)
    datos["template"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "{{" not in tex
    assert tex_datos.extract(tex) == datos


@pytest.mark.latex
@pytest.mark.skipif(MOTOR_PDF is None, reason="Sin motor LaTeX (pdflatex) instalado")
@pytest.mark.parametrize("plantilla", TEMPLATES)
def test_compila_pdf_es(plantilla, prefs_tmp):
    datos = datos_minimos("es")
    datos["template"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])


@pytest.mark.latex
@pytest.mark.skipif(
    MOTOR_PDF is None or MOTOR_CJK is None,
    reason="Sin motores LaTeX (pdflatex/xelatex) para compilar texto CJK",
)
@pytest.mark.parametrize("plantilla", TEMPLATES)
def test_compila_pdf_zh(plantilla, prefs_tmp):
    datos = datos_minimos("zh")
    datos["template"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])
