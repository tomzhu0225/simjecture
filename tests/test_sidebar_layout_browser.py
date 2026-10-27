"""The navigation sidebar keeps conversations visible on laptop-height screens."""

import threading

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


def nav_geometry(page):
    return page.evaluate(
        """() => [...document.querySelectorAll('.sidebar .nav-item')]
          .filter(item => item.getClientRects().length)
          .map(item => { const box = item.getBoundingClientRect();
            return {left: Math.round(box.left), width: Math.round(box.width)}; })"""
    )


@pytest.mark.parametrize(("width", "height"), [(1280, 720), (1366, 768), (1440, 1000)])
def test_sidebar_rows_align_and_conversations_stay_visible(tmp_path, width, height):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path)
    for index in range(12):
        app.workspace.create({"name": f"Laptop conversation {index + 1}"})
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/workspace")
            page.locator("#project-list .project-link").first.wait_for()
            resources = page.locator(".workspace-resources")
            # Short screens start with Resources collapsed; tall screens keep it open.
            assert resources.evaluate("e => e.open") is (height >= 860)
            if height < 860:
                page.locator(".workspace-resources summary").click()
                page.get_by_role("button", name="Research tools", exact=True).wait_for()
            # Every row, inside or outside the Resources group, has the same highlight box.
            rows = nav_geometry(page)
            assert len(rows) >= 5
            assert len({(row["left"], row["width"]) for row in rows}) == 1
            # Even with Resources expanded, several conversations remain visible.
            visible = page.evaluate(
                """() => {
                  const list = document.querySelector('#project-list').getBoundingClientRect();
                  return [...document.querySelectorAll('#project-list .project-link')]
                    .filter(link => { const box = link.getBoundingClientRect();
                      return box.top >= list.top - 1 && box.bottom <= list.bottom + 1; })
                    .length; }"""
            )
            assert visible >= 3
            # The reader's choice survives a reload.
            page.locator(".workspace-resources summary").click()
            page.reload()
            page.locator("#project-list .project-link").first.wait_for()
            assert resources.evaluate("e => e.open") is False
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
