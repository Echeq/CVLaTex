# -*- coding: utf-8 -*-
"""Exportar/abrir .cvjson v3: incrustado y materializado de medios.

Simula una cache movida borrando los ficheros originales antes de importar:
open_cv debe escribir los medios en prefs.CACHE_DIR y reescribir las rutas.
Tambien cubre la lectura de v1/v2 (con copia `<fichero>.v2.bak` antes de
migrar) y el autosave v3 con autosave legacy plano.
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
    monkeypatch.setattr(api, "choose_file", lambda *a, **k: str(ruta))
    return api


def test_export_cv_v3_incrusta_medios_y_open_cv_los_materializa(prefs_tmp, monkeypatch):
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
    datos = latex_gen.empty_data()
    datos["cv_language"] = "es"
    datos["name"] = "Ana"
    # Estado tras aplicar un recorte: "photo" es la imagen ya recortada,
    # "photo_original" la subida y "photo_crop" el rectangulo normalizado.
    datos["photo"] = str(recorte)
    datos["photo_original"] = str(foto)
    datos["photo_crop"] = rectangulo
    datos["school_logo"] = str(logo)
    datos["work"] = [
        {"position": "Dev", "company": "Acme", "logo": str(logo)},
        {"position": "Gif", "company": "Otra", "logo": str(gif)},
        {"position": "Inexistente", "company": "Otra", "logo": str(inexistente)},
    ]

    salida = tmp / "mi_cv.cvjson"
    api = _api_con_ruta(monkeypatch, salida)
    resultado = api.export_cv(datos)
    assert resultado == {"ok": True, "ruta": str(salida)}

    contenido = json.loads(salida.read_text(encoding="utf-8"))
    assert contenido["version"] == 3
    assert contenido["data"]["photo"] == str(recorte)
    assert contenido["data"]["photo_crop"] == rectangulo

    esperados = {
        str(foto): b"contenido-foto-original",
        str(recorte): b"contenido-recorte-original",
        str(logo): b"contenido-logo-original",
    }
    medios = contenido["media"]
    assert set(medios) == set(esperados)
    for ruta_original, info in medios.items():
        assert info["name"] == os.path.basename(ruta_original)
        assert base64.b64decode(info["b64"]) == esperados[ruta_original]

    # Cache movida: los ficheros originales ya no existen.
    for ruta in (foto, recorte, logo):
        ruta.unlink()
    assert not foto.exists() and not recorte.exists() and not logo.exists()

    resultado = _api_con_ruta(monkeypatch, salida).open_cv()
    assert resultado["ok"] is True
    datos_nuevos = resultado["datos"]

    # Un fichero cv_* por cada medio distinto incrustado: photo (recorte),
    # photo_original y school_logo (que comparte ruta con work[0].logo).
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

    for clave in ("photo", "photo_original", "school_logo"):
        ruta_nueva = datos_nuevos[clave]
        assert ruta_nueva != datos[clave]
        assert os.path.isfile(ruta_nueva), clave
        assert os.path.basename(ruta_nueva).startswith("cv_")
        assert os.path.realpath(os.path.dirname(ruta_nueva)) == os.path.realpath(prefs.CACHE_DIR)

    with open(datos_nuevos["photo"], "rb") as f:
        assert f.read() == b"contenido-recorte-original"
    with open(datos_nuevos["photo_original"], "rb") as f:
        assert f.read() == b"contenido-foto-original"
    with open(datos_nuevos["school_logo"], "rb") as f:
        assert f.read() == b"contenido-logo-original"

    assert datos_nuevos["work"][0]["logo"] == datos_nuevos["school_logo"]
    # El rectangulo de recorte (dict) sobrevive a la importacion v2: el
    # relleno con empty_data() solo sustituye claves ausentes cuando el
    # valor por defecto es None, sin comprobar el tipo contra NoneType.
    assert datos_nuevos["photo_crop"] == rectangulo
    # El gif no se incrusta y el logo inexistente no se reescribe.
    assert datos_nuevos["work"][1]["logo"] == str(gif)
    assert datos_nuevos["work"][2]["logo"] == str(inexistente)


def test_open_cv_v1_conserva_rutas_y_relena_vacios(prefs_tmp, monkeypatch):
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
    resultado = api.open_cv()
    assert resultado["ok"] is True
    datos = resultado["datos"]

    # v1 no materializa: la ruta original se conserva aunque el fichero exista.
    assert datos["photo"] == str(ruta_foto)
    assert os.path.isfile(datos["photo"])
    # Antes de migrar un fichero <v3 se copia a <fichero>.v2.bak.
    respaldo = tmp / "v1.cvjson.v2.bak"
    assert respaldo.read_text(encoding="utf-8") == cvjson.read_text(encoding="utf-8")
    # Migracion y relleno con el esquema vacio.
    assert datos["work"] == [{"tipo": "Trabajo", "position": "Dev"}]
    assert datos["internships"] == []
    assert "experiencia" not in datos
    vacios = latex_gen.empty_data()
    for clave, valor in vacios.items():
        assert clave in datos
        assert isinstance(datos[clave], type(valor))
    # Un archivo antiguo sin la clave photo_crop la recibe como None.
    assert datos["photo_crop"] is None


# ---------------- autosave ----------------

def _escribir_autosave(contenido):
    os.makedirs(prefs.APP_DIR, exist_ok=True)
    with open(os.path.join(prefs.APP_DIR, "autosave.cvjson"), "w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False)


def test_autosave_v3_round_trip_devuelve_datos_planos(prefs_tmp):
    tmp = prefs_tmp
    origenes = tmp / "medios"
    origenes.mkdir()
    foto = origenes / "foto.png"
    foto.write_bytes(b"foto-autosave")
    logo = origenes / "logo.png"
    logo.write_bytes(b"logo-autosave")

    datos = latex_gen.empty_data()
    datos["cv_language"] = "es"
    datos["name"] = "Ana"
    datos["photo"] = str(foto)
    datos["work"] = [{"position": "Dev", "company": "Acme", "logo": str(logo)}]

    api = main.Api(None)
    assert api.autosave(datos) == {"ok": True}

    # El autosave guarda el mismo sobre v3 {version, data, media}.
    with open(os.path.join(prefs.APP_DIR, "autosave.cvjson"), "r", encoding="utf-8") as f:
        contenido = json.load(f)
    assert contenido["version"] == 3
    assert contenido["data"]["name"] == "Ana"
    assert set(contenido["media"]) == {str(foto), str(logo)}

    leidos = api.autosave_read()
    assert isinstance(leidos, dict)
    # El sobre v3 no debe filtrarse al frontend.
    assert not ({"version", "media", "data"} & set(leidos))
    assert set(leidos) == set(latex_gen.empty_data())

    # Los campos no-media vuelven identicos.
    for clave in latex_gen.empty_data():
        if clave in ("photo", "work"):
            continue
        assert leidos[clave] == datos[clave], clave
    assert leidos["work"][0]["position"] == "Dev"
    assert leidos["work"][0]["company"] == "Acme"

    # Los medios se rematerializan en CACHE_DIR.
    for vieja, nueva, esperado in (
        (str(foto), leidos["photo"], b"foto-autosave"),
        (str(logo), leidos["work"][0]["logo"], b"logo-autosave"),
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

    leidos = main.Api(None).autosave_read()
    assert isinstance(leidos, dict)
    # Migracion experiencia -> work/internships.
    assert leidos["work"] == [{"tipo": "Trabajo", "position": "Dev"}]
    assert leidos["internships"] == [{"tipo": "Pasantía", "position": "Becaria"}]
    assert "experiencia" not in leidos
    assert leidos["name"] == "CV antiguo"
    # Relleno de claves ausentes con el esquema vacio.
    for clave, valor in latex_gen.empty_data().items():
        assert clave in leidos
        assert isinstance(leidos[clave], type(valor)), clave
    assert leidos["photo_crop"] is None


def test_autosave_read_ausente_o_invalido_devuelve_none(prefs_tmp):
    api = main.Api(None)
    ruta = os.path.join(prefs.APP_DIR, "autosave.cvjson")

    # Fichero ausente.
    assert api.autosave_read() is None

    # JSON corrupto.
    os.makedirs(prefs.APP_DIR, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("{no-es-json")
    assert api.autosave_read() is None

    # JSON valido pero no dict.
    _escribir_autosave([1, 2, 3])
    assert api.autosave_read() is None

    # Sobre v2 sin datos utilizables.
    _escribir_autosave({"version": 2, "datos": "texto", "medios": {}})
    assert api.autosave_read() is None

    # Sobre v3 sin datos utilizables.
    _escribir_autosave({"version": 3, "data": "texto", "media": {}})
    assert api.autosave_read() is None
