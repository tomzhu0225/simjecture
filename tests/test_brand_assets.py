"""Keep the approved brand bytes, public asset boundary, and HTML contract stable."""

from __future__ import annotations

import hashlib
import threading
import xml.etree.ElementTree as ET
from contextlib import closing
from html.parser import HTMLParser
from http.client import HTTPConnection
from io import BytesIO

import pytest
from PIL import Image

from conjecture_solver.web import server as web_server
from conjecture_solver.web.application import SimjectureWebApplication

# Digests of the approved kit, rather than a second runtime-dependent source copy.
APPROVED_ASSETS = {
    "simjecture-lockup-light.svg": (
        "abf44a24ded52c69d99fc1418b78d554f001789e754d1e7377ae053e317214ec"
    ),
    "simjecture-lockup-dark.svg": (
        "56ed8a76b4378e4dea18431aba765d31af5a7476c4fb359e21713b0f06f9a4b0"
    ),
    "favicon.svg": "4ea77ae6f63bd6a2c5ab402683df91427d56a347b6473444f29f0f3d09493d03",
    "favicon.ico": "9092f49561c26b94e142a33137479c053a51fea1035469937861c969af2f8acb",
}
EXPECTED_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data: blob:; connect-src 'self' data:; object-src 'none'; "
    "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
)


@pytest.fixture(scope="module")
def brand_server(tmp_path_factory):
    root = tmp_path_factory.mktemp("brand-http")
    app = SimjectureWebApplication(
        runs_root=root, scan_roots=(root,), allow_mutations=False
    )
    server = web_server.create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _get(server, path):
    # HTTPConnection preserves dot segments; URL-normalizing clients can conceal a
    # server traversal regression by rewriting the request before it reaches it.
    with closing(HTTPConnection("127.0.0.1", server.server_port, timeout=10)) as client:
        client.request("GET", path)
        response = client.getresponse()
        return response.status, dict(response.getheaders()), response.read()


@pytest.mark.parametrize("filename", APPROVED_ASSETS)
def test_brand_assets_serve_approved_bytes_and_security_headers(brand_server, filename):
    status, headers, body = _get(brand_server, "/assets/brand/" + filename)
    assert status == 200
    expected_type = "image/x-icon" if filename.endswith(".ico") else "image/svg+xml"
    assert headers["Content-Type"] == expected_type
    assert headers["Content-Length"] == str(len(body))
    assert headers["Cache-Control"] == "no-cache"
    assert headers["Content-Security-Policy"] == EXPECTED_CSP
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert hashlib.sha256(body).hexdigest() == APPROVED_ASSETS[filename]
    assert body == (web_server.STATIC_ROOT / "brand" / filename).read_bytes()


@pytest.mark.parametrize("filename", ["favicon.svg", "favicon.ico"])
def test_favicon_aliases_match_shared_assets(brand_server, filename):
    asset_status, asset_headers, asset_body = _get(brand_server, "/assets/brand/" + filename)
    status, headers, body = _get(brand_server, "/" + filename + "?v=approved")
    assert status == asset_status == 200
    assert body == asset_body
    assert headers["Content-Type"] == asset_headers["Content-Type"]
    assert headers["Content-Security-Policy"] == EXPECTED_CSP
    assert headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize(
    "path",
    [
        "/assets/brand/",
        "/assets/brand/missing.svg",
        "/assets/brand/README.md",
        "/assets/brand/OPEN-SANS-NOTICE.txt",
        "/assets/brand/APACHE-2.0.txt",
        "/assets/brand/simjecture-lockup-light.svg.js",
        "/assets/brand/SIMJECTURE-LOCKUP-LIGHT.svg",
        "/assets/brand/../workspace.html",
        "/assets/brand/../../server.py",
        "/assets/brand/%2e%2e/workspace.html",
        "/assets/brand/%2e%2e%2fworkspace.html",
        "/assets/brand/..%5cworkspace.html",
        "/assets/brand/%252e%252e/workspace.html",
        "/assets/brand/simjecture-lockup-light.svg/extra",
        "/assets/brand/simjecture-lockup-light.svg%00",
    ],
)
def test_brand_namespace_rejects_unknown_files_and_traversal(brand_server, path):
    status, headers, body = _get(brand_server, path)
    assert status == 404
    assert headers["Content-Type"].startswith("application/json")
    assert b"static resource not found" in body
    assert headers["Content-Security-Policy"] == EXPECTED_CSP


def test_brand_allowlist_is_explicit_even_for_existing_files(brand_server, tmp_path, monkeypatch):
    assert {name for name in web_server.STATIC_ASSETS if name.startswith("brand/")} == {
        "brand/" + filename for filename in APPROVED_ASSETS
    }
    directory = tmp_path / "brand"
    directory.mkdir()
    (directory / "not-approved.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    monkeypatch.setattr(web_server, "STATIC_ROOT", tmp_path)
    status, _, body = _get(brand_server, "/assets/brand/not-approved.svg")
    assert status == 404
    assert b"static resource not found" in body


@pytest.mark.parametrize("filename", [name for name in APPROVED_ASSETS if name.endswith(".svg")])
def test_svg_artwork_is_self_contained_font_independent_geometry(filename):
    raw = (web_server.STATIC_ROOT / "brand" / filename).read_bytes()
    assert b"<!DOCTYPE" not in raw.upper()
    assert b"<!ENTITY" not in raw.upper()
    root = ET.fromstring(raw)
    namespace = "{http://www.w3.org/2000/svg}"
    assert root.tag == namespace + "svg"
    assert root.find(namespace + "title").text == "Simjecture"
    viewbox = [float(value) for value in root.attrib["viewBox"].split()]
    assert viewbox[:2] == [0, 0]
    assert viewbox[2] > 0 and viewbox[3] > 0
    assert root.findall(".//" + namespace + "path")
    safe_elements = {"svg", "title", "g", "path", "circle", "rect"}
    for element in root.iter():
        assert element.tag.startswith(namespace)
        assert element.tag.removeprefix(namespace) in safe_elements
        for attribute, value in element.attrib.items():
            name = attribute.rsplit("}", 1)[-1].lower()
            assert not name.startswith("on")
            assert name not in {"href", "src", "style"}
            assert not name.startswith("font")
            assert "url(" not in value.lower()
    if filename.startswith("simjecture-lockup"):
        assert viewbox == [0, 0, 288.824, 64]
        # All ten wordmark letters are paths, never runtime font glyphs.
        assert len(root.findall(".//" + namespace + "path")) == 11


@pytest.mark.parametrize(
    ("filename", "expected_colors"),
    [
        ("simjecture-lockup-light.svg", {"#6658D9", "#202332"}),
        ("simjecture-lockup-dark.svg", {"#B5A7FF", "#F4F4FC"}),
        ("favicon.svg", {"#6658D9", "#FFFFFF"}),
    ],
)
def test_brand_artwork_uses_approved_theme_palette(filename, expected_colors):
    root = ET.parse(web_server.STATIC_ROOT / "brand" / filename)
    colors = {
        value
        for element in root.iter()
        for attribute, value in element.attrib.items()
        if attribute in {"fill", "stroke"} and value != "none"
    }
    assert colors == expected_colors


def test_ico_contains_decodable_small_size_variants():
    raw = (web_server.STATIC_ROOT / "brand/favicon.ico").read_bytes()
    with Image.open(BytesIO(raw)) as icon:
        assert icon.format == "ICO"
        assert icon.ico.sizes() == {(16, 16), (32, 32), (48, 48)}
        for size in icon.ico.sizes():
            frame = icon.ico.getimage(size)
            frame.load()
            assert frame.size == size
            assert frame.getbbox() is not None


class _BrandMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.brand_elements = []
        self.in_brand = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.elements.append((tag, attributes))
        if tag == "a" and "brand" in attributes.get("class", "").split():
            self.in_brand = True
        if self.in_brand:
            self.brand_elements.append((tag, attributes))

    def handle_endtag(self, tag):
        if tag == "a":
            self.in_brand = False


@pytest.mark.parametrize(
    ("route", "name", "target", "variants"),
    [
        ("/workspace", "Simjecture research workspace", "/workspace", ["dark"]),
        ("/monitor", "Simjecture home", "/", ["light", "dark"]),
    ],
)
def test_both_headers_use_shared_decorative_artwork_and_favicons(
    brand_server, route, name, target, variants
):
    status, _, body = _get(brand_server, route)
    assert status == 200
    markup = _BrandMarkup()
    markup.feed(body.decode())
    brands = [attrs for tag, attrs in markup.brand_elements if tag == "a"]
    assert len(brands) == 1
    assert brands[0]["aria-label"] == name
    assert brands[0]["href"] == target
    images = [attrs for tag, attrs in markup.brand_elements if tag == "img"]
    assert len(images) == len(variants)
    for attrs, variant in zip(images, variants, strict=True):
        assert attrs["src"] == f"/assets/brand/simjecture-lockup-{variant}.svg"
        assert set(attrs["class"].split()) == {"brand-logo", f"brand-logo-{variant}"}
        assert attrs["alt"] == ""
        assert attrs["aria-hidden"] == "true"
        assert float(attrs["width"]) > 0 and float(attrs["height"]) > 0
    assert not any(tag == "svg" for tag, _ in markup.brand_elements)
    assert not any(
        {"mark", "brand-mark"}.intersection(attrs.get("class", "").split())
        for _, attrs in markup.brand_elements
    )
    links = [attrs for tag, attrs in markup.elements if tag == "link"]
    icons = {attrs["href"]: attrs for attrs in links if attrs.get("rel") == "icon"}
    assert icons["/favicon.svg"]["type"] == "image/svg+xml"
    assert icons["/favicon.svg"]["sizes"] == "any"
    assert icons["/favicon.ico"]["type"] == "image/x-icon"
    assert set(icons["/favicon.ico"]["sizes"].split()) == {"16x16", "32x32", "48x48"}
    stylesheets = [attrs["href"] for attrs in links if attrs.get("rel") == "stylesheet"]
    assert stylesheets[-1] == "/assets/interface.css"


def test_shared_brand_css_keeps_existing_security_policy(brand_server):
    status, headers, body = _get(brand_server, "/assets/interface.css")
    assert status == 200
    assert headers["Content-Type"] == "text/css; charset=utf-8"
    assert headers["Content-Security-Policy"] == EXPECTED_CSP
    assert b".brand-logo" in body
    assert b".brand-logo-light" in body
    assert b".brand-logo-dark" in body
