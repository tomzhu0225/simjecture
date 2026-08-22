from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from conjecture_solver.cli import build_parser
from conjecture_solver.web.application import (
    SimjectureWebApplication,
    WebApplicationError,
)
from conjecture_solver.web.server import create_server


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n")


def _campaign(root: Path) -> Path:
    root.mkdir(parents=True)
    _write_json(
        root / "mvp_manifest.json",
        {
            "schema_version": "0.1.0",
            "hypothesis": "An absolute scale cannot change the bounded pattern outcome.",
            "campaign_instruction": "Use a converged finite-domain test.",
            "config": {"max_wall_seconds": 1800},
        },
    )
    (root / "workspace").mkdir()
    (root / "workspace" / "result.json").write_text('{"pattern": true}\n')
    (root / "workspace" / "figure.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><circle r="2"/></svg>\n'
    )
    (root / "workspace" / "report.html").write_text("<script>alert('no')</script>\n")
    claims = [
        {
            "id": "claim_root",
            "statement": "An absolute scale cannot change the bounded pattern outcome.",
            "kind": "scientific",
            "relation": "root",
            "parent_id": None,
            "status": "falsified",
            "rationale": "Operator supplied root.",
            "evidence_contracts": [
                {
                    "version": 1,
                    "observable": "Pattern measure.",
                    "decision_rule": "Falsify when outcomes separate.",
                }
            ],
            "evidence": [
                {
                    "path": "result.json",
                    "note": "The outcomes separate.",
                    "observation_sufficient": True,
                }
            ],
            "closed_reason": "A counterexample was observed.",
        },
        {
            "id": "claim_child",
            "statement": "Discrete modes make the absolute scale observable.",
            "kind": "scientific",
            "relation": "refines",
            "parent_id": "claim_root",
            "status": "supported",
            "evidence_contracts": [],
            "evidence": [],
        },
        {
            "id": "claim_diagnostic",
            "statement": "The diagnostic resolves the separating mode.",
            "kind": "diagnostic",
            "relation": "diagnostic_of",
            "parent_id": "claim_child",
            "status": "supported",
            "evidence_contracts": [],
            "evidence": [],
        },
    ]
    _write_json(
        root / "hypothesis_ledger.json",
        {
            "schema_version": "0.2.0",
            "root_hypothesis": claims[0]["statement"],
            "claims": claims,
        },
    )
    (root / "transcript.jsonl").write_text(
        json.dumps(
            {
                "kind": "assistant",
                "iteration": 1,
                "model": "test-model",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
                "content": json.dumps(
                    {
                        "action": "list_claims",
                        "research_note": "Inspect the hypothesis tree.",
                    }
                ),
            }
        )
        + "\n"
    )
    _write_json(
        root / "mvp_report.json",
        {
            "schema_version": "0.3.0",
            "hypothesis": claims[0]["statement"],
            "campaign_instruction": "Use a converged finite-domain test.",
            "status": "completed",
            "final_answer": "The bounded root hypothesis is falsified.",
            "iterations": 1,
            "elapsed_wall_seconds": 42.0,
            "workspace_artifacts": {"result.json": "sha"},
            "claim_ledger": {"claims": claims},
            "open_claim_ids": [],
            "closed_claim_ids": ["claim_root", "claim_child", "claim_diagnostic"],
            "finish_claim_notes": ["all claims closed"],
        },
    )
    return root


def test_web_projection_reuses_hypothesis_and_validation_semantics(tmp_path: Path) -> None:
    root = _campaign(tmp_path / "run")
    application = SimjectureWebApplication(
        initial_run=root,
        scan_roots=(tmp_path,),
        runs_root=tmp_path / "new-runs",
    )
    token = application.initial_campaign
    assert token is not None

    payload = application.campaign_snapshot(token)
    assert not payload["snapshot"]["identity"]["run_directory"].startswith("/")
    graph = payload["hypothesis_graph"]
    assert [node["id"] for node in graph["nodes"]] == ["claim_root", "claim_child"]
    assert graph["edges"] == [
        {"source": "claim_root", "target": "claim_child", "relation": "refines"}
    ]
    assert payload["validation_claims"]["claim_child"] == ["claim_diagnostic"]
    assert (
        payload["claim_details"]["claim_root"]["evidence"][0]["artifact_path"]
        == "workspace/result.json"
    )
    assert payload["snapshot"]["token_usage"]["total_tokens"] == 120
    assert payload["snapshot"]["execution_status"] == "terminal"
    artifacts = {item["path"]: item for item in payload["artifacts"]}
    assert artifacts["workspace/result.json"]["claimed_by"] == ["claim_root"]
    assert artifacts["workspace/figure.svg"]["preview"] == "image"
    assert payload["controls"]["read_only_reason"] is None


def test_web_artifacts_are_contained_and_symlinks_are_rejected(tmp_path: Path) -> None:
    root = _campaign(tmp_path / "run")
    application = SimjectureWebApplication(initial_run=root, scan_roots=(tmp_path,))
    token = application.initial_campaign
    assert token is not None

    resource = application.artifact(token, "workspace/result.json")
    assert resource.path.read_text() == '{"pattern": true}\n'
    with pytest.raises(WebApplicationError, match="invalid artifact path"):
        application.artifact(token, "../outside.txt")

    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n")
    (root / "workspace" / "escape.txt").symlink_to(outside)
    with pytest.raises(WebApplicationError, match="symbolic-link"):
        application.artifact(token, "workspace/escape.txt")


def test_read_only_web_application_rejects_mutations(tmp_path: Path) -> None:
    root = _campaign(tmp_path / "run")
    application = SimjectureWebApplication(
        initial_run=root,
        scan_roots=(tmp_path,),
        allow_mutations=False,
    )
    with pytest.raises(WebApplicationError, match="read-only"):
        application.create_campaign({"hypothesis": "A test hypothesis."})
    token = application.initial_campaign
    assert token is not None
    assert application.campaign_snapshot(token)["controls"] == {
        "can_pause": False,
        "can_resume": False,
        "can_cancel": False,
        "read_only_reason": "this web session is read-only",
    }


def test_create_campaign_uses_structured_launch_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from conjecture_solver.web import application as web_application

    captured: dict[str, Any] = {}

    def materialize(request: Any) -> object:
        captured["request"] = request
        output = Path(request.output_directory)
        output.mkdir(parents=True)
        (output / "operator_input").mkdir()
        (output / "operator_input" / "hypothesis.txt").write_text(request.hypothesis)
        return SimpleNamespace(output_directory=str(output))

    class FakeCampaign:
        identity = SimpleNamespace(pid=4321)

        def close(self) -> None:
            captured["closed"] = True

    monkeypatch.setattr(web_application, "materialize_operator_input", materialize)
    monkeypatch.setattr(web_application, "start_managed_campaign", lambda plan: FakeCampaign())
    application = SimjectureWebApplication(
        scan_roots=(tmp_path / "empty",),
        runs_root=tmp_path / "runs",
    )
    result = application.create_campaign(
        {
            "hypothesis": "A bounded hypothesis is falsifiable.",
            "instruction": "Prefer the installed numerical skill.",
            "campaign_id": "campaign-web-test",
            "max_wall_seconds": 1800,
            "max_command_seconds": 120,
            "max_workspace_mb": 256,
            "max_memory_mb": 2048,
        }
    )
    request = captured["request"]
    assert request.hypothesis == "A bounded hypothesis is falsifiable."
    assert request.instruction == "Prefer the installed numerical skill."
    assert request.campaign_id == "campaign-web-test"
    assert request.max_command_seconds == 120
    assert captured["closed"] is True
    assert result["pid"] == 4321
    assert application.registry.resolve(result["campaign"]).name == "campaign-web-test"


def test_create_campaign_rejects_invalid_operator_fields(tmp_path: Path) -> None:
    application = SimjectureWebApplication(
        scan_roots=(tmp_path / "empty",),
        runs_root=tmp_path / "runs",
    )
    with pytest.raises(WebApplicationError, match="campaign id") as caught:
        application.create_campaign(
            {
                "hypothesis": "A bounded hypothesis.",
                "campaign_id": "../escape",
            }
        )
    assert caught.value.status == 400


def test_local_http_api_serves_assets_snapshot_and_protects_post(tmp_path: Path) -> None:
    root = _campaign(tmp_path / "run")
    application = SimjectureWebApplication(initial_run=root, scan_roots=(tmp_path,))
    server = create_server(application, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with httpx.Client(base_url=base, timeout=5) as client:
            home = client.get("/")
            assert home.status_code == 200
            assert "Simjecture" in home.text
            assert "default-src 'self'" in home.headers["content-security-policy"]
            assert client.get("/assets/app.js").status_code == 200

            bootstrap = client.get("/api/bootstrap").json()
            token = bootstrap["selected_campaign"]
            assert bootstrap["control_token"]
            snapshot = client.get("/api/snapshot", params={"campaign": token})
            assert snapshot.status_code == 200
            assert snapshot.json()["snapshot"]["phase"] == "completed"

            artifact = client.get(
                "/api/artifact",
                params={"campaign": token, "path": "workspace/result.json"},
            )
            assert artifact.status_code == 200
            assert artifact.json() == {"pattern": True}
            assert "script-src 'none'" in artifact.headers["content-security-policy"]

            html_artifact = client.get(
                "/api/artifact",
                params={"campaign": token, "path": "workspace/report.html"},
            )
            assert html_artifact.status_code == 200
            assert html_artifact.headers["content-disposition"].startswith("attachment;")

        with httpx.Client(base_url=base, timeout=5) as client:
            rejected = client.post(
                "/api/campaigns",
                headers={"Content-Type": "application/json"},
                json={"hypothesis": "No token should mean no launch."},
            )
            assert rejected.status_code == 403
            assert rejected.json()["error"] == "invalid control token"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_web_cli_contract() -> None:
    args = build_parser().parse_args(
        [
            "web",
            "artifacts/demo",
            "--scan-root",
            "demos",
            "--runs-root",
            "artifacts",
            "--port",
            "0",
            "--no-open",
            "--read-only",
        ]
    )
    assert args.command == "web"
    assert args.run_directory == "artifacts/demo"
    assert args.scan_root == ["demos"]
    assert args.port == 0
    assert args.no_open is True
    assert args.read_only is True


def test_web_server_rejects_non_loopback_bind(tmp_path: Path) -> None:
    application = SimjectureWebApplication(scan_roots=(tmp_path,))
    with pytest.raises(ValueError, match="localhost only"):
        create_server(application, host="0.0.0.0", port=0)
