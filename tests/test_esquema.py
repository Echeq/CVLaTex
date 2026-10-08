# -*- coding: utf-8 -*-
"""Esquema de datos canonico y migracion de .cvjson antiguos (Fase 1).

No requiere GUI, ni LaTeX, ni pywebview: solo importa ``latex_gen`` y
``_migrar_datos`` de ``main`` (importar main no abre ninguna ventana).
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_gen  # noqa: E402
from main import _migrar_datos  # noqa: E402

CLAVES_ESPERADAS = {
    "idioma_cv", "plantilla", "nombre", "profesion", "email", "telefono",
    "direccion", "web", "nacimiento", "nacionalidad", "github", "linkedin",
    "datos_extra", "foto", "foto_original", "foto_recorte", "foto_ancho_cm",
    "foto_alto_cm", "institucion_egresado", "logo_egresado",
    "logo_egresado_ancho_cm", "logo_egresado_alto_cm", "perfil",
    "trabajo", "pasantia", "proyectos", "proyectosu", "educacion",
    "habilidades", "idiomas", "referencias", "bloques", "columnas",
}

CLAVES_TEXTO = (
    "nombre", "profesion", "email", "telefono", "direccion", "web",
    "nacimiento", "nacionalidad", "github", "linkedin",
    "institucion_egresado", "logo_egresado", "perfil", "foto", "foto_original",
)

CLAVES_LISTA = (
    "datos_extra", "trabajo", "pasantia", "proyectos", "proyectosu",
    "educacion", "habilidades", "idiomas", "referencias", "bloques",
)

CLAVES_MEDIDA = (
    "foto_ancho_cm", "foto_alto_cm",
    "logo_egresado_ancho_cm", "logo_egresado_alto_cm",
)


def test_datos_vacios_tiene_las_claves_exactas():
    d = latex_gen.datos_vacios()
    assert isinstance(d, dict)
    assert set(d) == CLAVES_ESPERADAS


def test_datos_vacios_tipos_y_valores_por_defecto():
    d = latex_gen.datos_vacios()
    assert d["idioma_cv"] == "zh"
    assert d["plantilla"] == "clasico"
    for clave in CLAVES_TEXTO:
        assert isinstance(d[clave], str), clave
    for clave in CLAVES_LISTA:
        assert isinstance(d[clave], list), clave
        assert d[clave] == [], clave
    for clave in CLAVES_MEDIDA:
        assert isinstance(d[clave], float), clave
    assert d["foto_recorte"] is None
    columnas = d["columnas"]
    assert isinstance(columnas, dict)
    assert set(columnas) == {"trabajo", "pasantia", "proyectos", "proyectosu", "educacion"}
    assert all(isinstance(v, int) and v == 1 for v in columnas.values())


def test_datos_vacios_devuelve_estructuras_nuevas():
    a = latex_gen.datos_vacios()
    b = latex_gen.datos_vacios()
    assert a == b
    a["nombre"] = "cambiado"
    a["datos_extra"].append({"etiqueta": "x", "valor": "y"})
    a["bloques"].append({"tipo": "separador"})
    a["columnas"]["trabajo"] = 3
    assert b["nombre"] == ""
    assert b["datos_extra"] == []
    assert b["bloques"] == []
    assert b["columnas"]["trabajo"] == 1


def test_migrar_experiencia_y_habilidades_antiguas():
    datos = {
        "experiencia": [
            {"tipo": "Trabajo", "puesto": "Dev"},
            {"tipo": "Pasantía", "puesto": "Becario"},
            {"tipo": "pasantia", "puesto": "Practicas"},
            {"puesto": "Sin tipo"},
        ],
        "habilidades": [
            {"categoria": "Lenguajes", "valores": "Python"},
            {"nombre": "SQL", "nivel": "Alto"},
        ],
    }
    salida = _migrar_datos(datos)
    assert "experiencia" not in salida
    assert salida["trabajo"] == [
        {"tipo": "Trabajo", "puesto": "Dev"},
        {"puesto": "Sin tipo"},
    ]
    assert salida["pasantia"] == [
        {"tipo": "Pasantía", "puesto": "Becario"},
        {"tipo": "pasantia", "puesto": "Practicas"},
    ]
    assert salida["habilidades"] == [
        {"categoria": "Lenguajes", "valores": "Python"},
        {"categoria": "SQL", "valores": "Alto"},
    ]


def test_migrar_no_pisa_trabajo_o_pasantia_existentes():
    datos = {
        "experiencia": [{"tipo": "Trabajo", "puesto": "Antiguo"}],
        "trabajo": [{"puesto": "Actual"}],
        "habilidades": [],
    }
    salida = _migrar_datos(datos)
    assert salida["trabajo"] == [{"puesto": "Actual"}]
    assert salida["experiencia"] == [{"tipo": "Trabajo", "puesto": "Antiguo"}]


@pytest.mark.parametrize(
    "datos",
    [
        {},
        {"experiencia": "no-es-lista", "habilidades": {"a": 1}},
        {"experiencia": [], "habilidades": []},
        {"experiencia": [None, "texto", 3, {"tipo": None}], "habilidades": [None, "x", 3, {}]},
        {"experiencia": [{"tipo": 7, "puesto": None}], "habilidades": [{"sin_nombre": 1}]},
    ],
)
def test_migrar_formas_mal_formadas_no_lanza(datos):
    salida = _migrar_datos(datos)
    assert isinstance(salida, dict)


def test_migrar_no_dict_devuelve_la_entrada():
    assert _migrar_datos(None) is None
    assert _migrar_datos("texto") == "texto"
    assert _migrar_datos(7) == 7


# ---------------------------------------------------------------------------
# Bloques libres: saneado via _migrar_datos (main._sanear_bloques)
# ---------------------------------------------------------------------------

def _bloques_saneados(bloques):
    """Pasa por _migrar_datos (como al abrir un .cvjson) y devuelve los bloques."""
    return _migrar_datos({"bloques": bloques})["bloques"]


@pytest.mark.parametrize(
    "entrada",
    [
        None,
        "x",
        3,
        {"a": 1},
        [],
        [None, 3, "s"],
        [{}],
        [[]],
        [{"tipo": "otro"}],
        [{"tipo": None}],
    ],
)
def test_bloques_invalidos_o_inexistentes_no_lanzan(entrada):
    salida = _bloques_saneados(entrada)
    assert isinstance(salida, list)
    assert salida == []


def test_bloques_no_lista_y_sin_tipo_se_descartan():
    assert _bloques_saneados("x") == []
    assert _bloques_saneados([None, 3, "s"]) == []
    assert _bloques_saneados([{"tipo": "otro"}]) == []
    assert _bloques_saneados([{"tipo": "otro"}, None, {"sin_tipo": 1}]) == []
    assert _migrar_datos({})["bloques"] == []


def test_bloques_separador_estilo_invalido_o_ausente_cae_a_linea():
    salida = _bloques_saneados([
        {"tipo": "separador", "estilo": "zzz"},
        {"tipo": "separador"},
        {"tipo": "separador", "estilo": None},
        {"tipo": "separador", "estilo": 7},
    ])
    assert [b["estilo"] for b in salida] == ["linea"] * 4
    assert all(b["tipo"] == "separador" for b in salida)


def test_bloques_seccion_titulo_y_contenido_se_convierten_a_texto():
    salida = _bloques_saneados([
        {"tipo": "seccion", "titulo": 5, "contenido": None},
        {"tipo": "seccion", "titulo": None, "contenido": 0},
    ])
    assert salida[0]["titulo"] == "5"
    assert salida[0]["contenido"] == ""
    assert salida[1]["titulo"] == ""
    assert salida[1]["contenido"] == "0"


def test_bloques_posicion_invalida_o_ausente_cae_a_final():
    salida = _bloques_saneados([
        {"tipo": "separador", "posicion": "marte"},
        {"tipo": "separador", "posicion": 3},
        {"tipo": "separador"},
        {"tipo": "separador", "posicion": "inicio"},
    ])
    assert [b["posicion"] for b in salida] == ["final", "final", "final", "inicio"]


def test_bloques_id_ausente_se_genera_y_duplicados_se_regeneran():
    salida = _bloques_saneados([
        {"tipo": "separador"},
        {"id": "repe", "tipo": "separador"},
        {"id": "repe", "tipo": "separador"},
        {"id": 17, "tipo": "separador"},
    ])
    ids = [b["id"] for b in salida]
    assert len(ids) == 4
    assert len(set(ids)) == 4
    assert ids[1] == "repe"
    for i, ident in enumerate(ids):
        assert isinstance(ident, str) and ident
        if i != 1:
            assert re.fullmatch(r"[0-9a-f]{32}", ident), ident


def test_bloques_solo_conservan_claves_canonicas():
    salida = _bloques_saneados([
        {"id": "a", "tipo": "separador", "estilo": "banda", "posicion": "inicio",
         "basura": 1, "contenido": "x", "titulo": "y"},
        {"id": "b", "tipo": "seccion", "titulo": "T", "contenido": "C",
         "posicion": "final", "estilo": "linea", "extra": {}},
    ])
    assert set(salida[0]) == {"id", "tipo", "estilo", "posicion"}
    assert set(salida[1]) == {"id", "tipo", "titulo", "contenido", "posicion"}


def test_bloques_validos_se_conservan_intactos():
    validos = [
        {"id": "s1", "tipo": "separador", "estilo": "espacio", "posicion": "inicio"},
        {"id": "s2", "tipo": "seccion", "titulo": "Mi sección",
         "contenido": "Uno\nDos", "posicion": "educacion"},
    ]
    assert _bloques_saneados(validos) == validos


def test_bloques_formas_raras_nunca_lanzan():
    class Explosivo:
        def __str__(self):
            raise RuntimeError("boom")

    casos = [
        {"bloques": None},
        {"bloques": "x"},
        {"bloques": 7},
        {"bloques": {"tipo": "seccion"}},
        {"bloques": [None, 3, "s", [], (), {}]},
        {"bloques": [{"tipo": "otro"}]},
        {"bloques": [{"tipo": "seccion", "titulo": Explosivo()}]},
        {"bloques": [{"tipo": "separador", "estilo": Explosivo()}]},
        {"bloques": [{"tipo": "separador", "posicion": Explosivo()}]},
        {"bloques": [{"tipo": "seccion", "contenido": {"a": 1}}]},
        {"bloques": ["texto", {"tipo": object()}]},
    ]
    for datos in casos:
        salida = _migrar_datos(datos)
        assert isinstance(salida, dict)
        assert isinstance(salida["bloques"], list)
