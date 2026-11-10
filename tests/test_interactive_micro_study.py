from __future__ import annotations

import json
from pathlib import Path

import pytest

from conjecture_solver.research_service import put
from conjecture_solver.web.activity import describe_tool
from conjecture_solver.web.micro_study import (
    IndependentReviewSpec,
    MicroStudySpec,
)
from conjecture_solver.web.workspace import Workspace


def test_micro_study_and_review_spec_validation():
    spec = MicroStudySpec(
        question="Does CFL=0.45 conserve total mass to 1e-12?",
        success_criteria="Run 3 grid sizes and verify mass conservation drift <= 1e-12.",
        minutes=10,
    )
    assert spec.minutes == 10.0
    assert spec.completion_policy == "answer"

    with pytest.raises(ValueError):
        MicroStudySpec(
            question="Too long budget",
            success_criteria="Valid criteria string",
            minutes=120,
        )

    rev = IndependentReviewSpec(
        claim="Mass drift is below 1e-14 across all three grids.",
        evidence_files=["results.json"],
    )
    assert rev.evidence_files == ["results.json"]


def test_describe_tool_recognizes_micro_study_and_review():
    ms = describe_tool("run_micro_study", {"question": "Test dispersion relation"})
    assert ms["label"] == "Running micro-study"
    assert ms["detail"] == "Test dispersion relation"

    rv = describe_tool("review_work", {"claim": "Energy error < 1e-6"})
    assert rv["label"] == "Independent review"
    assert rv["detail"] == "Energy error < 1e-6"


def test_review_work_freezes_files_and_records_verdict(tmp_path: Path, monkeypatch):
    workspace = Workspace(tmp_path / ".workspace")
    workspace.save_api({"base_url": "http://127.0.0.1:9999/v1"})
    project = workspace.create({"name": "Audit project"})
    workspace.select_agent(project["id"], {"backend": "builtin", "model": "test-reviewer"})
    project_dir = workspace.directory(project["id"])
    (project_dir / "files/metrics.json").write_text('{"l2_error": 0.0012, "grid": 32}\n')

    def fake_run_agent(prompt, root, config, **kwargs):
        assert kwargs.get("judge") is True
        assert kwargs.get("review_root") == root
        assert "metrics.json" in prompt
        return json.dumps(
            {
                "status": "needs_controls",
                "summary": (
                    "Single grid resolution 32 is insufficient to establish convergence rate."
                ),
                "missing_controls": ["Run N=64 and N=128 grid convergence check"],
                "unverified_assumptions": ["Assumed smooth periodic initial data"],
            }
        )

    monkeypatch.setattr("conjecture_solver.web.micro_study.run_agent", fake_run_agent)
    result = workspace.review_work(
        project["id"],
        {
            "claim": "Second-order L2 convergence is established.",
            "evidence_files": ["metrics.json"],
            "criteria": "Require at least three grid resolutions.",
        },
    )
    assert result["status"] == "needs_controls"
    assert "metrics.json" in result["evidence_manifest"]
    report_path = project_dir / "files" / result["report_file"]
    assert report_path.is_file()
    assert "Single grid resolution 32" in report_path.read_text()

    with pytest.raises(ValueError, match="inside this project's files"):
        workspace.review_work(
            project["id"],
            {
                "claim": "Traversal attempt",
                "evidence_files": ["../project.json"],
            },
        )


def test_run_micro_study_materializes_and_exports_summary(tmp_path: Path, monkeypatch):
    workspace = Workspace(tmp_path / ".workspace")
    workspace.save_api({"base_url": "http://127.0.0.1:9999/v1"})
    project = workspace.create({"name": "Micro-study project"})
    workspace.select_agent(project["id"], {"backend": "builtin", "model": "test-model"})
    project_dir = workspace.directory(project["id"])
    (project_dir / "files/solver.py").write_text("print('ok')\n")

    class DummyCampaign:
        def close(self):
            pass

    def fake_start_managed_campaign(plan):
        root = Path(plan.output_directory)
        (root / "supervisor").mkdir(parents=True, exist_ok=True)
        put(
            root / "supervisor/state.json",
            {"status": "completed", "activity": "Finished", "updated_at": 100.0},
        )
        put(
            root / "research_report.json",
            {"summary": "Verified solver.py across all requested test points."},
        )
        (root / "STUDY_LEDGER.md").write_text("# Study Ledger\n\nAll checks passed.\n")
        return DummyCampaign()

    monkeypatch.setattr(
        "conjecture_solver.mvp_launch.start_managed_campaign",
        fake_start_managed_campaign,
    )
    result = workspace.run_micro_study(
        project["id"],
        {
            "question": "Does solver.py pass the 3-point verification check?",
            "success_criteria": "All 3 points complete with zero error.",
            "minutes": 5,
            "input_files": ["solver.py"],
            "wait": True,
        },
    )
    assert result["status"] == "completed"
    assert result["report"]["summary"] == "Verified solver.py across all requested test points."
    summary_path = project_dir / "files" / result["summary_file"]
    assert summary_path.is_file()
    text = summary_path.read_text()
    assert "Verified solver.py across all requested test points." in text
    assert result["study_link"] in text

    loaded = workspace.project(project["id"])
    assert len(loaded["studies"]) == 1
    assert loaded["studies"][0]["micro_study"] is True


@pytest.fixture
def review_api():
    from tests.test_workspace_protocol import api

    yield from api.__wrapped__()


@pytest.mark.parametrize("reviewer_model", ["", "alternate-api-model"])
def test_cli_review_uses_endpoint_model_and_frozen_text(
    tmp_path, monkeypatch, review_api, reviewer_model
):
    from conjecture_solver.web import micro_study
    from tests.test_workspace_protocol import response

    url, requests, replies = review_api
    workspace = Workspace(tmp_path / ".workspace")
    workspace.save_api({"base_url": url})
    project = workspace.create({"name": "Review snapshot"})
    monkeypatch.setattr(
        workspace,
        "project_connection",
        lambda _: {
            "backend": "grok",
            "model": "native-model",
        },
    )
    monkeypatch.setattr(workspace, "models", lambda backend: {"default": "api-reviewer"})
    project_id = project["id"]
    evidence = workspace.directory(project_id) / "files/evidence.txt"
    evidence.write_text("original measurement")
    freeze = micro_study.freeze_file

    def freeze_then_update(root, source):
        frozen = freeze(root, source)
        source.write_text("new measurement")
        return frozen

    monkeypatch.setattr(micro_study, "freeze_file", freeze_then_update)
    replies.append(
        response(
            text=json.dumps(
                dict(
                    status="accepted",
                    summary="The supplied measurement supports the stated claim.",
                )
            )
        )
    )
    result = workspace.review_work(
        project_id,
        {
            "claim": "The original measurement was recorded.",
            "evidence_files": ["evidence.txt"],
            "reviewer_model": reviewer_model,
        },
    )
    assert result["status"] == "accepted"
    assert len(requests) == 1 and requests[0]["model"] == (reviewer_model or "api-reviewer")
    assert requests[0]["tool_choice"] == "auto"
    packet = workspace.directory(project_id) / "reviews" / result["review_id"] / "packet.json"
    assert (
        json.loads(packet.read_text())["inline_sources"]["evidence.txt"] == "original measurement"
    )
    assert "new measurement" not in json.dumps(requests)


def test_background_study_link_and_final_summary_survive_restart(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from conjecture_solver.web.application import SimjectureWebApplication

    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    workspace = app.workspace
    workspace.save_api({"base_url": "http://127.0.0.1:9999/v1"})
    project = workspace.create(
        {
            "name": "Background study",
            "agent": {
                "backend": "builtin",
                "model": "test-model",
            },
        }
    )

    def start(plan):
        root = Path(plan.output_directory)
        (root / "supervisor").mkdir(exist_ok=True)
        put(root / "supervisor/state.json", {"status": "running"})
        return SimpleNamespace(close=lambda: None)

    monkeypatch.setattr("conjecture_solver.mvp_launch.start_managed_campaign", start)
    result = Workspace(workspace.root).run_micro_study(
        project["id"],
        {
            "question": "Does the measurement match the reference?",
            "success_criteria": "Measure the difference.",
            "minutes": 5,
            "wait": False,
        },
    )
    root = Path(result["path"])
    assert app.resolve_campaign(result["campaign"]) == root
    summary = workspace.directory(project["id"]) / "files" / result["summary_file"]
    assert "`running`" in summary.read_text()
    assert (root / result["study_link"].partition("/")[2]).is_file()
    put(root / "research_report.json", {"summary": "The measurement matches the reference."})
    put(root / "supervisor/state.json", {"status": "completed"})
    Workspace(workspace.root).deliver_study_reports()
    assert "`completed`" in summary.read_text()
    assert "The measurement matches" in summary.read_text()
    assert workspace.project(project["id"])["studies"][0]["summary_status"] == "completed"
    put(root / "research_report.json", {"summary": "The final ledger was flushed."})
    workspace.deliver_study_reports()
    assert "The final ledger was flushed." in summary.read_text()
