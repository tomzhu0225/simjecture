"""Conversation storage must handle multibyte titles and existing long IDs."""

import json
import os
import re
from datetime import date

import pytest

from conjecture_solver.web import workspace as module
from conjecture_solver.web.workspace import Workspace, private_json


@pytest.mark.parametrize(
    "name",
    [
        "研究" * 80,
        "a" * 63 + "中文研究",
        "𠮷" * 80,
        "请你根据本地的多个聊天记录，帮我梳理一下本月我的主要工作，下周要进行月度汇报，"
        "最好是图片，易展示，梳理有几个不同的工作分支，进展如何",
    ],
    ids=["chinese", "mixed-boundary", "four-byte-unicode", "reported-title"],
)
def test_new_conversations_with_multibyte_titles_can_send(tmp_path, monkeypatch, name):
    workspace = Workspace(tmp_path / ".workspace")
    config = {"backend": "codex", "model": "fixture"}
    monkeypatch.setattr(workspace, "project_connection", lambda _: config)
    monkeypatch.setattr(workspace, "inventory_context", lambda: "Test inventory")
    monkeypatch.setattr(module, "spawn", lambda *args: {})
    first = workspace.create({"name": name})
    second = workspace.create({"name": name})
    assert first["name"] == second["name"] == name
    assert first["id"] != second["id"]
    for conversation in (first, second):
        assert len(os.fsencode(conversation["id"])) <= 80
        workspace.send(conversation["id"], {"message": name})
        assert workspace.project(conversation["id"])["messages"][0]["content"] == name
    connections = list((workspace.root / "turn-connections").iterdir())
    assert len(connections) == 2
    assert all(json.loads(path.read_text()) == config for path in connections)


def test_existing_long_conversation_can_send_without_moving_files(tmp_path, monkeypatch):
    workspace = Workspace(tmp_path / ".workspace")
    name = "研究" * 40
    conversation = workspace.create({"name": name})
    original = workspace.directory(conversation["id"])
    legacy_id = f"{date.today().isoformat()}-{name[:65]}"
    directory = original.with_name(legacy_id)
    original.rename(directory)
    record = json.loads((directory / "project.json").read_text())
    record["id"] = legacy_id
    (directory / "project.json").write_text(json.dumps(record))
    (directory / "files/keep.txt").write_text("Existing result")
    config = {"backend": "codex", "model": "fixture"}
    monkeypatch.setattr(workspace, "project_connection", lambda _: config)
    monkeypatch.setattr(workspace, "inventory_context", lambda: "Test inventory")
    monkeypatch.setattr(module, "spawn", lambda *args: {})
    workspace.send(legacy_id, {"message": "Continue the existing conversation."})
    assert workspace.directory(legacy_id) == directory
    assert (directory / "files/keep.txt").read_text() == "Existing result"
    assert workspace.project(legacy_id)["messages"][0]["content"].startswith("Continue")


def test_private_json_supports_full_length_filenames_and_private_permissions(tmp_path):
    limit = os.pathconf(tmp_path, "PC_NAME_MAX")
    target = tmp_path / ("x" * (limit - len(".json")) + ".json")
    private_json(target, {"version": 1})
    private_json(target, {"version": 2})
    assert json.loads(target.read_text()) == {"version": 2}
    assert target.stat().st_mode & 0o777 == 0o600
    assert list(tmp_path.iterdir()) == [target]


def test_private_json_failure_preserves_original_and_removes_temporary_file(tmp_path):
    target = tmp_path / "connection.json"
    private_json(target, {"version": 1})
    before = target.read_bytes()
    with pytest.raises(TypeError):
        private_json(target, {"bad": object()})
    assert target.read_bytes() == before
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("name", ["English research title", "!!!", "中文研究", "a" * 160])
def test_names_remain_valid_identifiers(tmp_path, name):
    conversation = Workspace(tmp_path / ".workspace").create({"name": name})
    assert re.fullmatch(r"[\w-]{1,100}", conversation["id"])
    assert conversation["name"] == name
