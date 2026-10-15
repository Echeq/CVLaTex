# -*- coding: utf-8 -*-
"""Esquema de datos canonico y migracion de .cvjson antiguos (Fase 1).

No requiere GUI, ni LaTeX, ni pywebview: solo importa ``latex_gen`` y
``migrate_data`` de ``main`` (importar main no abre ninguna ventana).
"""

import copy
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_gen  # noqa: E402
import tex_datos  # noqa: E402
from main import migrate_data  # noqa: E402

CLAVES_ESPERADAS = {
    "cv_language", "template", "name", "profession", "email", "phone",
    "address", "socials", "extra_fields", "photo", "photo_original",
    "photo_crop", "photo_width_cm", "photo_height_cm", "school_name",
    "school_logo", "school_logo_width_cm", "school_logo_height_cm", "summary",
    "work", "internships", "projects", "university_projects", "education",
    "skills", "languages", "references", "blocks", "columns",
    "section_titles", "hidden_sections", "section_order",
}

CLAVES_TEXTO = (
    "name", "profession", "email", "phone", "address",
    "school_name", "school_logo", "summary", "photo", "photo_original",
)

CLAVES_LISTA = (
    "socials", "extra_fields", "work", "internships", "projects",
    "university_projects", "education", "skills", "languages", "references",
    "blocks", "hidden_sections", "section_order",
)

CLAVES_MEDIDA = (
    "photo_width_cm", "photo_height_cm",
    "school_logo_width_cm", "school_logo_height_cm",
)


def test_datos_vacios_tiene_las_claves_exactas():
    d = latex_gen.empty_data()
    assert isinstance(d, dict)
    assert set(d) == CLAVES_ESPERADAS


def test_datos_vacios_tipos_y_valores_por_defecto():
    d = latex_gen.empty_data()
    assert d["cv_language"] == "zh"
    assert d["template"] == "classic"
    for clave in CLAVES_TEXTO:
        assert isinstance(d[clave], str), clave
    for clave in CLAVES_LISTA:
        assert isinstance(d[clave], list), clave
        assert d[clave] == [], clave
    for clave in CLAVES_MEDIDA:
        assert isinstance(d[clave], float), clave
    assert d["photo_crop"] is None
    assert d["section_titles"] == {}
    assert d["hidden_sections"] == []
    assert d["section_order"] == []
    columnas = d["columns"]
    assert isinstance(columnas, dict)
    assert set(columnas) == {
        "work", "internships", "projects", "university_projects", "education",
    }
    assert all(isinstance(v, int) and v == 1 for v in columnas.values())


def test_datos_vacios_devuelve_estructuras_nuevas():
    a = latex_gen.empty_data()
    b = latex_gen.empty_data()
    assert a == b
    a["name"] = "cambiado"
    a["socials"].append({"network": "github", "label": "", "value": "x"})
    a["extra_fields"].append({"label": "x", "value": "y"})
    a["blocks"].append({"type": "separator"})
    a["columns"]["work"] = 3
    a["section_titles"]["summary"] = "Sobre mí"
    a["hidden_sections"].append("languages")
    a["section_order"].append("work")
    assert b["name"] == ""
    assert b["socials"] == []
    assert b["extra_fields"] == []
    assert b["blocks"] == []
    assert b["columns"]["work"] == 1
    assert b["section_titles"] == {}
    assert b["hidden_sections"] == []
    assert b["section_order"] == []


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
    salida = migrate_data(datos)
    assert "experiencia" not in salida
    assert salida["work"] == [
        {"tipo": "Trabajo", "position": "Dev"},
        {"position": "Sin tipo"},
    ]
    assert salida["internships"] == [
        {"tipo": "Pasantía", "position": "Becario"},
        {"tipo": "pasantia", "position": "Practicas"},
    ]
    assert salida["skills"] == [
        {"category": "Lenguajes", "values": "Python"},
        {"category": "SQL", "values": "Alto"},
    ]


def test_migrar_no_pisa_work_o_internships_existentes():
    datos = {
        "experiencia": [{"tipo": "Trabajo", "puesto": "Antiguo"}],
        "trabajo": [{"puesto": "Actual"}],
        "habilidades": [],
    }
    salida = migrate_data(datos)
    assert salida["work"] == [{"position": "Actual"}]
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
    salida = migrate_data(datos)
    assert isinstance(salida, dict)


def test_migrar_no_dict_devuelve_la_entrada():
    assert migrate_data(None) is None
    assert migrate_data("texto") == "texto"
    assert migrate_data(7) == 7


# ---------------------------------------------------------------------------
# Socials: esquema, saneado y migracion de los campos fijos antiguos
# ---------------------------------------------------------------------------

def test_social_networks_contrato():
    assert latex_gen.SOCIAL_NETWORKS == (
        "github", "linkedin", "x", "instagram", "facebook", "youtube",
        "tiktok", "telegram", "wechat", "website", "other",
    )


def test_datos_vacios_no_tiene_los_campos_fijos_antiguos():
    d = latex_gen.empty_data()
    for clave in ("github", "linkedin", "website", "birth_date", "nationality"):
        assert clave not in d, clave


def test_migrar_campos_fijos_a_socials_y_extra_fields():
    copia = {
        "cv_language": "es",
        "name": "Ana",
        "github": "github.com/ana",
        "linkedin": "linkedin.com/in/ana",
        "website": "https://ana.dev",
        "birth_date": "12/05/1994",
        "nationality": "Española",
    }
    salida = migrate_data(dict(copia))
    assert salida["socials"] == [
        {"network": "github", "label": "", "value": "github.com/ana"},
        {"network": "linkedin", "label": "", "value": "linkedin.com/in/ana"},
        {"network": "website", "label": "", "value": "https://ana.dev"},
    ]
    assert salida["extra_fields"] == [
        {"label": "Nacimiento", "value": "12/05/1994"},
        {"label": "Nacionalidad", "value": "Española"},
    ]
    for clave in ("github", "linkedin", "website", "birth_date", "nationality"):
        assert clave not in salida, clave
    # El resto de datos no se toca.
    assert salida["name"] == "Ana"
    assert salida["cv_language"] == "es"


def test_migrar_campos_fijos_espanoles_heredados():
    salida = migrate_data({
        "nacimiento": "1990",
        "nacionalidad": "Chilena",
        "web": "web.example",
        "github": "github.com/heredero",
    })
    assert salida["socials"] == [
        {"network": "github", "label": "", "value": "github.com/heredero"},
        {"network": "website", "label": "", "value": "web.example"},
    ]
    assert salida["extra_fields"] == [
        {"label": "出生年月", "value": "1990"},
        {"label": "国籍", "value": "Chilena"},
    ]
    for clave in ("nacimiento", "nacionalidad", "web"):
        assert clave not in salida, clave


def test_migrar_etiqueta_de_nacimiento_segun_idioma():
    por_idioma = {
        "es": ("Nacimiento", "Nacionalidad"),
        "en": ("Date of birth", "Nationality"),
        "zh": ("出生年月", "国籍"),
    }
    for idioma, etiquetas in por_idioma.items():
        salida = migrate_data({
            "cv_language": idioma, "birth_date": "2000", "nationality": "X",
        })
        assert [x["label"] for x in salida["extra_fields"]] == list(etiquetas)
    # Idioma desconocido o ausente: zh por defecto, es si falta la tabla.
    assert migrate_data({"birth_date": "2000"})["extra_fields"] == [
        {"label": "出生年月", "value": "2000"},
    ]
    assert migrate_data({"cv_language": "ru", "birth_date": "2000"})["extra_fields"] == [
        {"label": "Nacimiento", "value": "2000"},
    ]


def test_migrar_socials_existentes_se_conservan_y_antiguos_se_anaden():
    salida = migrate_data({
        "socials": [{"network": "x", "label": "", "value": "x.com/ana"}],
        "github": "github.com/ana",
    })
    assert salida["socials"] == [
        {"network": "x", "label": "", "value": "x.com/ana"},
        {"network": "github", "label": "", "value": "github.com/ana"},
    ]


def test_sanear_socials_contrato():
    salida = migrate_data({"socials": [
        {"network": "github", "label": "", "value": "github.com/a"},
        {"network": "marte", "label": "Mi red", "value": "marte.example"},
        {"network": "other", "label": "Blog", "value": "blog.io"},
        {"network": "x", "value": "   "},
        {"network": "linkedin"},
        {"network": 7, "label": 9, "value": 0},
        "no-dict",
        3,
    ]})
    assert salida["socials"] == [
        {"network": "github", "label": "", "value": "github.com/a"},
        {"network": "other", "label": "Mi red", "value": "marte.example"},
        {"network": "other", "label": "Blog", "value": "blog.io"},
        {"network": "other", "label": "9", "value": "0"},
    ]


def test_migrar_socials_es_idempotente():
    datos = {
        "cv_language": "es",
        "github": "github.com/ana",
        "birth_date": "12/05/1994",
        "socials": [{"network": "other", "label": "Blog", "value": "blog.io"}],
    }
    primera = migrate_data(datos)
    copia = copy.deepcopy(primera)
    segunda = migrate_data(copia)
    assert segunda == primera
    assert not ({"github", "linkedin", "website", "birth_date", "nationality"} & set(segunda))


def test_migrar_socials_formas_raras_nunca_lanzan():
    class Explosivo:
        def __str__(self):
            raise RuntimeError("boom")

    casos = [
        {"socials": None},
        {"socials": "x"},
        {"socials": 7},
        {"socials": {"network": "github"}},
        {"socials": [None, 3, "s", [], (), {}]},
        {"socials": [{"network": Explosivo(), "value": "v"}]},
        {"socials": [{"network": "github", "value": Explosivo()}]},
        {"socials": [{"network": "github", "label": Explosivo(), "value": "v"}]},
        {"github": Explosivo(), "linkedin": Explosivo(), "website": Explosivo()},
        {"birth_date": Explosivo(), "nationality": Explosivo()},
    ]
    for datos in casos:
        salida = migrate_data(datos)
        assert isinstance(salida, dict)
        assert isinstance(salida["socials"], list)


def test_build_tex_cabecera_socials():
    d = latex_gen.empty_data()
    d["cv_language"] = "es"
    d["name"] = "Ana"
    d["socials"] = [
        {"network": "github", "label": "Ignorado", "value": "github.com/ana"},
        {"network": "linkedin", "label": "", "value": "linkedin.com/in/a"},
        {"network": "x", "label": "", "value": "x.com/ana"},
        {"network": "instagram", "label": "", "value": "@ana"},
        {"network": "facebook", "label": "", "value": "fb.com/ana"},
        {"network": "youtube", "label": "", "value": "yt.com/ana"},
        {"network": "tiktok", "label": "", "value": "tiktok.com/@a"},
        {"network": "telegram", "label": "", "value": "t.me/ana"},
        {"network": "wechat", "label": "", "value": "ana_wx"},
        {"network": "website", "label": "", "value": "ana.dev"},
        {"network": "other", "label": "Mastodon", "value": "mastodon/@ana"},
        {"network": "other", "label": "", "value": "solo.dev"},
        {"network": "other", "label": "   ", "value": "blanco.dev"},
        {"network": "github", "label": "x", "value": "   "},
    ]
    d["extra_fields"] = [{"label": "Nacimiento", "value": "12/05/1994"}]
    tex = latex_gen.build_tex(d, PREFS_PRUEBA)
    for aguja in (
        "\\textbf{GitHub:} \\texttt{github.com/ana}",
        "\\textbf{LinkedIn:} \\texttt{linkedin.com/in/a}",
        "\\textbf{X:} \\texttt{x.com/ana}",
        "\\textbf{Instagram:} \\texttt{@ana}",
        "\\textbf{Facebook:} \\texttt{fb.com/ana}",
        "\\textbf{YouTube:} \\texttt{yt.com/ana}",
        "\\textbf{TikTok:} \\texttt{tiktok.com/@a}",
        "\\textbf{Telegram:} \\texttt{t.me/ana}",
        "\\textbf{WeChat:} \\texttt{ana\\_wx}",
        "\\textbf{Web:} \\texttt{ana.dev}",
        "\\textbf{Mastodon:} \\texttt{mastodon/@ana}",
        "\\textbf{Enlace:} \\texttt{solo.dev}",
        "\\textbf{Enlace:} \\texttt{blanco.dev}",
        "\\textbf{Nacimiento:} 12/05/1994",
    ):
        assert aguja in tex, aguja
    # El label solo se usa con "other"; las entradas sin valor se omiten.
    assert "Ignorado" not in tex
    assert "\\texttt{   }" not in tex
    # Los socials se renderizan antes que los datos adicionales.
    assert tex.index("\\textbf{GitHub:}") < tex.index("\\textbf{Nacimiento:}")


def test_build_tex_socials_idioma_del_documento():
    d = latex_gen.empty_data()
    d["cv_language"] = "zh"
    d["socials"] = [
        {"network": "website", "label": "", "value": "ana.cn"},
        {"network": "other", "label": "", "value": "otro.cn"},
    ]
    tex = latex_gen.build_tex(d, PREFS_PRUEBA)
    assert "\\textbf{网站:} \\texttt{ana.cn}" in tex
    assert "\\textbf{链接:} \\texttt{otro.cn}" in tex

    d["cv_language"] = "en"
    tex = latex_gen.build_tex(d, PREFS_PRUEBA)
    assert "\\textbf{Website:} \\texttt{ana.cn}" in tex
    assert "\\textbf{Link:} \\texttt{otro.cn}" in tex


# ---------------------------------------------------------------------------
# Bloques libres: saneado via migrate_data (main.sanitize_blocks)
# ---------------------------------------------------------------------------

def _bloques_saneados(bloques):
    """Pasa por migrate_data (como al abrir un .cvjson) y devuelve los bloques."""
    return migrate_data({"blocks": bloques})["blocks"]


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
    assert _bloques_saneados([{"type": "other"}]) == []
    assert _bloques_saneados([{"tipo": "otro"}, None, {"sin_tipo": 1}]) == []
    assert migrate_data({})["blocks"] == []


def test_bloques_separador_estilo_invalido_o_ausente_cae_a_line():
    salida = _bloques_saneados([
        {"tipo": "separador", "estilo": "zzz"},
        {"tipo": "separador"},
        {"tipo": "separador", "estilo": None},
        {"tipo": "separador", "estilo": 7},
    ])
    assert [b["style"] for b in salida] == ["line"] * 4
    assert all(b["type"] == "separator" for b in salida)


def test_bloques_seccion_titulo_y_contenido_se_convierten_a_texto():
    salida = _bloques_saneados([
        {"tipo": "seccion", "titulo": 5, "contenido": None},
        {"tipo": "seccion", "titulo": None, "contenido": 0},
    ])
    assert salida[0]["title"] == "5"
    assert salida[0]["content"] == ""
    assert salida[1]["title"] == ""
    assert salida[1]["content"] == "0"


def test_bloques_posicion_invalida_o_ausente_cae_al_final():
    salida = _bloques_saneados([
        {"tipo": "separador", "posicion": "marte"},
        {"tipo": "separador", "posicion": 3},
        {"tipo": "separador"},
        {"tipo": "separador", "posicion": "inicio"},
    ])
    assert [b["position"] for b in salida] == ["end", "end", "end", "start"]


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
    assert set(salida[0]) == {"id", "type", "style", "position"}
    assert set(salida[1]) == {"id", "type", "title", "content", "position"}


def test_bloques_listado_se_sanean():
    salida = _bloques_saneados([
        {"id": "a", "tipo": "listado", "modo": "zzz", "columnas": 9,
         "titulo": 5, "entradas": [{"titulo": "A", "detalle": "B", "basura": 1},
                                   None, "x", 3]},
        {"id": "b", "tipo": "listado", "modo": "periodo", "columnas": "2",
         "entradas": [{"periodo": "2020", "descripcion": "D", "otra": 2}]},
    ])
    assert set(salida[0]) == {
        "id", "type", "mode", "title", "columns", "entries", "position",
    }
    assert salida[0]["mode"] == "columns"
    assert salida[0]["columns"] == 3
    assert salida[0]["title"] == "5"
    assert salida[0]["position"] == "end"
    assert salida[0]["entries"] == [{"title": "A", "detail": "B"}]
    assert salida[1]["mode"] == "period"
    assert salida[1]["columns"] == 2
    assert salida[1]["entries"] == [{"period": "2020", "description": "D"}]


def test_bloques_listado_formas_raras_nunca_lanzan():
    class Explosivo:
        def __str__(self):
            raise RuntimeError("boom")

    casos = [
        {"blocks": [{"type": "list"}]},
        {"blocks": [{"type": "list", "mode": Explosivo()}]},
        {"blocks": [{"type": "list", "columns": Explosivo(),
                     "entries": Explosivo()}]},
        {"blocks": [{"type": "list", "title": Explosivo(),
                     "entries": [None, 3, "x", {"title": Explosivo()}]}]},
    ]
    for datos in casos:
        salida = migrate_data(datos)
        assert isinstance(salida["blocks"], list)


def test_bloques_validos_se_conservan_intactos():
    validos = [
        {"id": "s1", "type": "separator", "style": "space", "position": "start"},
        {"id": "s2", "type": "section", "title": "Mi sección",
         "content": "Uno\nDos", "position": "education"},
    ]
    assert _bloques_saneados(validos) == validos


def test_bloques_formas_raras_nunca_lanzan():
    class Explosivo:
        def __str__(self):
            raise RuntimeError("boom")

    casos = [
        {"blocks": None},
        {"blocks": "x"},
        {"blocks": 7},
        {"blocks": {"type": "section"}},
        {"blocks": [None, 3, "s", [], (), {}]},
        {"blocks": [{"type": "other"}]},
        {"blocks": [{"type": "section", "title": Explosivo()}]},
        {"blocks": [{"type": "separator", "style": Explosivo()}]},
        {"blocks": [{"type": "separator", "position": Explosivo()}]},
        {"blocks": [{"type": "section", "content": {"a": 1}}]},
        {"blocks": ["texto", {"type": object()}]},
    ]
    for datos in casos:
        salida = migrate_data(datos)
        assert isinstance(salida, dict)
        assert isinstance(salida["blocks"], list)


# ---------------------------------------------------------------------------
# Orden, titulos y secciones ocultas
# ---------------------------------------------------------------------------

PREFS_PRUEBA = {
    "paper": "a4",
    "margins": {"top": 2.0, "bottom": 2.0, "left": 2.0, "right": 2.0},
    "font_size": 11,
}


class _Explosivo:
    def __str__(self):
        raise RuntimeError("boom")

    def __eq__(self, other):
        raise RuntimeError("boom")

    __hash__ = None


def _sin_bloque_datos(tex):
    inicio = tex.index(tex_datos.MARK_START)
    fin = tex.index(tex_datos.MARK_END, inicio)
    fin = tex.index("\n", fin) + 1
    return tex[:inicio] + tex[fin:]


def test_orden_secciones_defecto_exacto():
    assert latex_gen.DEFAULT_SECTION_ORDER == (
        "summary", "education", "projects", "university_projects", "internships",
        "work", "skills", "languages", "references",
    )


def test_normalizar_orden_secciones_contrato():
    defecto = list(latex_gen.DEFAULT_SECTION_ORDER)
    assert latex_gen.normalize_section_order({}) == defecto
    assert latex_gen.normalize_section_order({"section_order": []}) == defecto
    assert latex_gen.normalize_section_order(
        {"section_order": ["work", "summary"]}
    ) == [
        "work", "summary", "education", "projects", "university_projects",
        "internships", "skills", "languages", "references",
    ]
    # Dedup conservando la primera aparicion y claves invalidas descartadas.
    assert latex_gen.normalize_section_order(
        {"section_order": ["work", "marte", "work", "summary", None, 7]}
    ) == [
        "work", "summary", "education", "projects", "university_projects",
        "internships", "skills", "languages", "references",
    ]


@pytest.mark.parametrize(
    "data",
    [
        None,
        "x",
        7,
        [],
        {"section_order": None},
        {"section_order": "work"},
        {"section_order": {"work": 1}},
        {"section_order": [b"bytes"]},
        {"section_order": [_Explosivo()]},
    ],
)
def test_normalizar_orden_secciones_no_lanza(data):
    resultado = latex_gen.normalize_section_order(data)
    assert list(resultado) == list(latex_gen.DEFAULT_SECTION_ORDER)


def test_titulo_personalizado_contrato():
    assert latex_gen.custom_section_title({}, "summary") is None
    assert latex_gen.custom_section_title({"section_titles": {}}, "summary") is None
    assert latex_gen.custom_section_title(
        {"section_titles": {"summary": "  Sobre mí  "}}, "summary"
    ) == "Sobre mí"
    assert latex_gen.custom_section_title(
        {"section_titles": {"summary": 5}}, "summary"
    ) == "5"
    assert latex_gen.custom_section_title(
        {"section_titles": {"summary": "   "}}, "summary"
    ) is None
    assert latex_gen.custom_section_title(
        {"section_titles": {"summary": None}}, "summary"
    ) is None


@pytest.mark.parametrize(
    "data",
    [
        None,
        "x",
        7,
        [],
        {"section_titles": None},
        {"section_titles": "x"},
        {"section_titles": 7},
        {"section_titles": {"summary": _Explosivo()}},
    ],
)
def test_titulo_personalizado_no_lanza(data):
    assert latex_gen.custom_section_title(data, "summary") is None


def test_seccion_oculta_contrato():
    assert latex_gen.is_section_hidden({}, "summary") is False
    assert latex_gen.is_section_hidden(
        {"hidden_sections": ["summary"]}, "summary"
    ) is True
    assert latex_gen.is_section_hidden(
        {"hidden_sections": ["languages"]}, "summary"
    ) is False
    assert latex_gen.is_section_hidden(
        {"hidden_sections": "summary"}, "summary"
    ) is False


@pytest.mark.parametrize(
    "data",
    [
        None,
        "x",
        7,
        [],
        {"hidden_sections": None},
        {"hidden_sections": 7},
        {"hidden_sections": {"summary": True}},
        {"hidden_sections": [_Explosivo()]},
    ],
)
def test_seccion_oculta_no_lanza(data):
    resultado = latex_gen.is_section_hidden(data, "summary")
    assert isinstance(resultado, bool)
    assert resultado is False


def test_build_tex_orden_titulos_y_ocultas():
    d = latex_gen.empty_data()
    d["cv_language"] = "es"
    d["summary"] = "Perfil visible."
    d["work"] = [{"position": "Desarrolladora", "company": "Acme"}]
    d["languages"] = [{"language": "Español", "level": "Nativo"}]
    d["section_order"] = ["work", "summary", "languages"]
    d["hidden_sections"] = ["languages"]
    d["section_titles"] = {"work": "I+D 100% & ~"}
    d["blocks"] = [
        {"id": "b1", "type": "separator", "style": "line", "position": "languages"},
        {"id": "b2", "type": "separator", "style": "band", "position": "references"},
    ]
    tex = latex_gen.build_tex(d, PREFS_PRUEBA)
    cuerpo = tex[tex.index("\\begin{document}"):]
    # Titulo personalizado escapado y secciones en el orden pedido.
    assert "\\cvsection{I+D 100\\% \\& \\textasciitilde{}}" in cuerpo
    idx_trabajo = cuerpo.index("\\cvsection{I+D")
    idx_perfil = cuerpo.index("\\cvsection{Perfil}")
    assert idx_trabajo < idx_perfil
    # La seccion oculta no emite titulo ni entradas...
    assert "\\cvsection{Idiomas}" not in cuerpo
    assert "Español" not in cuerpo
    # ...pero su bloque anclado sigue renderizandose en esa posicion.
    idx_linea = cuerpo.index("\\cvblockline")
    assert idx_perfil < idx_linea
    assert "\\cvblockband" in cuerpo


@pytest.mark.parametrize(
    "basura",
    [
        {"section_order": "work"},
        {"section_order": [None, 7, {"x": 1}, "summary", "summary"]},
        {"section_titles": ["no", "dict"]},
        {"section_titles": {"summary": ""}},
        {"hidden_sections": {"summary": True}},
        {"hidden_sections": None},
        {"section_order": None, "section_titles": None, "hidden_sections": None},
    ],
)
def test_build_tex_tolera_basura_en_las_tres_claves(basura):
    d = latex_gen.empty_data()
    d.update(basura)
    tex = latex_gen.build_tex(d, PREFS_PRUEBA)
    assert "{{" not in tex
    assert tex_datos.extract(tex) == d


@pytest.mark.parametrize("plantilla", latex_gen.TEMPLATES)
def test_build_tex_defaults_no_cambian_la_salida(plantilla):
    d = latex_gen.empty_data()
    d["template"] = plantilla
    d["cv_language"] = "es"
    d["summary"] = "Perfil breve."
    d["work"] = [{"position": "Dev", "company": "Acme"}]
    d["skills"] = [{"category": "Lenguajes", "values": "Python"}]
    d["languages"] = [{"language": "Inglés", "level": "B2"}]
    d["references"] = [{"name": "Ana", "contact": "ana@example.com"}]
    d["blocks"] = [
        {"id": "b", "type": "separator", "style": "band", "position": "work"},
    ]
    sin_claves = {
        k: v for k, v in d.items()
        if k not in ("section_titles", "hidden_sections", "section_order")
    }
    tex_sin = _sin_bloque_datos(latex_gen.build_tex(sin_claves, PREFS_PRUEBA))
    tex_con = _sin_bloque_datos(latex_gen.build_tex(d, PREFS_PRUEBA))
    assert tex_con == tex_sin


def test_build_tex_chinese_respeta_titulos_y_ocultas():
    d = latex_gen.empty_data()
    d["template"] = "chinese"
    d["work"] = [{
        "position": "工程师", "company": "公司", "start": "2020", "end": "2024",
    }]
    d["education"] = [{"degree_type": "bachelor", "degree": "计算机", "institution": "大学"}]
    d["section_order"] = ["work"]
    d["hidden_sections"] = ["education"]
    d["section_titles"] = {"work": "Trabajo & I+D"}
    tex = latex_gen.build_tex(d, PREFS_PRUEBA)
    cuerpo = tex[tex.index("\\begin{document}"):]
    assert "\\cvsection{Trabajo \\& I+D}" in cuerpo
    assert "计算机" not in cuerpo
    assert "\\cvcnline" in cuerpo
    assert tex_datos.extract(tex) == d
