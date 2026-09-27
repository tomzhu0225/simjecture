"""Continuity is scoped to a conversation, model and provider connection."""

import json
import os
import sys
from pathlib import Path

import pytest

from conjecture_solver.web.workspace import Workspace
from conjecture_solver.workspace_agent import run_external
from conjecture_solver.workspace_sessions import load_session, save_session
from tests.test_workspace import connect, wait_for
from tests.test_workspace import provider as protocol_provider


@pytest.fixture
def provider():
    yield from protocol_provider.__wrapped__()


def test_route_change_never_reuses_another_connection(tmp_path):
    config = dict(backend="builtin", model="m1", base_url="https://a.example/v1", api_key="secret")
    save_session(tmp_path, config, history=[{"role": "user", "content": "first"}])
    assert load_session(tmp_path, config)["history"]
    for key, value in [
        ("model", "m2"),
        ("backend", "grok"),
        ("base_url", "https://b.example"),
        ("api_key", "rotated"),
    ]:
        assert not load_session(tmp_path, config | {key: value})
    path = tmp_path / "agent-session.json"
    assert "secret" not in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600
    assert not load_session(tmp_path / "another-project", config)


@pytest.mark.parametrize(
    "backend,flag", [("grok", "--resume"), ("codex", "resume"), ("agy", "--conversation")]
)
def test_native_cli_resumes_same_project_and_model(tmp_path, monkeypatch, backend, flag):
    binary = tmp_path / "bin"
    binary.mkdir()
    command = binary / backend
    command.write_text(
        f"#!{sys.executable}\n"
        + """
import json,sys
from pathlib import Path
args=sys.argv[1:]
Path('argv.json').write_text(json.dumps(args))
model=args[args.index('--model')+1]
session='session-'+model
backend=Path(sys.argv[0]).name
if backend=='codex':
 print(json.dumps({'type':'thread.started','thread_id':session}))
 print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'done'}}))
 print(json.dumps({'type':'turn.completed','usage':{'input_tokens':1,'output_tokens':1}}))
elif backend=='grok':
 print(json.dumps({'type':'result','subtype':'success','session_id':session,'result':'done'}))
else:
 print(json.dumps({'event':'result','result':{'conversation_id':session,'response':'done'}}))
"""
    )
    command.chmod(0o755)
    monkeypatch.setenv("PATH", str(binary) + os.pathsep + os.environ["PATH"])
    w = Workspace(tmp_path / "runs/.workspace")
    project = w.create({"name": "Session test"})
    root = Path(project["files_directory"])
    config = dict(backend=backend, model="m1")
    for number in range(3):
        turn = root.parent / "turns" / str(number)
        turn.mkdir()
        if number == 2:
            config["model"] = "m2"
        assert run_external("Current request", root, config, turn, w) == "done"
        args = json.loads((root / "argv.json").read_text())
        assert (flag in args) == (number == 1)
    assert load_session(root.parent, config)["cursor"] == "session-m2"


def test_api_preserves_structured_history_between_turns(tmp_path, provider):
    url, requests = provider
    w = Workspace(tmp_path / ".workspace")
    connect(w, url)
    requests.clear()
    project = w.create({"name": "API continuity"})
    for message in ["Grill me to prepare a study.", "Grill me to prepare the next step."]:
        w.send(project["id"], {"message": message})
        wait_for(lambda: not w.project(project["id"])["running"])
    assert len(requests) == 2
    assert requests[0]["messages"][0] == requests[1]["messages"][0]
    assert requests[1]["messages"][: len(requests[0]["messages"])] == requests[0]["messages"]
    assert len(requests[1]["messages"]) > len(requests[0]["messages"])
    turns = sorted((w.directory(project["id"]) / "turns").iterdir())
    assert "Previous conversation" in (turns[0] / "prompt.txt").read_text()
    assert "Previous conversation" not in (turns[1] / "prompt.txt").read_text()
