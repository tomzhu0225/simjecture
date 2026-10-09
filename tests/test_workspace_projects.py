"""Workspace separation, durable grouping and immutable research context."""

import base64
import hashlib
import json
import threading
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from conjecture_solver.cli import build_parser
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server
from conjecture_solver.workspace_projects import WorkspaceDirectory


@pytest.fixture
def spaces(tmp_path):
    return WorkspaceDirectory(tmp_path)


def test_default_is_the_existing_workspace_with_no_migration(spaces):
    workspace = spaces.open()
    conversation = workspace.create({"name": "Existing question"})
    before = (workspace.directory(conversation["id"]) / "project.json").read_bytes()
    spaces.create({"id": "lab", "name": "Example laboratory"})
    assert spaces.open().root == spaces.root / ".workspace"
    assert spaces.open("lab").projects() == []
    assert (workspace.directory(conversation["id"]) / "project.json").read_bytes() == before
    assert workspace.freeze_context(conversation["id"], spaces.root / "unused") is None
    assert not (spaces.root / "unused").exists()


def test_workspace_selection_is_explicit_and_settings_stay_separate(spaces):
    spaces.create({"id": "lab", "name": "Example laboratory"})
    personal, lab = spaces.open(), spaces.open("lab")
    p = personal.create({"name": "Shared name"})
    q = lab.create({"name": "Shared name"})
    assert p["id"] == q["id"]  # Identical opaque IDs do not imply shared storage.
    personal.save_collection({"name": "Only here"})
    assert not lab.collections()
    assert personal.settings_path != lab.settings_path
    assert personal.machine_registry.root != lab.machine_registry.root
    assert personal.directory(p["id"]) != lab.directory(q["id"])
    assert spaces.open() is personal


def test_group_and_move_keep_paths_and_existing_study_bytes(spaces):
    workspace = spaces.open()
    conversation = workspace.create({"name": "A question"})
    path = workspace.directory(conversation["id"])
    evidence = path / "studies" / "previous" / "result.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text('{"accepted":false}')
    group = workspace.save_collection({"name": "Investigation", "instructions": "Check units."})
    moved = workspace.assign_collection(conversation["id"], group["id"])
    assert moved["collection"] == group["id"]
    assert workspace.collection(group["id"])["conversations"] == [conversation["id"]]
    workspace.assign_collection(conversation["id"], None)
    assert workspace.collection(group["id"])["conversations"] == []
    assert evidence.read_text() == '{"accepted":false}'
    assert workspace.directory(conversation["id"]) == path


def test_context_revisions_are_frozen_and_explicitly_not_evidence(spaces, tmp_path):
    workspace = spaces.open()
    group = workspace.save_collection(
        {"name": "Generic device", "instructions": "Test the baseline."}
    )
    conversation = workspace.create({"name": "Compare candidates", "collection": group["id"]})
    workspace.collection_file(
        {
            "id": group["id"],
            "name": "inputs/reference.txt",
            "content": base64.b64encode(b"baseline A").decode(),
        }
    )
    first = workspace.freeze_context(conversation["id"], tmp_path / "first")
    workspace.save_collection({"id": group["id"], "instructions": "Test an alternative."})
    workspace.collection_file(
        {
            "id": group["id"],
            "name": "inputs/reference.txt",
            "content": base64.b64encode(b"baseline B").decode(),
        }
    )
    second = workspace.freeze_context(conversation["id"], tmp_path / "second")
    assert first["revision"] != second["revision"]
    assert (tmp_path / "first/files/inputs/reference.txt").read_bytes() == b"baseline A"
    assert first["files"][0]["sha256"] == hashlib.sha256(b"baseline A").hexdigest()
    assert first["project"]["instructions"] == "Test the baseline."
    assert first["evidence_status"] == "context_only"
    assert "not accepted evidence" in workspace.context_prompt(first, "project_context")
    with pytest.raises(FileExistsError):
        workspace.freeze_context(conversation["id"], tmp_path / "first")


@pytest.mark.parametrize("bad", ["../other", "/tmp", "", None, ["lab"]])
def test_invalid_workspace_id_never_falls_back_to_personal(spaces, bad):
    with pytest.raises(ValueError):
        spaces.open(bad)


def test_context_rejects_symlinks_and_upload_escape(spaces, tmp_path):
    workspace = spaces.open()
    group = workspace.save_collection({"name": "Generic device"})
    with pytest.raises(ValueError):
        workspace.collection_file({"id": group["id"], "name": "../../outside", "content": "WA=="})
    outside = tmp_path / "private.txt"
    outside.write_text("Not selected for this project")
    (workspace.collection_path(group["id"]) / "files" / "linked").symlink_to(outside)
    assert "symbolic links" in workspace.collection(group["id"])["context_error"]
    assert len(workspace.collections()) == 1  # Invalid context does not disable the workspace.
    conversation = workspace.create({"name": "Blocked snapshot", "collection": group["id"]})
    with pytest.raises(ValueError, match="symbolic links"):
        workspace.freeze_context(conversation["id"], tmp_path / "blocked")


def test_cli_uses_same_records_without_a_server(spaces, capsys, tmp_path):
    parser = build_parser()

    def call(kind, *words, space="personal"):
        args = parser.parse_args(
            [kind, "--runs-root", str(spaces.root), "--workspace", space, *words]
        )
        assert args.handler(args) == 0
        return json.loads(capsys.readouterr().out)

    call("workspace", "create", "--name", "Generic lab", "--id", "lab")
    project = call("project", "create", "--name", "Field study", space="lab")
    conversation = call(
        "conversation",
        "create",
        "--name",
        "Check reference",
        "--project",
        project["id"],
        space="lab",
    )
    reference = tmp_path / "reference.txt"
    reference.write_text("Private test fixture")
    call("project", "add-file", project["id"], str(reference), space="lab")
    result = call(
        "project",
        "snapshot",
        "--conversation",
        conversation["id"],
        "--output",
        str(tmp_path / "snapshot"),
        space="lab",
    )
    assert result["project"]["id"] == project["id"]
    assert call("conversation", "list") == []
    assert call("project", "show", project["id"], space="lab")["conversations"] == [
        conversation["id"]
    ]


def test_http_scope_download_and_readonly(spaces):
    app = SimjectureWebApplication(runs_root=spaces.root)
    app.workspaces.create({"name": "Generic lab", "id": "lab"})
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False
        ) as client:
            token = client.get("/api/workspace/bootstrap").json()["control_token"]
            headers = {"X-Simjecture-Token": token}
            url = "/api/workspace/collections?workspace=lab"
            group = client.post(url, json={"name": "Private group"}, headers=headers).json()
            assert client.get("/api/workspace/bootstrap").json()["collections"] == []
            assert (
                client.get("/api/workspace/bootstrap?workspace=lab").json()["collections"][0][
                    "name"
                ]
                == "Private group"
            )
            assert client.get("/api/workspace/bootstrap?workspace=unknown").status_code == 400
            assert client.get("/api/workspace/collection?id=" + group["id"]).status_code == 400
            assert (
                client.post(
                    "/api/workspace/collection-file?workspace=lab",
                    headers=headers,
                    json={"id": group["id"], "name": "reference.json", "content": "e30="},
                ).status_code
                == 200
            )
            response = client.get(
                f"/api/workspace/collection-download?workspace=lab&id={group['id']}&path=reference.json"
            )
            assert response.content == b"{}"
            assert response.headers["content-disposition"].startswith("attachment")
            app.allow_mutations = False
            assert client.post(url, json={"name": "Blocked"}, headers=headers).status_code == 403
    finally:
        server.shutdown()
        server.server_close()


def test_context_reaches_fresh_and_resumed_agent_turns(spaces, monkeypatch):
    from conjecture_solver.web import workspace as module
    from conjecture_solver.workspace_sessions import save_session

    workspace = spaces.open()
    config = {
        "backend": "builtin",
        "model": "fixture",
        "base_url": "http://127.0.0.1:1/v1",
        "api_key": "fixture",
    }
    monkeypatch.setattr(workspace, "project_connection", lambda _: config)
    monkeypatch.setattr(workspace, "inventory_context", lambda: "Generic test inventory")
    monkeypatch.setattr(module, "spawn", lambda *args: {})
    project = workspace.save_collection(
        {"name": "Study group", "instructions": "Check the calibration."}
    )
    conversation = workspace.create({"name": "Investigate", "collection": project["id"]})
    directory = workspace.directory(conversation["id"])
    workspace.send(conversation["id"], {"message": "Read the reference inputs."})
    first = sorted((directory / "turns").iterdir())[0]
    before = (first / "prompt.txt").read_bytes()
    assert "Check the calibration." in before.decode()
    assert (first / "project-context/context.json").is_file()
    save_session(directory, config, cursor="existing-session")
    workspace.save_collection(
        {"id": project["id"], "instructions": "Check the revised calibration."}
    )
    workspace.send(conversation["id"], {"message": "Continue."})
    latest = sorted((directory / "turns").iterdir())[-1]
    assert "existing session" in (latest / "prompt.txt").read_text()
    assert "Check the revised calibration." in (latest / "prompt.txt").read_text()
    assert (first / "prompt.txt").read_bytes() == before
    workspace.assign_collection(conversation["id"], None)
    workspace.send(conversation["id"], {"message": "An independent question."})
    latest = sorted((directory / "turns").iterdir())[-1]
    assert "no shared project" in (latest / "prompt.txt").read_text()


def test_autonomous_launch_freezes_context_and_keeps_registered_owner(spaces, monkeypatch):
    from conjecture_solver import execution, mvp_launch

    pytest.importorskip("smolagents")
    app = SimjectureWebApplication(runs_root=spaces.root)
    app.workspaces.create({"id": "lab", "name": "Generic lab"})
    workspace = app.workspaces.open("lab")
    config = {
        "backend": "builtin",
        "model": "fixture",
        "base_url": "http://127.0.0.1:1/v1",
        "api_key": "fixture",
    }
    monkeypatch.setattr(workspace, "project_connection", lambda _: config)
    monkeypatch.setattr(execution, "require_execution_backend", lambda _: {"available": True})
    monkeypatch.setattr(
        mvp_launch, "start_managed_campaign", lambda _: SimpleNamespace(close=lambda: None)
    )
    project = workspace.save_collection(
        {"name": "Reference study", "instructions": "Keep the unit system explicit."}
    )
    conversation = workspace.create({"name": "Test the reference", "collection": project["id"]})
    workspace.collection_file(
        {"id": project["id"], "name": "reference.txt", "content": "b3JpZ2luYWw="}
    )
    workspace.save_brief(
        conversation["id"],
        {
            "question": "The reference is accurate.",
            "success_criteria": "Numerical controls.",
            "constraints": "Generic fixture.",
            "hours": 0.05,
            "completion_policy": "answer",
        },
    )
    result = workspace.launch(
        conversation["id"],
        {"request_key": "first", "execution_backend": "process-cooperative"},
        app,
    )
    root = Path(result["path"])
    assert "Keep the unit system explicit." in (root / "operator_input/instruction.txt").read_text()
    snapshot = root / "research/project_context"
    assert (snapshot / "files/reference.txt").read_text() == "original"
    manifest = json.loads((snapshot / "context.json").read_text())
    workspace.collection_file(
        {"id": project["id"], "name": "reference.txt", "content": "cmV2aXNlZA=="}
    )
    assert (snapshot / "files/reference.txt").read_text() == "original"
    assert manifest["evidence_status"] == "context_only"
    assert app.workspace_context(result["campaign"], root)["workspace"] == "lab"
    assert app.workspace_context(result["campaign"], root)["project_id"] == conversation["id"]
