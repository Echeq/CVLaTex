# -*- coding: utf-8 -*-
"""Local HTTP server hardening: session token, Host/Origin checks, media scope.

The app server on 127.0.0.1 must only answer the app window: every route
requires the per-session token (query or cookie), the Host header must be the
exact loopback authority, and /media//preview/ only expose the files the app
itself creates. Tests use the real ThreadingHTTPServer on an ephemeral port.
"""

import http.client
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

import main  # noqa: E402
import prefs  # noqa: E402

MEDIA_NAME = "foto_" + "a" * 32 + ".png"
WRONG_EXT_NAME = "foto_" + "b" * 32 + ".gif"
# materialize_media() imports/restores media as cv_<uuid4().hex>.<ext>.
CV_MEDIA_NAME = "cv_" + "c" * 32 + ".png"
CV_WRONG_EXT_NAME = "cv_" + "d" * 32 + ".gif"
CV_NOT_HEX_NAME = "cv_" + "z" * 32 + ".png"


@pytest.fixture()
def prefs_tmp(tmp_path, monkeypatch):
    """Isolate prefs (dirs and cache) from the user machine."""
    app = tmp_path / "app"
    monkeypatch.setattr(prefs, "APP_DIR", str(app))
    monkeypatch.setattr(prefs, "CACHE_DIR", str(app / "cache"))
    monkeypatch.setattr(prefs, "BUILD_DIR", str(app / "cache" / "build"))
    monkeypatch.setattr(prefs, "PREFS_FILE", str(app / "prefs.json"))
    monkeypatch.setattr(prefs, "_CACHE", None)
    return tmp_path


@pytest.fixture()
def server(prefs_tmp):
    """Real loopback server plus the fixture media/build tree."""
    cache = prefs.CACHE_DIR
    build = prefs.BUILD_DIR
    os.makedirs(os.path.join(cache, "out"), exist_ok=True)
    os.makedirs(build, exist_ok=True)
    with open(os.path.join(cache, MEDIA_NAME), "wb") as f:
        f.write(b"MEDIA-BYTES")
    with open(os.path.join(cache, WRONG_EXT_NAME), "wb") as f:
        f.write(b"WRONG-EXT")
    with open(os.path.join(cache, CV_MEDIA_NAME), "wb") as f:
        f.write(b"CV-MEDIA-BYTES")
    with open(os.path.join(cache, CV_WRONG_EXT_NAME), "wb") as f:
        f.write(b"CV-WRONG-EXT")
    with open(os.path.join(cache, CV_NOT_HEX_NAME), "wb") as f:
        f.write(b"CV-NOT-HEX")
    with open(os.path.join(build, "main.tex"), "w", encoding="utf-8") as f:
        f.write("SECRET")
    with open(os.path.join(cache, "out", "result.pdf"), "wb") as f:
        f.write(b"%PDF-out")
    with open(os.path.join(build, "result.pdf"), "wb") as f:
        f.write(b"%PDF-build")
    with open(os.path.join(prefs_tmp, "outside.png"), "wb") as f:
        f.write(b"OUTSIDE")
    with open(os.path.join(prefs_tmp, "outside.pdf"), "wb") as f:
        f.write(b"OUTSIDE")

    srv, port, token = main._start_server()
    try:
        yield port, token
    finally:
        srv.shutdown()
        srv.server_close()


def _request(port, path, token=None, cookie=None, host=None, origin=None, method="GET"):
    """One HTTP request; returns (status, response, body bytes)."""
    headers = {}
    if token is not None:
        separator = "&" if "?" in path else "?"
        path = "%s%stoken=%s" % (path, separator, token)
    if cookie is not None:
        headers["Cookie"] = "%s=%s" % (main.SESSION_COOKIE, cookie)
    if origin is not None:
        headers["Origin"] = origin
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        if host is None:
            conn.request(method, path, headers=headers)
        else:
            # A Host header in `headers` disables http.client's automatic one.
            headers["Host"] = host
            conn.request(method, path, headers=headers)
        resp = conn.getresponse()
        body = resp.read()
        return resp.status, resp, body
    finally:
        conn.close()


def _cookie_from(resp):
    header = resp.getheader("Set-Cookie") or ""
    match = re.search(r"%s=([^;]+)" % main.SESSION_COOKIE, header)
    return match.group(1) if match else None


def test_root_requires_token_and_sets_session_cookie(server):
    port, token = server
    status, resp, body = _request(port, "/")
    assert status == 403
    assert token.encode() not in body

    status, resp, body = _request(port, "/?token=" + "x" * 43)
    assert status == 403
    assert token.encode() not in body

    status, resp, body = _request(port, "/", token=token)
    assert status == 200
    cookie_header = resp.getheader("Set-Cookie") or ""
    assert "%s=%s" % (main.SESSION_COOKIE, token) in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=Strict" in cookie_header
    assert "Path=/" in cookie_header
    assert token.encode() not in body

    cookie = _cookie_from(resp)
    assert cookie == token
    status, _, body = _request(port, "/index.html", cookie=cookie)
    assert status == 200
    assert b"<html" in body.lower()


def test_security_headers_on_success_and_error(server):
    port, token = server
    for path, code in (("/", 403), ("/index.html", 403)):
        status, resp, _ = _request(port, path)
        assert status == code
        assert resp.getheader("X-Content-Type-Options") == "nosniff"
        assert resp.getheader("Referrer-Policy") == "no-referrer"
        assert resp.getheader("Cache-Control") == "no-store"
    status, resp, _ = _request(port, "/?token=" + token)
    assert status == 200
    assert resp.getheader("X-Content-Type-Options") == "nosniff"
    assert resp.getheader("Referrer-Policy") == "no-referrer"
    assert resp.getheader("Cache-Control") == "no-store"


def test_host_header_must_be_exact_loopback_authority(server):
    port, token = server
    cookie = token
    expected = "127.0.0.1:%d" % port
    for bad_host in ("evil.example:%d" % port, "localhost:%d" % port, "evil.example"):
        status, _, body = _request(port, "/", token=token, host=bad_host)
        assert status == 403, bad_host
        assert token.encode() not in body
        status, _, _ = _request(port, "/index.html", cookie=cookie, host=bad_host)
        assert status == 403, bad_host
    # Missing Host header.
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.putrequest("GET", "/?token=" + token, skip_host=True)
        conn.endheaders()
        resp = conn.getresponse()
        resp.read()
        assert resp.status == 403
    finally:
        conn.close()
    # Exact authority passes.
    status, _, _ = _request(port, "/", token=token, host=expected)
    assert status == 200


def test_cross_origin_requests_are_rejected(server):
    port, token = server
    status, _, body = _request(
        port, "/", token=token, origin="https://evil.example"
    )
    assert status == 403
    assert token.encode() not in body
    status, _, _ = _request(port, "/index.html", cookie=token, origin="https://evil.example")
    assert status == 403
    status, _, _ = _request(
        port, "/", token=token, origin="http://127.0.0.1:%d" % port
    )
    assert status == 200


def test_media_only_serves_flat_app_media(server):
    port, token = server
    status, _, body = _request(port, "/media/" + MEDIA_NAME, cookie=token)
    assert status == 200
    assert body == b"MEDIA-BYTES"

    for path in (
        "/media/build/main.tex",
        "/media/out/result.pdf",
        "/media/main.tex",
        "/media/../outside.png",
        "/media/foto_../../x.png",
        "/media//tmp/outside.png",
        "/media/%2fetc%2fpasswd",
        "/media/" + WRONG_EXT_NAME,
        "/media/",
    ):
        status, _, body = _request(port, path, cookie=token)
        assert status == 404, path
        assert b"SECRET" not in body
        assert b"OUTSIDE" not in body


def test_media_serves_materialized_cv_files(server):
    """Imported/restored media is saved as cv_<32hex>.<png|jpg|jpeg>."""
    port, token = server
    # Obtain the session cookie the way the window does, then use it.
    status, resp, _ = _request(port, "/", token=token)
    assert status == 200
    cookie = _cookie_from(resp)
    assert cookie == token

    status, resp, body = _request(port, "/media/" + CV_MEDIA_NAME, cookie=cookie)
    assert status == 200
    assert body == b"CV-MEDIA-BYTES"

    for path in (
        "/media/cv_../../x.png",
        "/media/" + CV_WRONG_EXT_NAME,
        "/media/" + CV_NOT_HEX_NAME,
    ):
        status, _, body = _request(port, path, cookie=cookie)
        assert status == 404, path
        assert b"CV-MEDIA-BYTES" not in body
        assert b"OUTSIDE" not in body


def test_preview_only_serves_flat_pdfs_from_build_dir(server):
    port, token = server
    status, _, body = _request(port, "/preview/result.pdf", cookie=token)
    assert status == 200
    assert body == b"%PDF-build"

    for path in (
        "/preview/main.tex",
        "/preview/../outside.pdf",
        "/preview/sub/result.pdf",
        "/preview/",
    ):
        status, _, body = _request(port, path, cookie=token)
        assert status == 404, path
        assert b"SECRET" not in body


def test_static_routes_and_pdfjs_require_session(server):
    port, token = server
    for path in ("/app.js", "/style.css", "/i18n.js", "/pdfjs/viewer.html", "/favicon.ico"):
        status, _, _ = _request(port, path)
        assert status == 403, path
        status, _, body = _request(port, path, cookie=token)
        if path == "/favicon.ico":
            assert status == 204
        else:
            assert status == 200, path
            assert body


def test_unknown_routes_404_with_session_and_post_is_not_implemented(server):
    port, token = server
    status, _, _ = _request(port, "/nope", cookie=token)
    assert status == 404
    status, _, _ = _request(port, "/", cookie=token, method="POST")
    assert status in (405, 501)
