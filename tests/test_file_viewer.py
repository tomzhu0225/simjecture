"""Unit, API, and security tests for the v0.8 integrated file viewer and baseline diffs."""

from __future__ import annotations

import base64
import threading
from pathlib import Path

import httpx
import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.file_viewer import (
    MAX_INLINE_BYTES,
    capture_file_baseline,
    describe_project_files,
    read_file_view,
    resolve_safe_file,
)
from conjecture_solver.web.server import create_server
from conjecture_solver.web.workspace import Workspace

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)


def test_resolve_safe_file_enforces_containment_and_rejects_symlinks(tmp_path: Path):
    root = tmp_path / "files"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("top-secret", encoding="utf-8")
    (root / "ok.py").write_text("x = 1\n", encoding="utf-8")
    (root / ".hidden").write_text("nope", encoding="utf-8")
    (root / "link.py").symlink_to(outside)
    sub = root / "sub"
    sub.mkdir()
    (sub / "deep.md").write_text("# Hello\n", encoding="utf-8")

    resolved, rel = resolve_safe_file(root, "sub/deep.md")
    assert resolved == (sub / "deep.md").resolve()
    assert rel == "sub/deep.md"

    for bad in [
        "",
        "   ",
        "../secret.txt",
        "/etc/passwd",
        "sub/../../secret.txt",
        ".hidden",
        "link.py",
        "missing.py",
        "ok.py\x00.txt",
    ]:
        with pytest.raises(ValueError):
            resolve_safe_file(root, bad)


def test_baseline_diff_and_rich_readers(tmp_path: Path):
    ws = Workspace(tmp_path / ".workspace")
    project = ws.create({"name": "Viewer test"})
    project_dir = ws.directory(project["id"])
    files_dir = project_dir / "files"
    (files_dir / "solver.py").write_text("def step(x):\n    return x + 1\n", encoding="utf-8")
    (files_dir / "untouched.txt").write_text("steady\n", encoding="utf-8")

    turn_dir = project_dir / "turns/0001"
    turn_dir.mkdir(parents=True)
    capture_file_baseline(project_dir, turn_dir)

    # Modify solver.py, create markdown + csv + image + binary + oversized text
    (files_dir / "solver.py").write_text(
        "def step(x):\n    return 2 * x + 1\n\n# refined\n", encoding="utf-8"
    )
    (files_dir / "notes.md").write_text("# Derivation\n\n$E = mc^2$\n", encoding="utf-8")
    (files_dir / "grid.csv").write_text("n,err\n16,0.04\n32,0.01\n", encoding="utf-8")
    (files_dir / "plot.png").write_bytes(PNG_1X1)
    (files_dir / "raw.bin").write_bytes(b"\x00\x01\x02\xff\xfe")
    (files_dir / "huge.log").write_text("a" * (MAX_INLINE_BYTES + 4096), encoding="utf-8")

    all_files, edited_files = describe_project_files(project_dir)
    described = {entry["name"]: entry for entry in all_files}
    assert len(edited_files) >= 5
    assert described["untouched.txt"]["change"] == "unchanged"
    assert described["solver.py"]["change"] == "modified"
    assert described["solver.py"]["added_lines"] >= 2
    assert described["solver.py"]["removed_lines"] >= 1
    assert described["notes.md"]["change"] == "created"

    code_view = read_file_view(project_dir, project["id"], "solver.py")
    assert code_view["kind"] == "text"
    assert code_view["language"] == "python"
    assert code_view["change"] == "modified"
    assert code_view["diff"]["has_diff"] is True
    assert any(line["type"] == "add" for line in code_view["diff"]["lines"])
    assert any(line["type"] == "del" for line in code_view["diff"]["lines"])

    md_view = read_file_view(project_dir, project["id"], "notes.md")
    assert md_view["kind"] == "markdown"
    assert "$E = mc^2$" in md_view["content"]
    assert md_view["diff"]["has_diff"] is True

    csv_view = read_file_view(project_dir, project["id"], "grid.csv")
    assert csv_view["kind"] == "table"
    assert csv_view["table"]["headers"] == ["n", "err"]
    assert csv_view["table"]["rows"] == [["16", "0.04"], ["32", "0.01"]]

    img_view = read_file_view(project_dir, project["id"], "plot.png")
    assert img_view["kind"] == "image"
    assert "plot.png" in img_view["preview_url"]

    bin_view = read_file_view(project_dir, project["id"], "raw.bin")
    assert bin_view["kind"] == "binary"
    assert "content" not in bin_view

    huge_view = read_file_view(project_dir, project["id"], "huge.log")
    assert huge_view["kind"] == "text"
    assert huge_view["truncated"] is True
    assert len(huge_view["content"].encode("utf-8")) <= MAX_INLINE_BYTES


def test_file_content_http_endpoint_and_hosted_isolation(tmp_path: Path):
    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    project = app.workspace.create({"name": "HTTP Viewer"})
    project_dir = app.workspace.directory(project["id"])
    (project_dir / "files/report.md").write_text(
        "# Report\n\nAll checks passed.\n", encoding="utf-8"
    )
    # Also create a simulation workspace artifact to test source="simulation"
    sim_dir = project_dir / "simulations/001-demo"
    sim_work = sim_dir / "workspace"
    sim_work.mkdir(parents=True)
    (sim_dir / "request.json").write_text(
        '{"id": "001-demo", "name": "Demo run", "work_directory": "' + str(sim_work) + '"}',
        encoding="utf-8",
    )
    (sim_work / "metrics.json").write_text('{"l2_error": 1e-4}\n', encoding="utf-8")

    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False) as c:
            res = c.get(
                "/api/workspace/file-content",
                params={"id": project["id"], "path": "report.md"},
            )
            assert res.status_code == 200
            body = res.json()
            assert body["kind"] == "markdown"
            assert "All checks passed." in body["content"]

            sim_res = c.get(
                "/api/workspace/file-content",
                params={
                    "id": project["id"],
                    "path": "metrics.json",
                    "source": "simulation",
                    "simulation": "001-demo",
                },
            )
            assert sim_res.status_code == 200
            assert '"l2_error"' in sim_res.json()["content"]

            traversal = c.get(
                "/api/workspace/file-content",
                params={"id": project["id"], "path": "../project.json"},
            )
            assert traversal.status_code == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
