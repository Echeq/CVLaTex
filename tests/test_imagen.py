# -*- coding: utf-8 -*-
"""Api.guardar_imagen: data URLs base64 (PNG/JPEG) con prefijos foto/logo/recorte.

No hay GUI ni LaTeX: prefs se aisla con el fixture prefs_tmp (mismo patron que
test_bloques.py) y se comprueba que todo fichero escrito cae dentro de tmp_path.
"""

import base64
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import main  # noqa: E402
import prefs  # noqa: E402

# Constantes minimas de 1x1 para no depender de Pillow: un PNG RGBA de 70 bytes
# (firma + IHDR 1x1 + IDAT + IEND) y un JPEG de 160 bytes (SOI ... EOI).
PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA"
    "60e6kgAAAABJRU5ErkJggg=="
)
JPG_B64 = (
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRof"
    "Hh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAAB"
    "AAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=="
)

PATRON_NOMBRE = re.compile(r"^(foto|logo|recorte)_[0-9a-f]{32}\.(png|jpg)$")
PREFIJOS = ("foto", "logo", "recorte")


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


def data_url(mime, b64):
    """Construye la data URL que espera Api.guardar_imagen."""
    return "data:%s;base64,%s" % (mime, b64)


def ficheros_bajo(base):
    """Rutas absolutas de los ficheros bajo base (para detectar escrituras)."""
    rutas = set()
    for raiz, _dirs, ficheros in os.walk(str(base)):
        for nombre in ficheros:
            rutas.add(os.path.abspath(os.path.join(raiz, nombre)))
    return rutas


@pytest.mark.parametrize("tipo", [None, "foto", "logo", "recorte"])
@pytest.mark.parametrize(
    "mime,b64,ext",
    [("image/png", PNG_B64, ".png"), ("image/jpeg", JPG_B64, ".jpg")],
    ids=["png", "jpeg"],
)
def test_guardar_imagen_valida_escribe_en_cache(mime, b64, ext, tipo, prefs_tmp):
    antes = ficheros_bajo(prefs_tmp)

    resultado = main.Api(None).guardar_imagen(data_url(mime, b64), tipo)

    assert resultado["ok"] is True, resultado.get("errores")
    ruta = resultado["path"]
    assert os.path.isabs(ruta)
    assert os.path.dirname(ruta) == prefs.CACHE_DIR
    # Nada fuera de tmp_path: la ruta y el commonpath lo confirman.
    assert os.path.commonpath([os.path.abspath(ruta), str(prefs_tmp)]) == str(prefs_tmp)

    nombre = os.path.basename(ruta)
    assert PATRON_NOMBRE.fullmatch(nombre)
    esperado = tipo if tipo in PREFIJOS else "foto"
    assert nombre.startswith(esperado + "_")
    assert nombre.endswith(ext)
    assert resultado["url"] == "/media/" + nombre

    with open(ruta, "rb") as f:
        assert f.read() == base64.b64decode(b64, validate=True)

    # El unico fichero nuevo es el devuelto, y esta bajo tmp_path.
    assert ficheros_bajo(prefs_tmp) == antes | {os.path.abspath(ruta)}


@pytest.mark.parametrize("tipo", ["otro", "FOTO", "fotos", "", 123, 0])
def test_tipo_desconocido_cae_a_foto(tipo, prefs_tmp):
    resultado = main.Api(None).guardar_imagen(data_url("image/png", PNG_B64), tipo)
    assert resultado["ok"] is True, resultado.get("errores")
    nombre = os.path.basename(resultado["path"])
    assert PATRON_NOMBRE.fullmatch(nombre)
    assert nombre.startswith("foto_")
    assert os.path.commonpath([os.path.abspath(resultado["path"]), str(prefs_tmp)]) == str(prefs_tmp)


CASOS_INVALIDOS = [
    pytest.param("hola", id="sin-prefijo-data"),
    pytest.param("data:image/png;base64,!!!!", id="base64-con-simbolos"),
    pytest.param("data:image/png;base64,", id="payload-vacio"),
    pytest.param("data:image/png;base64,iVBORw0KGgo", id="longitud-invalida"),
    pytest.param(data_url("image/png", PNG_B64.rstrip("=")), id="padding-quitado"),
    pytest.param(data_url("image/png", PNG_B64[:21]), id="truncado-png"),
    pytest.param(data_url("image/jpeg", JPG_B64[:-7]), id="truncado-jpeg"),
    pytest.param(data_url("text/plain", "aGVsbG8="), id="mime-texto"),
    pytest.param(
        data_url("image/gif", "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"),
        id="mime-gif",
    ),
    pytest.param("data:;base64," + PNG_B64, id="sin-mime"),
    pytest.param("data:base64," + PNG_B64, id="data-url-sin-mime"),
    pytest.param(PNG_B64, id="solo-base64"),
    pytest.param("data:image/png," + PNG_B64, id="data-url-sin-base64"),
    pytest.param("data:image/png;base64,====", id="paddings-extra"),
]


@pytest.mark.parametrize("valor", CASOS_INVALIDOS)
def test_data_url_invalida_devuelve_error_sin_escribir(valor, prefs_tmp):
    antes = ficheros_bajo(prefs_tmp)

    resultado = main.Api(None).guardar_imagen(valor)

    assert resultado["ok"] is False
    errores = resultado["errores"]
    assert isinstance(errores, list) and errores
    assert all(isinstance(e, str) and e.strip() for e in errores)
    # Un fallo temprano no debe dejar ficheros (ni siquiera el directorio).
    assert ficheros_bajo(prefs_tmp) == antes


@pytest.mark.parametrize(
    "valor",
    [None, 123, 1.5, [], {}, b"abc", True, object()],
    ids=["none", "int", "float", "list", "dict", "bytes", "bool", "object"],
)
def test_entrada_no_str_nunca_lanza(valor, prefs_tmp):
    antes = ficheros_bajo(prefs_tmp)

    resultado = main.Api(None).guardar_imagen(valor)

    assert resultado["ok"] is False
    assert resultado["errores"] and all(resultado["errores"])
    assert ficheros_bajo(prefs_tmp) == antes


@pytest.mark.parametrize(
    "valor",
    [
        pytest.param("data:;base64," + PNG_B64, id="sin-mime-png"),
        pytest.param("data:;base64," + JPG_B64, id="sin-mime-jpeg"),
        pytest.param("data:base64," + PNG_B64, id="data-base64-png"),
        pytest.param(PNG_B64, id="base64-suelto-png"),
        pytest.param(JPG_B64, id="base64-suelto-jpeg"),
    ],
)
def test_sin_mime_nunca_lanza(valor, prefs_tmp):
    resultado = main.Api(None).guardar_imagen(valor)
    assert isinstance(resultado, dict)
    assert resultado["ok"] is False
    assert resultado["errores"]
