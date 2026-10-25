"""Hosted general runtimes require a qualified executor and never invent presets."""

import socket
import sys
import threading
import time

import pytest

from conjecture_solver.public.native import materialize, registry
from conjecture_solver.research_service import put
from tests.test_public_workspace import app as public_app
from tests.test_public_workspace import session

FAMILIES = ["freecad", "gmsh", "elmer", "feos", "material-eos"]


@pytest.fixture
def app(tmp_path):
    return public_app.__wrapped__(tmp_path)


def configure(app, *, executor=True, qualified=True, families=FAMILIES, origin="http://testserver"):
    root = app.state.store.root
    entries = [
        {
            "id": family + "-runtime", "family": family, "name": family,
            "qualified": qualified, "runtime_only": True, "binary": sys.executable,
            "scope": "Custom input files through the general executor",
            "qualification": "Synthetic test fixture only", "parameters": {},
        }
        for family in families
    ]
    put(root / "tools.json", {"tools": entries})
    put(root / "settings.json", {
        "public_origin": origin, "executor_qualified": executor,
        "tools_registry": str(root / "tools.json"),
    })
    return entries


@pytest.mark.parametrize("executor,qualified", [(True, True), (False, True), (True, False)])
def test_catalogue_exposes_only_qualified_general_runtimes(app, executor, qualified):
    configure(app, executor=executor, qualified=qualified)
    client = session(app)
    response = client.get("/api/workspace/tools")
    assert response.status_code == 200
    cards = response.json()
    if executor and qualified:
        assert {card["id"] for card in cards} == set(FAMILIES)
        assert all(card["general_execution"] and card["variants"] == [] for card in cards)
        assert len(registry(app.state.store.root)) == len(FAMILIES)
    else:
        assert cards == []
        assert registry(app.state.store.root) == []


def test_runtime_cannot_be_admitted_or_materialized_as_a_native_preset(app, tmp_path, monkeypatch):
    from conjecture_solver.public import worker

    entry = configure(app, families=["gmsh"])[0]
    client = session(app)
    before = client.get("/api/workspace/bootstrap").json()["projects"]
    response = client.post("/api/workspace/tool-demo", json={"name": entry["id"]})
    assert response.status_code == 400
    assert client.get("/api/workspace/bootstrap").json()["projects"] == before
    with pytest.raises(ValueError, match="run_command"):
        materialize(entry, {}, tmp_path / "case")
    assert not (tmp_path / "case").exists()
    monkeypatch.setattr(worker, "check_running", lambda *args: None)
    with pytest.raises(ValueError, match="run_command"):
        worker.run_native_case(app.state.store, "fixture", None, entry["id"], {})


def test_browser_prepares_a_custom_study_without_a_fake_starter_preset(app):
    playwright = pytest.importorskip("playwright.sync_api")
    uvicorn = pytest.importorskip("uvicorn")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    configure(app, families=["gmsh"], origin=origin)
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/workspace")
            if not page.locator(".workspace-resources").evaluate("e => e.open"):
                page.locator(".workspace-resources summary").click()
            page.get_by_role("button", name="Research tools", exact=True).click()
            page.get_by_role("button", name="View Gmsh details", exact=True).click()
            choice = page.get_by_role("combobox", name="Gmsh study setup", exact=True)
            playwright.expect(choice).to_have_value("custom-study")
            playwright.expect(choice.locator("option")).to_have_count(1)
            page.get_by_role("button", name="Prepare in chat", exact=True).click()
            playwright.expect(page.locator("#chat-input")).to_have_value(
                __import__("re").compile("Gmsh")
            )
            with app.state.store.connect() as db:
                assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
            assert not errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
