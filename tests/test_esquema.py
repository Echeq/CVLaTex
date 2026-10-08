# -*- coding: utf-8 -*-
"""Esquema de datos canonico y migracion de .cvjson antiguos (Fase 1).

No requiere GUI, ni LaTeX, ni pywebview: solo importa ``latex_gen`` y
``_migrar_datos`` de ``main`` (importar main no abre ninguna ventana).
"""

import os
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
    "habilidades", "idiomas", "referencias", "columnas",
}

CLAVES_TEXTO = (
    "nombre", "profesion", "email", "telefono", "direccion", "web",
    "nacimiento", "nacionalidad", "github", "linkedin",
    "institucion_egresado", "logo_egresado", "perfil", "foto", "foto_original",
)

CLAVES_LISTA = (
    "datos_extra", "trabajo", "pasantia", "proyectos", "proyectosu",
    "educacion", "habilidades", "idiomas", "referencias",
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
    a["columnas"]["trabajo"] = 3
    assert b["nombre"] == ""
    assert b["datos_extra"] == []
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
