"""Artifact placement is a persistent launch contract, including legacy resumes."""

import argparse
import json
import sys

import pytest

from conjecture_solver.research_service import ResearchService
from conjecture_solver.study import configure_parser
from conjecture_solver.study_launch import NativeStudyRequest, materialize_native, resume_native


def request(tmp_path, **values):
    return NativeStudyRequest(
        hypothesis="Synthetic artifact placement.",
        campaign_id="artifact-policy",
        output_directory=str(tmp_path / "study"),
        backend="codex",
        model="test-model",
        agent_executable=sys.executable,
        capability_directory="none",
        max_wall_seconds=300,
        **values,
    )


@pytest.mark.parametrize("policy", [None, "remote", "eager"])
def test_launch_and_resume_preserve_policy(tmp_path, monkeypatch, policy):
    import conjecture_solver.execution as execution

    monkeypatch.setattr(execution, "require_execution_backend", lambda _: {"available": True})
    plan = materialize_native(request(tmp_path, artifact_policy=policy))
    service = ResearchService(plan.output_directory)
    assert service.artifact_policy() == (policy or "remote")
    if policy:
        assert plan.argv[plan.argv.index("--artifact-policy") + 1] == policy
    assert resume_native(service.root).request.artifact_policy == policy
    assert materialize_native(request(tmp_path), resume=True).request.artifact_policy == policy
    alternate = "eager" if policy != "eager" else "remote"
    with pytest.raises(ValueError, match="differs"):
        materialize_native(request(tmp_path, artifact_policy=alternate), resume=True)
    with pytest.raises(ValueError, match="immutable"):
        ResearchService.create(
            service.root, service.manifest["hypothesis"], artifact_policy=alternate
        )


def test_historical_launch_without_policy_stays_eager(tmp_path, monkeypatch):
    import conjecture_solver.execution as execution

    monkeypatch.setattr(execution, "require_execution_backend", lambda _: {"available": True})
    plan = materialize_native(request(tmp_path))
    service = ResearchService(plan.output_directory)
    for filename, nested in [("research.json", False), ("study-launch.json", True)]:
        path = service.root / filename
        record = json.loads(path.read_text())
        (record["request"] if nested else record).pop("artifact_policy")
        path.write_text(json.dumps(record))
    assert resume_native(service.root).request.artifact_policy is None
    assert materialize_native(request(tmp_path), resume=True).request.artifact_policy is None
    assert (
        ResearchService.create(service.root, service.manifest["hypothesis"]).artifact_policy()
        == "eager"
    )
    parser = argparse.ArgumentParser()
    configure_parser(parser)
    assert parser.parse_args(["--campaign", str(service.root)]).artifact_policy is None
    assert (
        parser.parse_args(
            ["--campaign", str(service.root), "--artifact-policy", "remote"]
        ).artifact_policy
        == "remote"
    )
