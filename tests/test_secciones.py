# -*- coding: utf-8 -*-
"""Orden, titulos y secciones ocultas: build_tex, saneado y compilacion.

Cubre para las plantillas de ``latex_gen.TEMPLATES`` x (es, zh) con CV
completo: orden por defecto de titulos, orden personalizado (claves invalidas
y duplicadas ignoradas, faltantes anadidas), secciones ocultas (sin titulo ni
entradas, pero con su bloque anclado en posicion) y titulos personalizados con
escapado, fallback a LANG y descarte de valores no texto. Ademas el saneado
tolerante via ``main.migrate_data``, el round-trip .cvjson con ``Api`` y
compilaciones reales con el mismo patron skipif de test_bloques.py.

Todo corre sin GUI; las compilaciones se saltan cuando no hay motor LaTeX
(pdflatex / xelatex) instalado.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import ejemplo  # noqa: E402
import latex_engine  # noqa: E402
import latex_gen  # noqa: E402
import main  # noqa: E402
import prefs  # noqa: E402
import tex_datos  # noqa: E402

TEMPLATES = latex_gen.TEMPLATES
IDIOMAS = ("es", "zh")
ORDEN = list(latex_gen.DEFAULT_SECTION_ORDER)

MOTOR_PDF = latex_engine.find_pdflatex()
MOTOR_CJK = latex_engine.find_xelatex()

# Titulo que exige esc(): %, & y ~. En zh se usa ademas texto CJK para que la
# compilacion obligue a XeLaTeX.
TITULO_CUSTOM = "I+D 100% & ~"
TITULO_CUSTOM_ESC = "\\cvsection{I+D 100\\% \\& \\textasciitilde{}}"
TITULO_CUSTOM_ZH = "工作经历 100% & ~"

# Texto unico de la seccion que se oculta: no debe sobrevivir en el cuerpo.
MARCADOR_OCULTO = {"es": "ProyectoSecreto", "zh": "秘密项目"}

# Bloque anclado a "projects" para comprobar que una seccion oculta conserva
# la posicion de sus bloques.
BLOQUE_ANCLA = {
    "id": "bloque-ancla",
    "type": "separator",
    "style": "band",
    "position": "projects",
}


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


def datos_completos(idioma):
    """CV completo: las 9 secciones estandar con contenido en el idioma dado."""
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
            "name": "秘密项目", "organization": "个人项目", "start": "2023",
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
            "name": "ProyectoSecreto", "organization": "Hackathon Climate",
            "start": "2023", "end": "2023", "description": "App de rutas sostenibles.",
        }]
        d["university_projects"] = [{
            "name": "Gestor de biblioteca", "course": "Ingeniería del Software",
            "organization": "Universidad de Madrid", "start": "2015", "end": "2015",
            "description": "Proyecto de asignatura.",
        }]
        d["skills"] = [{"category": "Lenguajes", "values": "Python, Java"}]
        d["languages"] = [{"language": "Español", "level": "Nativo"}]
        d["references"] = [{"name": "Luis Pérez", "contact": "luis@example.com"}]
    return d


def _cuerpo(tex):
    """Parte del .tex a partir de \\begin{document} (sin preambulo ni datos)."""
    return tex[tex.index("\\begin{document}"):]


def _indice(tex, aguja):
    """Indice de `aguja` dentro del cuerpo (ignora el preambulo)."""
    return tex.index(aguja, tex.index("\\begin{document}"))


def _titulo(idioma, clave):
    """Titulo de seccion que build_tex emite con LANG para idioma y clave."""
    return "\\cvsection{" + latex_gen.esc(latex_gen.LANG[idioma][clave]) + "}"


# ---------------------------------------------------------------------------
# build_tex: las plantillas de TEMPLATES x (es, zh)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("plantilla", TEMPLATES)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_orden_por_defecto_de_titulos(plantilla, idioma, prefs_tmp):
    datos = datos_completos(idioma)
    datos["plantilla"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())

    assert "{{" not in tex
    assert tex_datos.extract(tex) == datos

    cuerpo = _cuerpo(tex)
    assert cuerpo.count("\\cvsection{") == len(ORDEN)
    indices = [_indice(tex, _titulo(idioma, clave)) for clave in ORDEN]
    assert indices == sorted(indices)
    assert len(set(indices)) == len(ORDEN)


# Orden bruto con una clave invalida y una duplicada, y el resultado esperado
# tras normalizar (las faltantes se anaden al final en orden por defecto).
ORDEN_BRUTO = ["work", "marte", "work", "university_projects"]
ORDEN_NORMALIZADO = [
    "work", "university_projects", "education", "summary", "internships",
    "projects", "skills", "languages", "references",
]


@pytest.mark.parametrize("plantilla", TEMPLATES)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_orden_personalizado_ignora_invalidas_duplicadas_y_anade_faltantes(
    plantilla, idioma, prefs_tmp
):
    datos = datos_completos(idioma)
    datos["template"] = plantilla
    datos["section_order"] = list(ORDEN_BRUTO)
    tex = latex_gen.build_tex(datos, prefs.load())

    assert "{{" not in tex
    assert tex_datos.extract(tex) == datos
    assert latex_gen.normalize_section_order(datos) == ORDEN_NORMALIZADO

    cuerpo = _cuerpo(tex)
    assert "marte" not in cuerpo
    assert cuerpo.count("\\cvsection{") == len(ORDEN)
    indices = [_indice(tex, _titulo(idioma, clave)) for clave in ORDEN_NORMALIZADO]
    assert indices == sorted(indices)


@pytest.mark.parametrize("plantilla", TEMPLATES)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_seccion_oculta_suprime_titulo_y_entradas_pero_conserva_su_bloque(
    plantilla, idioma, prefs_tmp
):
    datos = datos_completos(idioma)
    datos["template"] = plantilla
    datos["hidden_sections"] = ["projects"]
    datos["section_titles"] = {"projects": "Titulo que no debe salir"}
    datos["blocks"] = [dict(BLOQUE_ANCLA)]
    tex = latex_gen.build_tex(datos, prefs.load())

    assert "{{" not in tex
    assert tex_datos.extract(tex) == datos

    cuerpo = _cuerpo(tex)
    # Ni el titulo (ni siquiera uno personalizado) ni las entradas salen...
    assert _titulo(idioma, "projects") not in cuerpo
    assert "Titulo que no debe salir" not in cuerpo
    assert MARCADOR_OCULTO[idioma] not in cuerpo
    assert cuerpo.count("\\cvsection{") == len(ORDEN) - 1
    # ...pero el bloque anclado a la seccion oculta mantiene su posicion:
    # despues de education y antes de university_projects (orden por defecto).
    i_educacion = _indice(tex, _titulo(idioma, "education"))
    i_bloque = _indice(tex, "\\cvblockband")
    i_proyectosu = _indice(tex, _titulo(idioma, "university_projects"))
    assert i_educacion < i_bloque < i_proyectosu


@pytest.mark.parametrize("plantilla", TEMPLATES)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_titulos_personalizados_se_escapan_y_hay_fallback_a_lang(
    plantilla, idioma, prefs_tmp
):
    datos = datos_completos(idioma)
    datos["template"] = plantilla
    datos["section_titles"] = {
        "work": TITULO_CUSTOM,
        "summary": "  Perfil personalizado  ",
    }
    tex = latex_gen.build_tex(datos, prefs.load())

    assert "{{" not in tex
    assert tex_datos.extract(tex) == datos

    cuerpo = _cuerpo(tex)
    assert TITULO_CUSTOM_ESC in cuerpo
    assert "\\cvsection{Perfil personalizado}" in cuerpo
    # Las secciones sin titulo personalizado usan LANG.
    assert _titulo(idioma, "education") in cuerpo
    assert _titulo(idioma, "work") not in cuerpo
    assert _titulo(idioma, "summary") not in cuerpo
    assert cuerpo.count("\\cvsection{") == len(ORDEN)


# ---------------------------------------------------------------------------
# Saneado tolerante via main.migrate_data (como al abrir un .cvjson)
# ---------------------------------------------------------------------------

class _Explosivo:
    """Objeto hostil: ni str() ni comparacion funcionan."""

    def __str__(self):
        raise RuntimeError("__str__ explosivo")

    def __eq__(self, other):
        raise RuntimeError("__eq__ explosivo")

    __hash__ = None


class _StrStripExplosivo(str):
    """Subclase de str cuyo strip() lanza."""

    def strip(self, *args, **kwargs):
        raise RuntimeError("strip explosivo")

    __hash__ = str.__hash__


def _secciones_saneadas(datos):
    """Pasa por migrate_data y devuelve las 3 claves de secciones."""
    salida = main.migrate_data(datos)
    return (
        salida["section_titles"],
        salida["hidden_sections"],
        salida["section_order"],
    )


def test_migrar_secciones_validas_se_normalizan():
    titulos, ocultas, orden = _secciones_saneadas({
        # Claves y valores antiguos: se traducen al esquema canonico.
        "titulos_seccion": {"perfil": "  Sobre mí  ", "trabajo": "Experiencia",
                            "marte": "x"},
        # Dedup conservando la primera aparicion y descarte de invalidas.
        "secciones_ocultas": ["trabajo", "trabajo", "marte", "idiomas"],
        # Dedup + faltantes anadidas al final en orden por defecto.
        "orden_secciones": ["idiomas", "marte", "idiomas", "trabajo"],
    })
    assert titulos == {"summary": "Sobre mí", "work": "Experiencia"}
    assert ocultas == ["work", "languages"]
    assert orden == [
        "languages", "work", "education", "summary", "internships",
        "projects", "university_projects", "skills", "references",
    ]


def test_migrar_secciones_ausentes_quedan_canonicas():
    assert _secciones_saneadas({}) == ({}, [], list(ORDEN))


@pytest.mark.parametrize("entrada", [[], ()])
def test_migrar_orden_vacio_conserva_el_centinela(entrada):
    # La lista vacia es el centinela de empty_data(): no se expande al
    # guardar/migrar; normalizar_orden_secciones la expande al renderizar.
    _, _, orden = _secciones_saneadas({"section_order": entrada})
    assert orden == []


@pytest.mark.parametrize(
    "entrada", [None, "work", {"work": 1}, 7, _Explosivo()]
)
def test_migrar_orden_malformado_cae_al_orden_por_defecto(entrada):
    _, _, orden = _secciones_saneadas({"section_order": entrada})
    assert orden == list(ORDEN)


def test_migrar_titulos_descarta_no_str_vacios_y_claves_invalidas():
    titulos, _, _ = _secciones_saneadas({"section_titles": {
        "summary": "  Perfil OK  ",
        "work": 5,
        "education": None,
        "projects": "   ",
        "languages": b"bytes",
        "marte": "x",
    }})
    assert titulos == {"summary": "Perfil OK"}


@pytest.mark.parametrize(
    "datos",
    [
        {"section_order": [_Explosivo()]},
        {"section_order": [[], {"x": 1}, (), _Explosivo()]},
        {"hidden_sections": [_Explosivo(), set(), {}]},
        {"hidden_sections": _Explosivo()},
        {"hidden_sections": [["work"], "marte", 7]},
        {"section_titles": {"summary": _Explosivo()}},
        {"section_titles": {"summary": _StrStripExplosivo("Perfil")}},
        {"section_titles": _Explosivo()},
        {"section_order": _Explosivo()},
    ],
)
def test_migrar_secciones_hostiles_no_lanzan(datos):
    titulos, ocultas, orden = _secciones_saneadas(dict(datos))
    assert titulos == {}
    assert ocultas == []
    assert orden == list(ORDEN)


# ---------------------------------------------------------------------------
# Round-trip .cvjson con Api
# ---------------------------------------------------------------------------

ORDEN_CANONICO = [
    "languages", "summary", "education", "projects", "university_projects",
    "internships", "work", "skills", "references",
]


def test_cvjson_roundtrip_conserva_las_tres_claves(prefs_tmp, monkeypatch):
    datos = datos_completos("es")
    datos["template"] = "modern"
    datos["section_order"] = list(ORDEN_CANONICO)
    datos["hidden_sections"] = ["projects", "languages"]
    datos["section_titles"] = {"work": TITULO_CUSTOM, "summary": "Perfil propio"}
    ruta = prefs_tmp / "secciones.cvjson"

    api = main.Api(None)
    monkeypatch.setattr(api, "choose_file", lambda *a, **k: str(ruta))

    salida = api.export_cv(datos)
    assert salida == {"ok": True, "ruta": str(ruta)}
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    assert contenido["version"] == 3
    for clave in ("section_titles", "hidden_sections", "section_order"):
        assert contenido["data"][clave] == datos[clave]

    abierto = api.open_cv()
    assert abierto["ok"] is True
    for clave in ("section_titles", "hidden_sections", "section_order"):
        assert abierto["datos"][clave] == datos[clave]


def test_cvjson_abrir_sanea_las_tres_claves_escritas_a_mano(prefs_tmp, monkeypatch):
    datos = datos_completos("es")
    datos["section_order"] = ["languages", "marte", "languages", "work"]
    datos["hidden_sections"] = ["work", "work", "marte", 7, None]
    datos["section_titles"] = {
        "work": 5, "summary": "  Perfil X  ", "marte": "x", "languages": "   ",
    }
    ruta = prefs_tmp / "sucio.cvjson"
    ruta.write_text(
        json.dumps({"version": 2, "datos": datos, "medios": {}}, ensure_ascii=False),
        encoding="utf-8",
    )

    api = main.Api(None)
    monkeypatch.setattr(api, "choose_file", lambda *a, **k: str(ruta))

    abierto = api.open_cv()
    assert abierto["ok"] is True
    assert abierto["datos"]["section_titles"] == {"summary": "Perfil X"}
    assert abierto["datos"]["hidden_sections"] == ["work"]
    assert abierto["datos"]["section_order"] == [
        "languages", "work", "education", "summary", "internships",
        "projects", "university_projects", "skills", "references",
    ]


# ---------------------------------------------------------------------------
# Compilaciones reales (mismo patron skipif que test_bloques.py)
# ---------------------------------------------------------------------------

def datos_compilacion(idioma):
    """CV completo con orden parcial, una seccion oculta y un titulo custom."""
    datos = datos_completos(idioma)
    datos["section_order"] = ["work", "summary", "languages"]
    datos["hidden_sections"] = ["projects"]
    datos["section_titles"] = {
        "work": TITULO_CUSTOM if idioma == "es" else TITULO_CUSTOM_ZH,
    }
    datos["blocks"] = [dict(BLOQUE_ANCLA)]
    return datos


@pytest.mark.latex
@pytest.mark.skipif(MOTOR_PDF is None, reason="Sin motor LaTeX (pdflatex) instalado")
@pytest.mark.parametrize("plantilla", TEMPLATES)
def test_compila_pdf_secciones_es(plantilla, prefs_tmp):
    datos = datos_compilacion("es")
    datos["template"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "{{" not in tex
    assert tex_datos.extract(tex) == datos
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])


@pytest.mark.latex
@pytest.mark.skipif(
    MOTOR_PDF is None or MOTOR_CJK is None,
    reason="Sin motores LaTeX (pdflatex/xelatex) para compilar texto CJK",
)
@pytest.mark.parametrize("plantilla", TEMPLATES)
def test_compila_pdf_secciones_zh(plantilla, prefs_tmp):
    datos = datos_compilacion("zh")
    datos["template"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "{{" not in tex
    assert tex_datos.extract(tex) == datos
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])


# ---------------------------------------------------------------------------
# Regresion: un titulo por defecto con "&" (en: "Skills & certificates")
# debe escaparse igual que un titulo personalizado.
# ---------------------------------------------------------------------------

def test_seccion_por_defecto_con_ampersand_se_escapa(prefs_tmp):
    datos = ejemplo.sample_data("en")
    datos["template"] = "classic"
    tex = latex_gen.build_tex(datos, prefs.load())

    assert "\\cvsection{Skills \\& certificates}" in tex
    assert "\\cvsection{Skills & certificates}" not in tex


@pytest.mark.latex
@pytest.mark.skipif(MOTOR_PDF is None, reason="Sin motor LaTeX (pdflatex) instalado")
def test_compila_pdf_sample_en_con_ampersand_en_titulo(prefs_tmp):
    datos = ejemplo.sample_data("en")
    datos["template"] = "classic"
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "\\cvsection{Skills \\& certificates}" in tex

    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])
