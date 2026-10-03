"""Conversation ownership is a read-only projection, not new scientific state."""

import pytest

from conjecture_solver.research_continuation import preview
from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.workspace import load


def tree_bytes(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def owned_study(tmp_path, monkeypatch):
    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    monkeypatch.setattr(
        app.workspace, "default_agent", lambda: {"backend": "builtin", "model": "fixture"}
    )
    project = app.workspace.create({"name": "Energy conversion investigation"})
    directory = app.workspace.directory(project["id"])
    parent = ResearchService.create(directory / "studies/001-energy", "Account for the energy")
    (parent.work / "calculation.py").write_text("print(1)\n")
    campaign = app.registry.register(parent.root)
    record = {
        "campaign": campaign,
        "campaign_id": "001-energy",
        "path": str(parent.root),
        "question": parent.manifest["hypothesis"],
    }
    put(directory / "project.json", load(directory / "project.json") | {"studies": [record]})
    return app, project["id"], parent, campaign


def test_snapshot_projects_owning_conversation_without_writing(owned_study, tmp_path):
    app, identifier, parent, campaign = owned_study
    path = app.workspace.directory(identifier) / "project.json"
    saved = load(path)
    saved["studies"][0]["report_turn"] = "123456789"
    put(path, saved)
    before = tree_bytes(tmp_path)

    assert app.campaign_snapshot(campaign)["workspace_context"] == {
        "project_id": identifier,
        "project_name": "Energy conversion investigation",
        "campaign": campaign,
        "report_turn": "123456789",
    }
    assert preview(parent.root)["hypothesis"] == parent.manifest["hypothesis"]
    assert tree_bytes(tmp_path) == before
    assert not load(path).get("continuation_draft")


def test_context_survives_restart_and_read_only_session(owned_study, tmp_path):
    app, identifier, parent, campaign = owned_study
    before = tree_bytes(tmp_path)
    restarted = SimjectureWebApplication(
        runs_root=app.runs_root, scan_roots=(tmp_path / "empty",), allow_mutations=False
    )
    payload = restarted.campaign_snapshot(campaign)
    assert payload["workspace_context"]["project_id"] == identifier
    assert "report_turn" not in payload["workspace_context"]
    assert payload["controls"]["read_only_reason"] == "this web session is read-only"
    assert restarted.registry.resolve(campaign) == parent.root
    assert tree_bytes(tmp_path) == before


def test_standalone_snapshot_does_not_create_workspace(tmp_path):
    parent = ResearchService.create(tmp_path / "cli-study", "Standalone question")
    app = SimjectureWebApplication(
        initial_run=parent.root,
        runs_root=tmp_path / "runs",
        scan_roots=(tmp_path,),
        allow_mutations=False,
    )
    before = tree_bytes(tmp_path)
    assert app.campaign_snapshot(app.initial_campaign)["workspace_context"] is None
    assert not app.workspace.root.exists()
    assert tree_bytes(tmp_path) == before


def test_operator_study_added_after_server_start_appears_without_restart(owned_study):
    app, identifier, parent, _campaign = owned_study
    added = ResearchService.create(parent.root.parent / "002-new", "A new operator study")
    p = app.workspace.directory(identifier) / "project.json"
    saved = load(p)
    token = app.registry.token_for(added.root)
    saved["studies"].append(dict(campaign=token, path=str(added.root), question="New study"))
    put(p, saved)
    assert token in {r["id"] for r in app.campaigns()}
    assert app.registry.resolve(token) == added.root


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.pop("studies"),
        lambda p: p.update(studies=None),
        lambda p: p.update(studies=[None, "unexpected", {}]),
        lambda p: p["studies"][0].update(campaign="stale-token"),
        lambda p: p["studies"][0].pop("path"),
        lambda p: p["studies"][0].update(path=123),
        lambda p: p["studies"][0].update(path=p["studies"][0]["path"] + "-missing"),
        lambda p: p.update(id="different-conversation"),
        lambda p: p["studies"].append(dict(p["studies"][0])),
    ],
)
def test_unexpected_study_mappings_do_not_claim_ownership(owned_study, change):
    app, identifier, _, campaign = owned_study
    path = app.workspace.directory(identifier) / "project.json"
    saved = load(path)
    change(saved)
    put(path, saved)
    before = path.read_bytes()
    assert app.campaign_snapshot(campaign)["workspace_context"] is None
    assert path.read_bytes() == before


def test_malformed_project_record_does_not_break_campaign_snapshot(owned_study):
    app, identifier, _, campaign = owned_study
    path = app.workspace.directory(identifier) / "project.json"
    path.write_text("{unfinished")
    assert app.campaign_snapshot(campaign)["workspace_context"] is None
    path.write_text("[]")
    assert app.campaign_snapshot(campaign)["workspace_context"] is None


def test_owned_study_requires_registered_path_and_containment(owned_study, tmp_path):
    app, identifier, parent, campaign = owned_study
    directory = app.workspace.directory(identifier)
    path = directory / "project.json"
    standalone = ResearchService.create(tmp_path / "outside", "Other question")
    standalone_campaign = app.registry.register(standalone.root)
    alias = directory / "studies/002-linked"
    alias.symlink_to(standalone.root, target_is_directory=True)
    saved = load(path)
    saved["studies"].append(
        {"campaign": standalone_campaign, "path": str(alias), "question": "Linked external run"}
    )
    # A real sibling study path is also insufficient if the token maps elsewhere.
    saved["studies"][0]["path"] = str(alias)
    put(path, saved)
    assert app.campaign_snapshot(campaign)["workspace_context"] is None
    assert app.campaign_snapshot(standalone_campaign)["workspace_context"] is None
    saved["studies"][0]["path"] = str(parent.root)
    put(path, saved)
    assert app.campaign_snapshot(campaign)["workspace_context"]["project_id"] == identifier


def test_linked_conversation_directory_does_not_claim_ownership(owned_study, tmp_path):
    app, identifier, parent, campaign = owned_study
    directory = app.workspace.directory(identifier)
    moved = tmp_path / "elsewhere" / identifier
    moved.parent.mkdir()
    directory.rename(moved)
    directory.symlink_to(moved, target_is_directory=True)
    registered = app.registry.register(moved / "studies" / parent.root.name)
    saved = load(moved / "project.json")
    saved["studies"][0].update(campaign=registered, path=str(moved / "studies" / parent.root.name))
    put(moved / "project.json", saved)
    assert app.campaign_snapshot(registered)["workspace_context"] is None
    assert app.workspace.campaign_context(campaign, parent.root) is None


@pytest.mark.parametrize("report_turn", ["../other", "not-a-turn", 123, None])
def test_unexpected_report_turn_is_omitted(owned_study, report_turn):
    app, identifier, _, campaign = owned_study
    path = app.workspace.directory(identifier) / "project.json"
    saved = load(path)
    saved["studies"][0]["report_turn"] = report_turn
    put(path, saved)
    context = app.campaign_snapshot(campaign)["workspace_context"]
    assert context["project_id"] == identifier
    assert "report_turn" not in context


def test_direct_continuation_reuses_owner_without_launching(owned_study):
    app, identifier, parent, campaign = owned_study
    before = tree_bytes(parent.root)
    result = app.workspace.prepare_continuation(
        {
            "campaign": campaign,
            "guidance": "Resolve the boundary flux",
            "hours": 2,
            "files": ["calculation.py"],
        },
        app,
    )
    assert result["project"] == identifier
    assert result["view"] == "autonomous"
    saved = app.workspace.project(identifier)
    assert [p["id"] for p in app.workspace.projects()] == [identifier]
    assert len(saved["studies"]) == 1
    assert saved["continuation_draft"]["parent"] == str(parent.root)
    assert saved["continuation_draft"]["files"] == ["calculation.py"]
    assert saved["brief"]["hours"] == 2
    assert saved["brief"]["constraints"] == "Resolve the boundary flux"
    assert tree_bytes(parent.root) == before


def test_repeated_direct_preparation_keeps_existing_draft(owned_study, tmp_path):
    app, identifier, _, campaign = owned_study
    payload = {"campaign": campaign, "guidance": "First direction", "hours": 2}
    app.workspace.prepare_continuation(payload, app)
    before = tree_bytes(tmp_path)
    for retry in [payload, payload | {"guidance": "Different direction", "hours": 3}]:
        with pytest.raises(ValueError, match="Finish or clear the current proposal"):
            app.workspace.prepare_continuation(retry, app)
        assert tree_bytes(tmp_path) == before
    app.workspace.new_study(identifier)
    assert app.workspace.prepare_continuation(payload, app)["project"] == identifier


def test_busy_owner_is_not_replaced_or_mutated(owned_study, tmp_path, monkeypatch):
    app, identifier, _, campaign = owned_study
    turn = app.workspace.directory(identifier) / "turns/123456789"
    turn.mkdir()
    put(turn / "request.json", {"message": "Working", "created_at": 1})
    put(turn / "process.json", {"fixture": True})
    monkeypatch.setattr("conjecture_solver.web.workspace.alive", lambda record: bool(record))
    before = tree_bytes(tmp_path)
    with pytest.raises(ValueError, match="Wait for the interactive agent"):
        app.workspace.prepare_continuation({"campaign": campaign, "guidance": "Next"}, app)
    assert tree_bytes(tmp_path) == before


def test_existing_proposal_is_not_replaced_or_mutated(owned_study, tmp_path):
    app, identifier, _, campaign = owned_study
    path = app.workspace.directory(identifier) / "project.json"
    put(path, load(path) | {"brief": {"question": "Another investigation"}})
    before = tree_bytes(tmp_path)
    with pytest.raises(ValueError, match="Finish or clear the current proposal"):
        app.workspace.prepare_continuation({"campaign": campaign, "guidance": "Next"}, app)
    assert tree_bytes(tmp_path) == before


def test_legacy_launched_brief_does_not_block_owner_reuse(owned_study):
    app, identifier, parent, campaign = owned_study
    path = app.workspace.directory(identifier) / "project.json"
    brief = {"question": parent.manifest["hypothesis"]}
    put(parent.root / "project-brief.json", brief)
    put(path, load(path) | {"brief": brief})
    assert "brief_launched" not in load(path)
    result = app.workspace.prepare_continuation({"campaign": campaign, "guidance": "Next"}, app)
    assert result["project"] == identifier
    assert load(path)["brief_launched"] is None


def test_agent_preparation_uses_owner(owned_study, monkeypatch):
    app, identifier, parent, campaign = owned_study
    prepared = []
    monkeypatch.setattr(app.workspace, "prepare_continuation_chat", prepared.append)
    result = app.workspace.prepare_continuation({"campaign": campaign, "approach": "agent"}, app)
    assert result["project"] == identifier
    assert result["view"] == "interactive"
    assert prepared == [identifier]
    saved = app.workspace.project(identifier)
    assert saved["continuation_draft"]["parent"] == str(parent.root)
    assert saved["brief"] is None
    assert len(saved["studies"]) == 1


def test_explicit_project_still_takes_precedence(owned_study):
    app, identifier, parent, campaign = owned_study
    other = app.workspace.create({"name": "Explicit target"})["id"]
    owner_before = (app.workspace.directory(identifier) / "project.json").read_bytes()
    result = app.workspace.prepare_continuation(
        {"campaign": campaign, "project": other, "guidance": "Next"}, app
    )
    assert result["project"] == other
    assert app.workspace.project(other)["continuation_draft"]["parent"] == str(parent.root)
    assert (app.workspace.directory(identifier) / "project.json").read_bytes() == owner_before
    assert app.campaign_snapshot(campaign)["workspace_context"]["project_id"] == identifier


def test_standalone_continuation_still_creates_conversation(owned_study, tmp_path):
    app, identifier, _, _ = owned_study
    parent = ResearchService.create(tmp_path / "cli-study", "Standalone question")
    campaign = app.registry.register(parent.root)
    before = tree_bytes(parent.root)
    result = app.workspace.prepare_continuation({"campaign": campaign, "guidance": "Next"}, app)
    assert result["project"] != identifier
    saved = app.workspace.project(result["project"])
    assert saved["name"] == "Continue: Standalone question"
    assert saved["continuation_draft"]["parent"] == str(parent.root)
    assert not saved["studies"]
    assert app.campaign_snapshot(campaign)["workspace_context"] is None
    assert tree_bytes(parent.root) == before


def test_invalid_preparation_does_not_change_owner(owned_study, tmp_path):
    app, _, _, campaign = owned_study
    before = tree_bytes(tmp_path)
    for payload in [{"guidance": ""}, {"guidance": "Next", "hours": 999}, {"files": ["../bad"]}]:
        with pytest.raises(ValueError):
            app.workspace.prepare_continuation({"campaign": campaign} | payload, app)
        assert tree_bytes(tmp_path) == before


def test_missing_ownership_record_does_not_infer_owner_from_folder(owned_study):
    app, identifier, parent, campaign = owned_study
    path = app.workspace.directory(identifier) / "project.json"
    put(path, load(path) | {"studies": []})
    before = path.read_bytes()
    assert app.campaign_snapshot(campaign)["workspace_context"] is None
    result = app.workspace.prepare_continuation({"campaign": campaign, "guidance": "Next"}, app)
    assert result["project"] != identifier
    assert app.workspace.project(result["project"])["continuation_draft"]["parent"] == str(
        parent.root
    )
    assert path.read_bytes() == before


def test_invalid_explicit_project_does_not_fall_back_to_owner(owned_study, tmp_path):
    app, _, _, campaign = owned_study
    before = tree_bytes(tmp_path)
    with pytest.raises(ValueError, match="Unknown project"):
        app.workspace.prepare_continuation(
            {"campaign": campaign, "project": "not-a-project", "guidance": "Next"}, app
        )
    assert tree_bytes(tmp_path) == before
