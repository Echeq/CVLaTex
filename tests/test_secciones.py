# -*- coding: utf-8 -*-
"""Orden, titulos y secciones ocultas: build_tex, saneado y compilacion.

Cubre para las 5 plantillas de ``latex_gen.PLANTILLAS`` x (es, zh) con CV
completo: orden por defecto de titulos, orden personalizado (claves invalidas
y duplicadas ignoradas, faltantes anadidas), secciones ocultas (sin titulo ni
entradas, pero con su bloque anclado en posicion) y titulos personalizados con
escapado, fallback a LANG y descarte de valores no texto. Ademas el saneado
tolerante via ``main._migrar_datos``, el round-trip .cvjson con ``Api`` y
compilaciones reales con el mismo patron skipif de test_bloques.py.

Todo corre sin GUI; las compilaciones se saltan cuando no hay motor LaTeX
(pdflatex / xelatex) instalado.
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
ORDEN = list(latex_gen.ORDEN_SECCIONES_DEFECTO)

MOTOR_PDF = latex_engine.find_pdflatex()
MOTOR_CJK = latex_engine.find_xelatex()

# Titulo que exige esc(): %, & y ~. En zh se usa ademas texto CJK para que la
# compilacion obligue a XeLaTeX.
TITULO_CUSTOM = "I+D 100% & ~"
TITULO_CUSTOM_ESC = "\\cvsection{I+D 100\\% \\& \\textasciitilde{}}"
TITULO_CUSTOM_ZH = "工作经历 100% & ~"

# Texto unico de la seccion que se oculta: no debe sobrevivir en el cuerpo.
MARCADOR_OCULTO = {"es": "ProyectoSecreto", "zh": "秘密项目"}

# Bloque anclado a "proyectos" para comprobar que una seccion oculta conserva
# la posicion de sus bloques.
BLOQUE_ANCLA = {
    "id": "bloque-ancla",
    "tipo": "separador",
    "estilo": "banda",
    "posicion": "proyectos",
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
            "nombre": "秘密项目", "organizacion": "个人项目", "desde": "2023",
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
            "nombre": "ProyectoSecreto", "organizacion": "Hackathon Climate",
            "desde": "2023", "hasta": "2023", "descripcion": "App de rutas sostenibles.",
        }]
        d["proyectosu"] = [{
            "nombre": "Gestor de biblioteca", "asignatura": "Ingeniería del Software",
            "organizacion": "Universidad de Madrid", "desde": "2015", "hasta": "2015",
            "descripcion": "Proyecto de asignatura.",
        }]
        d["habilidades"] = [{"categoria": "Lenguajes", "valores": "Python, Java"}]
        d["idiomas"] = [{"idioma": "Español", "nivel": "Nativo"}]
        d["referencias"] = [{"nombre": "Luis Pérez", "contacto": "luis@example.com"}]
    return d


def _cuerpo(tex):
    """Parte del .tex a partir de \\begin{document} (sin preambulo ni datos)."""
    return tex[tex.index("\\begin{document}"):]


def _indice(tex, aguja):
    """Indice de `aguja` dentro del cuerpo (ignora el preambulo)."""
    return tex.index(aguja, tex.index("\\begin{document}"))


def _titulo(idioma, clave):
    """Titulo de seccion que build_tex emite con LANG para idioma y clave."""
    return "\\cvsection{" + latex_gen.LANG[idioma][clave] + "}"


# ---------------------------------------------------------------------------
# build_tex: las 5 plantillas x (es, zh)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_orden_por_defecto_de_titulos(plantilla, idioma, prefs_tmp):
    datos = datos_completos(idioma)
    datos["plantilla"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())

    assert "{{" not in tex
    assert tex_datos.extraer(tex) == datos

    cuerpo = _cuerpo(tex)
    assert cuerpo.count("\\cvsection{") == len(ORDEN)
    indices = [_indice(tex, _titulo(idioma, clave)) for clave in ORDEN]
    assert indices == sorted(indices)
    assert len(set(indices)) == len(ORDEN)


# Orden bruto con una clave invalida y una duplicada, y el resultado esperado
# tras normalizar (las faltantes se anaden al final en orden por defecto).
ORDEN_BRUTO = ["trabajo", "marte", "trabajo", "proyectosu"]
ORDEN_NORMALIZADO = [
    "trabajo", "proyectosu", "perfil", "educacion", "proyectos", "pasantia",
    "habilidades", "idiomas", "referencias",
]


@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_orden_personalizado_ignora_invalidas_duplicadas_y_anade_faltantes(
    plantilla, idioma, prefs_tmp
):
    datos = datos_completos(idioma)
    datos["plantilla"] = plantilla
    datos["orden_secciones"] = list(ORDEN_BRUTO)
    tex = latex_gen.build_tex(datos, prefs.load())

    assert "{{" not in tex
    assert tex_datos.extraer(tex) == datos
    assert latex_gen.normalizar_orden_secciones(datos) == ORDEN_NORMALIZADO

    cuerpo = _cuerpo(tex)
    assert "marte" not in cuerpo
    assert cuerpo.count("\\cvsection{") == len(ORDEN)
    indices = [_indice(tex, _titulo(idioma, clave)) for clave in ORDEN_NORMALIZADO]
    assert indices == sorted(indices)


@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_seccion_oculta_suprime_titulo_y_entradas_pero_conserva_su_bloque(
    plantilla, idioma, prefs_tmp
):
    datos = datos_completos(idioma)
    datos["plantilla"] = plantilla
    datos["secciones_ocultas"] = ["proyectos"]
    datos["titulos_seccion"] = {"proyectos": "Titulo que no debe salir"}
    datos["bloques"] = [dict(BLOQUE_ANCLA)]
    tex = latex_gen.build_tex(datos, prefs.load())

    assert "{{" not in tex
    assert tex_datos.extraer(tex) == datos

    cuerpo = _cuerpo(tex)
    # Ni el titulo (ni siquiera uno personalizado) ni las entradas salen...
    assert _titulo(idioma, "proyectos") not in cuerpo
    assert "Titulo que no debe salir" not in cuerpo
    assert MARCADOR_OCULTO[idioma] not in cuerpo
    assert cuerpo.count("\\cvsection{") == len(ORDEN) - 1
    # ...pero el bloque anclado a la seccion oculta mantiene su posicion:
    # despues de educacion y antes de proyectosu (orden por defecto).
    i_educacion = _indice(tex, _titulo(idioma, "educacion"))
    i_bloque = _indice(tex, "\\cvbloquebanda")
    i_proyectosu = _indice(tex, _titulo(idioma, "proyectosu"))
    assert i_educacion < i_bloque < i_proyectosu


@pytest.mark.parametrize("plantilla", PLANTILLAS)
@pytest.mark.parametrize("idioma", IDIOMAS)
def test_titulos_personalizados_se_escapan_y_hay_fallback_a_lang(
    plantilla, idioma, prefs_tmp
):
    datos = datos_completos(idioma)
    datos["plantilla"] = plantilla
    datos["titulos_seccion"] = {
        "trabajo": TITULO_CUSTOM,
        "perfil": "  Perfil personalizado  ",
    }
    tex = latex_gen.build_tex(datos, prefs.load())

    assert "{{" not in tex
    assert tex_datos.extraer(tex) == datos

    cuerpo = _cuerpo(tex)
    assert TITULO_CUSTOM_ESC in cuerpo
    assert "\\cvsection{Perfil personalizado}" in cuerpo
    # Las secciones sin titulo personalizado usan LANG.
    assert _titulo(idioma, "educacion") in cuerpo
    assert _titulo(idioma, "trabajo") not in cuerpo
    assert _titulo(idioma, "perfil") not in cuerpo
    assert cuerpo.count("\\cvsection{") == len(ORDEN)


# ---------------------------------------------------------------------------
# Saneado tolerante via main._migrar_datos (como al abrir un .cvjson)
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
    """Pasa por _migrar_datos y devuelve las 3 claves de secciones."""
    salida = main._migrar_datos(datos)
    return (
        salida["titulos_seccion"],
        salida["secciones_ocultas"],
        salida["orden_secciones"],
    )


def test_migrar_secciones_validas_se_normalizan():
    titulos, ocultas, orden = _secciones_saneadas({
        # La clave invalida se descarta; el valor se recorta.
        "titulos_seccion": {"perfil": "  Sobre mí  ", "trabajo": "Experiencia",
                            "marte": "x"},
        # Dedup conservando la primera aparicion y descarte de invalidas.
        "secciones_ocultas": ["trabajo", "trabajo", "marte", "idiomas"],
        # Dedup + faltantes anadidas al final en orden por defecto.
        "orden_secciones": ["idiomas", "marte", "idiomas", "trabajo"],
    })
    assert titulos == {"perfil": "Sobre mí", "trabajo": "Experiencia"}
    assert ocultas == ["trabajo", "idiomas"]
    assert orden == [
        "idiomas", "trabajo", "perfil", "educacion", "proyectos", "proyectosu",
        "pasantia", "habilidades", "referencias",
    ]


def test_migrar_secciones_ausentes_quedan_canonicas():
    assert _secciones_saneadas({}) == ({}, [], list(ORDEN))


@pytest.mark.parametrize("entrada", [[], ()])
def test_migrar_orden_vacio_conserva_el_centinela(entrada):
    # La lista vacia es el centinela de datos_vacios(): no se expande al
    # guardar/migrar; normalizar_orden_secciones la expande al renderizar.
    _, _, orden = _secciones_saneadas({"orden_secciones": entrada})
    assert orden == []


@pytest.mark.parametrize(
    "entrada", [None, "trabajo", {"trabajo": 1}, 7, _Explosivo()]
)
def test_migrar_orden_malformado_cae_al_orden_por_defecto(entrada):
    _, _, orden = _secciones_saneadas({"orden_secciones": entrada})
    assert orden == list(ORDEN)


def test_migrar_titulos_descarta_no_str_vacios_y_claves_invalidas():
    titulos, _, _ = _secciones_saneadas({"titulos_seccion": {
        "perfil": "  Perfil OK  ",
        "trabajo": 5,
        "educacion": None,
        "proyectos": "   ",
        "idiomas": b"bytes",
        "marte": "x",
    }})
    assert titulos == {"perfil": "Perfil OK"}


@pytest.mark.parametrize(
    "datos",
    [
        {"orden_secciones": [_Explosivo()]},
        {"orden_secciones": [[], {"x": 1}, (), _Explosivo()]},
        {"secciones_ocultas": [_Explosivo(), set(), {}]},
        {"secciones_ocultas": _Explosivo()},
        {"secciones_ocultas": [["trabajo"], "marte", 7]},
        {"titulos_seccion": {"perfil": _Explosivo()}},
        {"titulos_seccion": {"perfil": _StrStripExplosivo("Perfil")}},
        {"titulos_seccion": _Explosivo()},
        {"orden_secciones": _Explosivo()},
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
    "idiomas", "perfil", "educacion", "proyectos", "proyectosu", "pasantia",
    "trabajo", "habilidades", "referencias",
]


def test_cvjson_roundtrip_conserva_las_tres_claves(prefs_tmp, monkeypatch):
    datos = datos_completos("es")
    datos["plantilla"] = "moderno"
    datos["orden_secciones"] = list(ORDEN_CANONICO)
    datos["secciones_ocultas"] = ["proyectos", "idiomas"]
    datos["titulos_seccion"] = {"trabajo": TITULO_CUSTOM, "perfil": "Perfil propio"}
    ruta = prefs_tmp / "secciones.cvjson"

    api = main.Api(None)
    monkeypatch.setattr(api, "elegir_archivo", lambda *a, **k: str(ruta))

    salida = api.exportar_cv(datos)
    assert salida == {"ok": True, "ruta": str(ruta)}
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    assert contenido["version"] == 2
    for clave in ("titulos_seccion", "secciones_ocultas", "orden_secciones"):
        assert contenido["datos"][clave] == datos[clave]

    abierto = api.abrir_cv()
    assert abierto["ok"] is True
    for clave in ("titulos_seccion", "secciones_ocultas", "orden_secciones"):
        assert abierto["datos"][clave] == datos[clave]


def test_cvjson_abrir_sanea_las_tres_claves_escritas_a_mano(prefs_tmp, monkeypatch):
    datos = datos_completos("es")
    datos["orden_secciones"] = ["idiomas", "marte", "idiomas", "trabajo"]
    datos["secciones_ocultas"] = ["trabajo", "trabajo", "marte", 7, None]
    datos["titulos_seccion"] = {
        "trabajo": 5, "perfil": "  Perfil X  ", "marte": "x", "idiomas": "   ",
    }
    ruta = prefs_tmp / "sucio.cvjson"
    ruta.write_text(
        json.dumps({"version": 2, "datos": datos, "medios": {}}, ensure_ascii=False),
        encoding="utf-8",
    )

    api = main.Api(None)
    monkeypatch.setattr(api, "elegir_archivo", lambda *a, **k: str(ruta))

    abierto = api.abrir_cv()
    assert abierto["ok"] is True
    assert abierto["datos"]["titulos_seccion"] == {"perfil": "Perfil X"}
    assert abierto["datos"]["secciones_ocultas"] == ["trabajo"]
    assert abierto["datos"]["orden_secciones"] == [
        "idiomas", "trabajo", "perfil", "educacion", "proyectos", "proyectosu",
        "pasantia", "habilidades", "referencias",
    ]


# ---------------------------------------------------------------------------
# Compilaciones reales (mismo patron skipif que test_bloques.py)
# ---------------------------------------------------------------------------

def datos_compilacion(idioma):
    """CV completo con orden parcial, una seccion oculta y un titulo custom."""
    datos = datos_completos(idioma)
    datos["orden_secciones"] = ["trabajo", "perfil", "idiomas"]
    datos["secciones_ocultas"] = ["proyectos"]
    datos["titulos_seccion"] = {
        "trabajo": TITULO_CUSTOM if idioma == "es" else TITULO_CUSTOM_ZH,
    }
    datos["bloques"] = [dict(BLOQUE_ANCLA)]
    return datos


@pytest.mark.skipif(MOTOR_PDF is None, reason="Sin motor LaTeX (pdflatex) instalado")
@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_compila_pdf_secciones_es(plantilla, prefs_tmp):
    datos = datos_compilacion("es")
    datos["plantilla"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "{{" not in tex
    assert tex_datos.extraer(tex) == datos
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])


@pytest.mark.skipif(
    MOTOR_PDF is None or MOTOR_CJK is None,
    reason="Sin motores LaTeX (pdflatex/xelatex) para compilar texto CJK",
)
@pytest.mark.parametrize("plantilla", PLANTILLAS)
def test_compila_pdf_secciones_zh(plantilla, prefs_tmp):
    datos = datos_compilacion("zh")
    datos["plantilla"] = plantilla
    tex = latex_gen.build_tex(datos, prefs.load())
    assert "{{" not in tex
    assert tex_datos.extraer(tex) == datos
    resultado = latex_engine.compile(tex, None, None)
    assert resultado["ok"], resultado["errores"]
    assert resultado["pdf"] and os.path.isfile(resultado["pdf"])
