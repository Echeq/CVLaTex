# -*- coding: utf-8 -*-
"""Exportar/abrir .cvjson v2: incrustado y materializado de medios.

Simula una cache movida borrando los ficheros originales antes de importar:
abrir_cv debe escribir los medios en prefs.CACHE_DIR y reescribir las rutas.
"""

import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import latex_gen  # noqa: E402
import main  # noqa: E402
import prefs  # noqa: E402


@pytest.fixture()
def prefs_tmp(tmp_path, monkeypatch):
    app = tmp_path / "app"
    monkeypatch.setattr(prefs, "APP_DIR", str(app))
    monkeypatch.setattr(prefs, "CACHE_DIR", str(app / "cache"))
    monkeypatch.setattr(prefs, "BUILD_DIR", str(app / "cache" / "build"))
    monkeypatch.setattr(prefs, "PREFS_FILE", str(app / "prefs.json"))
    monkeypatch.setattr(prefs, "_CACHE", None)
    return tmp_path


def _api_con_ruta(monkeypatch, ruta):
    api = main.Api(None)
    monkeypatch.setattr(api, "elegir_archivo", lambda *a, **k: str(ruta))
    return api


def test_exportar_cv_v2_incrusta_medios_y_abrir_cv_los_materializa(prefs_tmp, monkeypatch):
    tmp = prefs_tmp
    origenes = tmp / "origenes"
    origenes.mkdir()
    foto = origenes / "foto.png"
    foto.write_bytes(b"contenido-foto-original")
    recorte = origenes / "recorte.png"
    recorte.write_bytes(b"contenido-recorte-original")
    logo = origenes / "logo.png"
    logo.write_bytes(b"contenido-logo-original")
    gif = origenes / "no-permitido.gif"
    gif.write_bytes(b"no-debe-incrustarse")
    inexistente = origenes / "borrado.png"

    rectangulo = {"x": 0.1, "y": 0.2, "w": 0.5, "h": 0.6}
    datos = latex_gen.datos_vacios()
    datos["idioma_cv"] = "es"
    datos["nombre"] = "Ana"
    # Estado tras aplicar un recorte: "foto" es la imagen ya recortada,
    # "foto_original" la subida y "foto_recorte" el rectangulo normalizado.
    datos["foto"] = str(recorte)
    datos["foto_original"] = str(foto)
    datos["foto_recorte"] = rectangulo
    datos["logo_egresado"] = str(logo)
    datos["trabajo"] = [
        {"puesto": "Dev", "empresa": "Acme", "logo": str(logo)},
        {"puesto": "Gif", "empresa": "Otra", "logo": str(gif)},
        {"puesto": "Inexistente", "empresa": "Otra", "logo": str(inexistente)},
    ]

    salida = tmp / "mi_cv.cvjson"
    api = _api_con_ruta(monkeypatch, salida)
    resultado = api.exportar_cv(datos)
    assert resultado == {"ok": True, "ruta": str(salida)}

    contenido = json.loads(salida.read_text(encoding="utf-8"))
    assert contenido["version"] == 2
    assert contenido["datos"]["foto"] == str(recorte)
    assert contenido["datos"]["foto_recorte"] == rectangulo

    esperados = {
        str(foto): b"contenido-foto-original",
        str(recorte): b"contenido-recorte-original",
        str(logo): b"contenido-logo-original",
    }
    medios = contenido["medios"]
    assert set(medios) == set(esperados)
    for ruta_original, info in medios.items():
        assert info["nombre"] == os.path.basename(ruta_original)
        assert base64.b64decode(info["b64"]) == esperados[ruta_original]

    # Cache movida: los ficheros originales ya no existen.
    for ruta in (foto, recorte, logo):
        ruta.unlink()
    assert not foto.exists() and not recorte.exists() and not logo.exists()

    resultado = _api_con_ruta(monkeypatch, salida).abrir_cv()
    assert resultado["ok"] is True
    datos_nuevos = resultado["datos"]

    # Un fichero cv_* por cada medio distinto incrustado: foto (recorte),
    # foto_original y logo_egresado (que comparte ruta con trabajo[0].logo).
    ficheros = [n for n in os.listdir(prefs.CACHE_DIR) if n.startswith("cv_")]
    assert len(ficheros) == 3
    contenidos = set()
    for nombre in ficheros:
        with open(os.path.join(prefs.CACHE_DIR, nombre), "rb") as f:
            contenidos.add(f.read())
    assert contenidos == {
        b"contenido-foto-original",
        b"contenido-recorte-original",
        b"contenido-logo-original",
    }

    for clave in ("foto", "foto_original", "logo_egresado"):
        ruta_nueva = datos_nuevos[clave]
        assert ruta_nueva != datos[clave]
        assert os.path.isfile(ruta_nueva), clave
        assert os.path.basename(ruta_nueva).startswith("cv_")
        assert os.path.realpath(os.path.dirname(ruta_nueva)) == os.path.realpath(prefs.CACHE_DIR)

    with open(datos_nuevos["foto"], "rb") as f:
        assert f.read() == b"contenido-recorte-original"
    with open(datos_nuevos["foto_original"], "rb") as f:
        assert f.read() == b"contenido-foto-original"
    with open(datos_nuevos["logo_egresado"], "rb") as f:
        assert f.read() == b"contenido-logo-original"

    assert datos_nuevos["trabajo"][0]["logo"] == datos_nuevos["logo_egresado"]
    # El rectangulo de recorte (dict) sobrevive a la importacion v2: el
    # relleno con datos_vacios() solo sustituye claves ausentes cuando el
    # valor por defecto es None, sin comprobar el tipo contra NoneType.
    assert datos_nuevos["foto_recorte"] == rectangulo
    # El gif no se incrusta y el logo inexistente no se reescribe.
    assert datos_nuevos["trabajo"][1]["logo"] == str(gif)
    assert datos_nuevos["trabajo"][2]["logo"] == str(inexistente)


def test_abrir_cv_v1_conserva_rutas_y_relena_vacios(prefs_tmp, monkeypatch):
    tmp = prefs_tmp
    ruta_foto = tmp / "antigua.png"
    ruta_foto.write_bytes(b"foto-v1")

    cvjson = tmp / "v1.cvjson"
    cvjson.write_text(
        json.dumps(
            {
                "version": 1,
                "datos": {
                    "nombre": "CV antiguo",
                    "foto": str(ruta_foto),
                    "experiencia": [{"tipo": "Trabajo", "puesto": "Dev"}],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    api = _api_con_ruta(monkeypatch, cvjson)
    resultado = api.abrir_cv()
    assert resultado["ok"] is True
    datos = resultado["datos"]

    # v1 no materializa: la ruta original se conserva aunque el fichero exista.
    assert datos["foto"] == str(ruta_foto)
    assert os.path.isfile(datos["foto"])
    # Migracion y relleno con el esquema vacio.
    assert datos["trabajo"] == [{"tipo": "Trabajo", "puesto": "Dev"}]
    assert datos["pasantia"] == []
    assert "experiencia" not in datos
    vacios = latex_gen.datos_vacios()
    for clave, valor in vacios.items():
        assert clave in datos
        assert isinstance(datos[clave], type(valor))
    # Un archivo antiguo sin la clave foto_recorte la recibe como None.
    assert datos["foto_recorte"] is None


# ---------------- autosave ----------------

def _escribir_autosave(contenido):
    os.makedirs(prefs.APP_DIR, exist_ok=True)
    with open(os.path.join(prefs.APP_DIR, "autosave.cvjson"), "w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False)


def test_autosave_v2_round_trip_devuelve_datos_planos(prefs_tmp):
    tmp = prefs_tmp
    origenes = tmp / "medios"
    origenes.mkdir()
    foto = origenes / "foto.png"
    foto.write_bytes(b"foto-autosave")
    logo = origenes / "logo.png"
    logo.write_bytes(b"logo-autosave")

    datos = latex_gen.datos_vacios()
    datos["idioma_cv"] = "es"
    datos["nombre"] = "Ana"
    datos["foto"] = str(foto)
    datos["trabajo"] = [{"puesto": "Dev", "empresa": "Acme", "logo": str(logo)}]

    api = main.Api(None)
    assert api.autosave(datos) == {"ok": True}

    leidos = api.autosave_leer()
    assert isinstance(leidos, dict)
    # El sobre v2 no debe filtrarse al frontend.
    assert not ({"version", "medios", "datos"} & set(leidos))
    assert set(leidos) == set(latex_gen.datos_vacios())

    # Los campos no-media vuelven identicos.
    for clave in latex_gen.datos_vacios():
        if clave in ("foto", "trabajo"):
            continue
        assert leidos[clave] == datos[clave], clave
    assert leidos["trabajo"][0]["puesto"] == "Dev"
    assert leidos["trabajo"][0]["empresa"] == "Acme"

    # Los medios se rematerializan en CACHE_DIR.
    for vieja, nueva, esperado in (
        (str(foto), leidos["foto"], b"foto-autosave"),
        (str(logo), leidos["trabajo"][0]["logo"], b"logo-autosave"),
    ):
        assert nueva != vieja
        assert os.path.isfile(nueva)
        assert os.path.basename(nueva).startswith("cv_")
        assert os.path.realpath(os.path.dirname(nueva)) == os.path.realpath(prefs.CACHE_DIR)
        with open(nueva, "rb") as f:
            assert f.read() == esperado


def test_autosave_legacy_plano_se_migra_y_relena(prefs_tmp):
    _escribir_autosave(
        {
            "nombre": "CV antiguo",
            "experiencia": [
                {"tipo": "Trabajo", "puesto": "Dev"},
                {"tipo": "Pasantía", "puesto": "Becaria"},
            ],
        }
    )

    leidos = main.Api(None).autosave_leer()
    assert isinstance(leidos, dict)
    # Migracion experiencia -> trabajo/pasantia.
    assert leidos["trabajo"] == [{"tipo": "Trabajo", "puesto": "Dev"}]
    assert leidos["pasantia"] == [{"tipo": "Pasantía", "puesto": "Becaria"}]
    assert "experiencia" not in leidos
    assert leidos["nombre"] == "CV antiguo"
    # Relleno de claves ausentes con el esquema vacio.
    for clave, valor in latex_gen.datos_vacios().items():
        assert clave in leidos
        assert isinstance(leidos[clave], type(valor)), clave
    assert leidos["foto_recorte"] is None


def test_autosave_leer_ausente_o_invalido_devuelve_none(prefs_tmp):
    api = main.Api(None)
    ruta = os.path.join(prefs.APP_DIR, "autosave.cvjson")

    # Fichero ausente.
    assert api.autosave_leer() is None

    # JSON corrupto.
    os.makedirs(prefs.APP_DIR, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("{no-es-json")
    assert api.autosave_leer() is None

    # JSON valido pero no dict.
    _escribir_autosave([1, 2, 3])
    assert api.autosave_leer() is None

    # Sobre v2 sin datos utilizables.
    _escribir_autosave({"version": 2, "datos": "texto", "medios": {}})
    assert api.autosave_leer() is None
