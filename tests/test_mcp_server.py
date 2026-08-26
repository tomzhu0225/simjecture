from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from conjecture_solver.campaign_jobs import CampaignLockBusyError
from conjecture_solver.mcp_schemas import (
    MUTATING_TOOLS,
    TOOL_REQUIRED,
    TOOL_SCHEMAS,
    tool_definitions,
    validate_catalog,
    validate_schema_subset,
)
from conjecture_solver.mcp_server import (
    BridgeConfig,
    CampaignMCPBridge,
    MCPBridgeError,
    MCPInputError,
    _mcp_error_payload,
)


class _FakeKernel:
    def __init__(self) -> None:
        self.actions: list[tuple[dict[str, Any], int]] = []
        self.jobs: list[dict[str, Any]] = []

    def snapshot(self) -> dict[str, Any]:
        return {"campaign": "fake", "claims": []}

    def execute(
        self,
        action: dict[str, Any],
        *,
        iteration: int = 0,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        self.actions.append((dict(action), iteration))
        return {"accepted": action["action"], "iteration": iteration}

    def execute_operation(
        self,
        operation_id: str,
        action: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        del timeout_seconds
        self.actions.append((dict(action), 1))
        if action["action"] == "cancel_job":
            return self.cancel_job(action["job_id"])
        return {
            "accepted": action["action"],
            "operation_id": operation_id,
            "iteration": 1,
        }

    def start_job(self, request: dict[str, Any]) -> dict[str, Any]:
        self.jobs.append(dict(request))
        return {"job_id": "job_fake", "status": "queued"}

    def job_status(self, job_id: str) -> dict[str, Any]:
        return {"job_id": job_id, "status": "succeeded"}

    def job_report(self, job_id: str) -> dict[str, Any]:
        return {"job_id": job_id, "status": "succeeded", "diagnostic": "bounded"}

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        return {"job_id": job_id, "status": "cancel_requested"}

    def prepare_adjudication(self, operation_id: str, **kwargs: Any) -> dict[str, Any]:
        return {"operation_id": operation_id, "prepared": kwargs["claim_id"]}

    def record_adjudication(self, operation_id: str, **kwargs: Any) -> dict[str, Any]:
        return {
            "operation_id": operation_id,
            "decision": kwargs["verdict"]["decision"],
        }

    def finalize_campaign(self, operation_id: str, **kwargs: Any) -> dict[str, Any]:
        return {"operation_id": operation_id, "final_answer": kwargs["final_answer"]}


def _call(bridge: CampaignMCPBridge, name: str, arguments: dict[str, Any] | None = None) -> Any:
    return asyncio.run(bridge.call_tool(name, arguments))


def test_tool_catalog_is_flat_and_uses_only_the_dsh_schema_subset() -> None:
    validate_catalog()
    expected = {
        "snapshot",
        "claims",
        "register_claim",
        "register_evidence_contract",
        "link_claim_evidence",
        "close_claim",
        "list_skills",
        "read_skill",
        "materialize_skill",
        "search_literature",
        "read_workspace_file",
        "write_workspace_file",
        "list_workspace_files",
        "run_python",
        "run_workbench_capability",
        "run_evidence_capability",
        "job_status",
        "cancel_job",
        "prepare_adjudication",
        "record_adjudication",
        "finalize_campaign",
    }
    definitions = tool_definitions()
    assert {definition["name"] for definition in definitions} == expected
    assert "finish" not in TOOL_SCHEMAS
    assert "shell" not in TOOL_SCHEMAS
    for definition in definitions:
        validate_schema_subset(definition["inputSchema"])
        name = definition["name"]
        schema = definition["inputSchema"]
        assert "iteration" not in schema
        if name in MUTATING_TOOLS:
            assert "operation_id" in TOOL_REQUIRED[name]
            assert "operation_id" in schema["required"]
    assert "root" not in TOOL_SCHEMAS["register_claim"]["properties"]["relation"]["enum"]
    assert "repairs" in TOOL_SCHEMAS["register_claim"]["properties"]["relation"]["enum"]
    assert "repair" in TOOL_SCHEMAS["register_claim"]["properties"]
    assert TOOL_SCHEMAS["claims"]["properties"]["view"]["enum"] == [
        "summary",
        "role",
        "full",
    ]
    assert "claim_ids" in TOOL_SCHEMAS["claims"]["properties"]
    assert TOOL_SCHEMAS["snapshot"]["properties"]["view"]["enum"] == [
        "summary",
        "instruction",
        "full",
    ]
    for name in (
        "run_python",
        "run_workbench_capability",
        "run_evidence_capability",
    ):
        assert "input_artifacts" in TOOL_REQUIRED[name]
        assert "input_artifacts" in TOOL_SCHEMAS[name]["required"]


def test_bridge_dispatches_claim_workspace_and_job_tools(tmp_path: Path) -> None:
    kernel = _FakeKernel()
    bridge = CampaignMCPBridge(kernel, config=BridgeConfig(workspace=tmp_path))
    input_artifact = {"path": "runs/source.json", "sha256": "a" * 64}

    assert _call(bridge, "snapshot") == {"campaign": "fake", "claims": []}
    claim_result = _call(
        bridge,
        "register_claim",
        {
            "claim_id": "claim_demo",
            "statement": "A sufficiently long scientific claim.",
            "kind": "scientific",
            "relation": "refines",
            "parent_id": "claim_root",
            "rationale": "A sufficiently long rationale.",
            "operation_id": "claim-demo-1",
        },
    )
    assert claim_result == {
        "accepted": "register_claim",
        "operation_id": "claim-demo-1",
        "iteration": 1,
    }
    assert "iteration" not in kernel.actions[-1][0]
    assert kernel.actions[-1][0]["research_note"] == "DSH MCP tool: register_claim"

    assert _call(bridge, "list_workspace_files") == {
        "accepted": "list_files",
        "iteration": 0,
    }
    assert kernel.actions[-1][0]["path"] == "."

    assert _call(
        bridge,
        "read_workspace_file",
        {
            "path": "guided/program.py",
            "start_line": 81,
            "line_count": 40,
        },
    ) == {
        "accepted": "read_file",
        "iteration": 0,
    }
    assert kernel.actions[-1][0]["path"] == "guided/program.py"
    assert kernel.actions[-1][0]["start_line"] == 81
    assert kernel.actions[-1][0]["line_count"] == 40

    assert _call(
        bridge,
        "run_python",
        {
            "operation_id": "python-probe-1",
            "argv": ["-c", "print('ok')"],
            "input_artifacts": [input_artifact],
            "timeout_seconds": 12,
        },
    ) == {"job_id": "job_fake", "status": "queued"}
    assert kernel.jobs[-1]["kind"] == "python"
    assert kernel.jobs[-1]["operation_id"] == "python-probe-1"
    assert kernel.jobs[-1]["argv"] == ["-c", "print('ok')"]
    assert kernel.jobs[-1]["input_artifacts"] == [input_artifact]
    assert kernel.jobs[-1]["timeout_seconds"] == 12

    _call(
        bridge,
        "run_workbench_capability",
        {
            "operation_id": "workbench-probe-1",
            "capability": "demo",
            "argv": ["demo.py"],
            "input_artifacts": [input_artifact],
        },
    )
    assert kernel.jobs[-1]["kind"] == "capability"
    assert kernel.jobs[-1]["stage"] == "workbench"
    assert kernel.jobs[-1]["input_artifacts"] == [input_artifact]

    _call(
        bridge,
        "run_evidence_capability",
        {
            "operation_id": "capability-probe-1",
            "capability": "demo",
            "argv": ["demo.py"],
            "active_claim_id": "claim_demo",
            "input_artifacts": [],
        },
    )
    assert kernel.jobs[-1]["kind"] == "capability"
    assert kernel.jobs[-1]["stage"] == "evidence"
    assert kernel.jobs[-1]["active_claim_id"] == "claim_demo"
    report = _call(bridge, "job_status", {"job_id": "job_fake"})
    assert report["status"] == "succeeded"
    assert report["diagnostic"] == "bounded"
    state = _call(
        bridge,
        "job_status",
        {"job_id": "job_fake", "report": False},
    )
    assert state == {"job_id": "job_fake", "status": "succeeded"}
    assert (
        _call(
            bridge,
            "cancel_job",
            {"operation_id": "cancel-job-1", "job_id": "job_fake"},
        )["status"]
        == "cancel_requested"
    )


def test_mutation_operation_id_is_forwarded_to_idempotent_kernel_seam(
    tmp_path: Path,
) -> None:
    class _IdempotentKernel(_FakeKernel):
        def __init__(self) -> None:
            super().__init__()
            self.operations: list[tuple[str, dict[str, Any], float | None]] = []

        def execute_operation(
            self,
            operation_id: str,
            action: dict[str, Any],
            *,
            timeout_seconds: float | None = None,
        ) -> dict[str, Any]:
            self.operations.append((operation_id, dict(action), timeout_seconds))
            return {
                "accepted": action["action"],
                "operation_id": operation_id,
            }

    kernel = _IdempotentKernel()
    bridge = CampaignMCPBridge(kernel, config=BridgeConfig(workspace=tmp_path))
    result = _call(
        bridge,
        "register_claim",
        {
            "operation_id": "claim-idempotent-1",
            "claim_id": "claim_demo",
            "statement": "A sufficiently long scientific claim.",
            "kind": "scientific",
            "relation": "refines",
            "parent_id": "claim_root",
            "rationale": "A sufficiently long rationale.",
        },
    )
    assert result == {
        "accepted": "register_claim",
        "operation_id": "claim-idempotent-1",
    }
    assert kernel.operations == [
        (
            "claim-idempotent-1",
            {
                "claim_id": "claim_demo",
                "statement": "A sufficiently long scientific claim.",
                "kind": "scientific",
                "relation": "refines",
                "parent_id": "claim_root",
                "rationale": "A sufficiently long rationale.",
                "research_note": "DSH MCP tool: register_claim",
                "action": "register_claim",
            },
            600.0,
        )
    ]


def test_mcp_lock_contention_has_a_stable_retry_code() -> None:
    payload = _mcp_error_payload(
        CampaignLockBusyError("campaign writer lock is held"),
        tool="job_status",
    )

    assert payload == {
        "error": {
            "code": "campaign_writer_busy",
            "message": "campaign writer lock is held",
        },
        "tool": "job_status",
    }


def test_bridge_dispatches_isolated_adjudication_and_finalization(tmp_path: Path) -> None:
    bridge = CampaignMCPBridge(_FakeKernel(), config=BridgeConfig(workspace=tmp_path))
    common = {
        "operation_id": "judge-root-v1",
        "claim_id": "claim_root",
        "contract_version": 1,
        "case_for_sufficiency": (
            "The complete prospective ensemble passed every registered check."
        ),
    }
    assert _call(bridge, "prepare_adjudication", common)["prepared"] == "claim_root"
    verdict = {
        "claim_id": "claim_root",
        "contract_version": 1,
        "decision": "sufficient",
        "scientific_disposition": "supported",
        "claim_tested": True,
        "contract_preserves_claim_semantics": True,
        "rationale": "The complete bounded evidence package satisfies the contract.",
        "evidence_gaps": [],
        "next_test": None,
    }
    recorded = _call(
        bridge,
        "record_adjudication",
        {
            **common,
            "case_sha256": "a" * 64,
            "verdict": verdict,
            "model": "deepseek-chat",
            "route": "dsh-subagent:deepseek-official",
            "judge_run_id": "judge-session-one",
            "usage": {"totalTokens": 123},
        },
    )
    assert recorded["decision"] == "sufficient"
    finalized = _call(
        bridge,
        "finalize_campaign",
        {
            "operation_id": "finish-root-v1",
            "final_answer": "The bounded claim is supported by the accepted package.",
        },
    )
    assert finalized["operation_id"] == "finish-root-v1"


def test_bridge_rejects_unsafe_or_unexposed_actions(tmp_path: Path) -> None:
    bridge = CampaignMCPBridge(_FakeKernel(), config=BridgeConfig(workspace=tmp_path))
    with pytest.raises(MCPInputError, match="unknown scientific MCP tool"):
        _call(bridge, "finish")
    with pytest.raises(MCPInputError, match="relative workspace"):
        _call(bridge, "read_workspace_file", {"path": "../outside"})
    with pytest.raises(MCPInputError, match="start_line"):
        _call(
            bridge,
            "read_workspace_file",
            {"path": "inside", "start_line": 0, "line_count": 20},
        )
    with pytest.raises(MCPInputError, match="1 to 256"):
        _call(
            bridge,
            "run_python",
            {"operation_id": "empty-python", "argv": [], "input_artifacts": []},
        )
    with pytest.raises(MCPInputError, match="missing required argument.*input_artifacts"):
        _call(
            bridge,
            "run_python",
            {"operation_id": "missing-inputs", "argv": ["-c", "print('x')"]},
        )
    with pytest.raises(MCPInputError, match="64 lowercase hexadecimal"):
        _call(
            bridge,
            "run_python",
            {
                "operation_id": "bad-input-hash",
                "argv": ["-c", "print('x')"],
                "input_artifacts": [{"path": "input.json", "sha256": "A" * 64}],
            },
        )


def test_bridge_bounds_tool_output(tmp_path: Path) -> None:
    class _LargeSnapshot(_FakeKernel):
        def snapshot(self) -> dict[str, str]:
            return {"payload": "x" * 50_000}

    bridge = CampaignMCPBridge(
        _LargeSnapshot(),
        config=BridgeConfig(workspace=tmp_path, max_output_chars=1_024),
    )
    result = _call(bridge, "snapshot")
    assert result["truncated"] is True
    assert len(result["preview"]) < 1_024
    assert len(result["sha256"]) == 64
    assert len(json.dumps(result, separators=(",", ":"))) <= 1_024


def test_snapshot_summary_removes_duplicated_receipt_bulk(tmp_path: Path) -> None:
    instruction = "i" * 9_000
    hypothesis = "h" * 3_000

    class _LargeCampaignSnapshot(_FakeKernel):
        def snapshot(self) -> dict[str, Any]:
            return {
                "hypothesis": hypothesis,
                "manifest": {
                    "schema_version": "0.22.0",
                    "hypothesis": hypothesis,
                    "campaign_instruction": instruction,
                    "config": {"max_wall_seconds": 21_600},
                    "guided_commissioning": {
                        "available": True,
                        "name": "guided-demo",
                        "description": "d" * 2_000,
                        "capability": "qualified-demo",
                        "program_path": "guided/demo.py",
                        "operator_validation": "v" * 2_000,
                        "files": [{"path": "guided/demo.py", "bytes": 100, "sha256": "a" * 64}],
                        "package_sha256": "b" * 64,
                    },
                },
                "claim_ledger": {
                    "schema_version": "0.9.0",
                    "claim_count": 1,
                    "open_count": 1,
                    "claims": [
                        {
                            "id": "claim_root",
                            "kind": "scientific",
                            "relation": "root",
                            "parent_id": None,
                            "status": "open",
                            "statement": hypothesis,
                            "repair": None,
                            "evidence_contract_count": 1,
                            "evidence_count": 1,
                            "decisive_contract_version": None,
                        }
                    ],
                },
                "skill_hashes": {"demo": "c" * 64},
                "capability_hashes": {"qualified-demo": "d" * 64},
                "artifact_provenance": {
                    "schema_version": "0.2.0",
                    "artifact_count": 1,
                    "artifacts_truncated": False,
                    "artifacts": {
                        "runs/result.json": {
                            "bytes": 100,
                            "evidence_eligible": True,
                            "execution_succeeded": True,
                            "command_argv": ["x" * 50_000],
                            "operation_id": "run-one",
                            "job_id": "job_one",
                            "job_status": "succeeded",
                            "input_artifacts_declared": True,
                            "input_artifacts": [
                                {
                                    "path": "runs/source.json",
                                    "sha256": "e" * 64,
                                    "evidence_eligible": False,
                                }
                            ],
                            "input_lineage_eligible": False,
                            "input_lineage_issues": [
                                "input 'runs/source.json' is ineligible"
                            ],
                        }
                    },
                },
                "literature_search_count": 0,
                "literature_searches_truncated": False,
                "literature_searches": [],
                "job_count": 1,
                "jobs_truncated": False,
                "jobs": [
                    {
                        "job_id": "job_one",
                        "operation_id": "run-one",
                        "status": "succeeded",
                    }
                ],
                "budget": {"remaining_wall_seconds": 19_000},
            }

    bridge = CampaignMCPBridge(
        _LargeCampaignSnapshot(),
        config=BridgeConfig(workspace=tmp_path, max_output_chars=20_000),
    )
    summary = _call(bridge, "snapshot")
    assert summary.get("truncated") is not True
    assert summary["view"] == "summary"
    assert summary["hypothesis_truncated"] is True
    assert summary["manifest"]["campaign_instruction_truncated"] is True
    assert summary["claim_ledger"]["claims"][0]["statement_truncated"] is True
    artifact = summary["artifact_provenance"]["artifacts"]["runs/result.json"]
    assert "command_argv" not in artifact
    assert artifact["job_status"] == "succeeded"
    assert artifact["input_artifacts_declared"] is True
    assert artifact["input_artifact_count"] == 1
    assert artifact["input_lineage_eligible"] is False
    assert artifact["input_lineage_issues"] == [
        "input 'runs/source.json' is ineligible"
    ]
    assert "input_artifacts" not in artifact

    exact_instruction = _call(bridge, "snapshot", {"view": "instruction"})
    assert exact_instruction == {
        "view": "instruction",
        "campaign_instruction": instruction,
        "campaign_instruction_truncated": False,
        "campaign_instruction_sha256": hashlib.sha256(instruction.encode()).hexdigest(),
    }
    assert _call(bridge, "snapshot", {"view": "full"})["truncated"] is True


def test_claim_views_project_before_the_output_bound(tmp_path: Path) -> None:
    root_contract = {
        "version": 1,
        "observable": "A bounded observable.",
        "expected_outcomes": "Pass or fail prospectively.",
        "decision_rule": "Reject when the registered threshold is crossed.",
        "required_observation": "One qualified run.",
        "uncertainty_criterion": "Finite uncertainty below the threshold.",
        "inconclusive_conditions": "Missing or invalid diagnostics.",
        "validation_checks": [{"json_path": "checks.valid", "expected_value": True}],
        "execution_binding": {
            "capability": "qualified-simulator",
            "program_path": "guided/sim.py",
            "program_sha256": "a" * 64,
            "commissioning_argv": ["guided/sim.py", "--smoke"],
            "allowed_scientific_argv": [["guided/sim.py", "--science"]],
        },
        "additional_execution_bindings": [],
        "registered_iteration": 1,
    }
    root = {
        "id": "claim_root",
        "statement": "A falsifiable root statement.",
        "kind": "scientific",
        "relation": "root",
        "parent_id": None,
        "status": "open",
        "rationale": "Operator supplied.",
        "repair": None,
        "evidence_contracts": [root_contract],
        "evidence": [
            {
                "path": "runs/result.json",
                "note": "Qualified output.",
                "contract_version": 1,
                "observation_sufficient": True,
                "observation_note": "All registered checks passed.",
                "commissioning_claim_id": "claim_instrument",
                "validation_passed": True,
                "validation_results": [{"unbounded_kernel_detail": "x" * 50_000}],
                "iteration": 4,
                "provenance": {
                    "sha256": "b" * 64,
                    "tracked": True,
                    "evidence_eligible": True,
                    "execution_succeeded": True,
                    "command_argv": ["guided/sim.py", "--science"],
                    "input_artifacts_declared": True,
                    "input_artifacts": [
                        {
                            "path": "runs/source.json",
                            "sha256": "c" * 64,
                            "evidence_eligible": True,
                        }
                    ],
                    "input_lineage_eligible": True,
                    "input_lineage_issues": [],
                },
            }
        ],
        "closed_reason": None,
        "decisive_contract_version": None,
        "created_iteration": 0,
        "updated_iteration": 4,
    }
    instrument = {
        **root,
        "id": "claim_instrument",
        "statement": "The simulator is commissioned.",
        "kind": "instrument",
        "relation": "instrument_of",
        "parent_id": "claim_root",
        "status": "supported",
        "evidence_contracts": [],
        "evidence": [],
    }

    class _LargeLedger(_FakeKernel):
        def execute(
            self,
            action: dict[str, Any],
            *,
            iteration: int = 0,
            **_kwargs: Any,
        ) -> dict[str, Any]:
            self.actions.append((dict(action), iteration))
            if action["action"] == "list_claims":
                return {
                    "claim_ledger": {
                        "schema_version": "0.9.0",
                        "claim_count": 2,
                        "open_count": 1,
                    },
                    "claims": [root, instrument],
                }
            return {"accepted": action["action"], "iteration": iteration}

    kernel = _LargeLedger()
    bridge = CampaignMCPBridge(
        kernel,
        config=BridgeConfig(workspace=tmp_path, max_output_chars=4_096),
    )

    summary = _call(bridge, "claims")
    assert summary["view"] == "summary"
    assert summary["matching_claim_count"] == 2
    assert summary["claims"][0]["evidence_count"] == 1
    assert "evidence" not in summary["claims"][0]

    children = _call(
        bridge,
        "claims",
        {"view": "summary", "parent_id": "CLAIM_ROOT", "limit": 100},
    )
    assert [claim["id"] for claim in children["claims"]] == ["claim_instrument"]

    role = _call(
        bridge,
        "claims",
        {"view": "role", "claim_ids": ["CLAIM_ROOT"]},
    )
    assert role.get("truncated") is not True
    assert (
        role["claims"][0]["evidence_contracts"][0]["execution_binding"]
        == (root_contract["execution_binding"])
    )
    projected_evidence = role["claims"][0]["evidence"][0]
    assert projected_evidence["validation_result_count"] == 1
    assert projected_evidence["validation_results_omitted_count"] == 0
    assert len(projected_evidence["validation_results_sha256"]) == 64
    assert role["claims"][0]["evidence"][0]["provenance"]["command_argv"] == [
        "guided/sim.py",
        "--science",
    ]
    assert projected_evidence["provenance"]["input_artifact_count"] == 1
    assert projected_evidence["provenance"]["input_lineage_eligible"] is True
    assert "input_artifacts" not in projected_evidence["provenance"]

    missing = _call(
        bridge,
        "claims",
        {"view": "role", "claim_ids": ["claim_absent"]},
    )
    assert missing["claims"] == []
    assert missing["missing_claim_ids"] == ["claim_absent"]

    full = _call(
        bridge,
        "claims",
        {"view": "full", "claim_ids": ["claim_root"]},
    )
    assert full["truncated"] is True
    assert kernel.actions[-1][0] == {
        "action": "list_claims",
        "research_note": "DSH MCP tool: list_claims",
    }

    with pytest.raises(MCPInputError, match="requires explicit claim_ids"):
        _call(bridge, "claims", {"view": "role"})
    with pytest.raises(MCPInputError, match="accepts at most 1 claim_ids"):
        _call(
            bridge,
            "claims",
            {"view": "role", "claim_ids": ["claim_root", "claim_instrument"]},
        )
    with pytest.raises(MCPInputError, match="must lie in"):
        _call(bridge, "claims", {"limit": 101})


def test_role_claim_view_keeps_a_long_evidence_tail_under_the_output_bound(
    tmp_path: Path,
) -> None:
    evidence = [
        {
            "path": f"runs/result_{index:02d}.json",
            "note": "Qualified output. " + ("n" * 800),
            "contract_version": 3,
            "observation_sufficient": index >= 18,
            "observation_note": "All registered checks passed. " + ("x" * 800),
            "commissioning_claim_id": None,
            "validation_passed": True,
            "validation_results": [{"detail": "y" * 2_000}],
            "iteration": index,
            "provenance": {
                "sha256": "b" * 64,
                "tracked": True,
                "evidence_eligible": True,
                "execution_succeeded": True,
                "command_argv": ["guided/sim.py", "--science", str(index)],
            },
        }
        for index in range(20)
    ]
    root = {
        "id": "claim_root",
        "statement": "A falsifiable root statement.",
        "kind": "scientific",
        "relation": "root",
        "parent_id": None,
        "status": "open",
        "rationale": "Operator supplied.",
        "repair": None,
        "evidence_contracts": [
            {
                "version": 3,
                "observable": "A bounded observable.",
                "decision_rule": "Reject when the registered threshold is crossed.",
                "validation_checks": [
                    {"json_path": "S_input", "expected_value": 100},
                    {"json_path": "n_dumps", "expected_value": 7},
                    {"json_path": "n_rows", "expected_value": 7},
                ],
                "execution_binding": {},
            }
        ],
        "evidence": evidence,
        "closed_reason": None,
        "decisive_contract_version": None,
        "created_iteration": 0,
        "updated_iteration": 20,
    }

    class _LongLedger(_FakeKernel):
        def execute(
            self,
            action: dict[str, Any],
            *,
            iteration: int = 0,
            **_kwargs: Any,
        ) -> dict[str, Any]:
            del iteration, _kwargs
            if action["action"] == "list_claims":
                return {"claim_ledger": {"schema_version": "0.9.0"}, "claims": [root]}
            return {"accepted": action["action"]}

    bridge = CampaignMCPBridge(
        _LongLedger(),
        config=BridgeConfig(workspace=tmp_path, max_output_chars=30_000),
    )
    role = _call(bridge, "claims", {"view": "role", "claim_ids": ["claim_root"]})
    encoded = json.dumps(role, separators=(",", ":"))
    assert role.get("truncated") is not True
    assert len(encoded) <= 30_000
    assert role["claims"][0]["evidence_count"] == 20
    assert role["claims"][0]["evidence_truncated"] is True
    paths = [item["path"] for item in role["claims"][0]["evidence"]]
    assert "runs/result_18.json" in paths
    assert "runs/result_19.json" in paths
    assert all(len(item["observation_note"]) <= 403 for item in role["claims"][0]["evidence"])


def test_role_claim_view_balances_outcomes_without_reordering_history(
    tmp_path: Path,
) -> None:
    evidence = []
    for index in range(20):
        sufficient = index not in {1, 19}
        contract_version = 1 if index == 0 else 2
        evidence.append(
            {
                "path": f"runs/result_{index:02d}.json",
                "note": f"Observation {index}.",
                "contract_version": contract_version,
                "observation_sufficient": sufficient,
                "observation_note": "qualified" if sufficient else "contradictory",
                "validation_passed": index != 1,
                "validation_results": [
                    {
                        "json_path": "checks.valid",
                        "expected_value": True,
                        "actual_value": index != 1,
                        "passed": index != 1,
                    }
                ],
                "iteration": index,
                "provenance": {
                    "sha256": f"{index:064x}",
                    "tracked": True,
                    "evidence_eligible": True,
                    "execution_succeeded": index != 1,
                    "job_status": "failed" if index == 1 else "succeeded",
                },
            }
        )
    root = {
        "id": "claim_root",
        "statement": "A bounded claim with mixed evidence.",
        "kind": "scientific",
        "relation": "root",
        "parent_id": None,
        "status": "supported",
        "rationale": "Operator supplied.",
        "repair": None,
        "evidence_contracts": [
            {"version": 1, "observable": "Initial decisive observation."},
            {"version": 2, "observable": "Later observations."},
        ],
        "evidence": evidence,
        "closed_reason": "Contract one was decisive.",
        "decisive_contract_version": 1,
        "created_iteration": 0,
        "updated_iteration": 19,
    }

    class _MixedLedger(_FakeKernel):
        def execute(
            self,
            action: dict[str, Any],
            *,
            iteration: int = 0,
            **_kwargs: Any,
        ) -> dict[str, Any]:
            del iteration, _kwargs
            if action["action"] == "list_claims":
                return {"claim_ledger": {"schema_version": "0.9.0"}, "claims": [root]}
            return {"accepted": action["action"]}

    bridge = CampaignMCPBridge(
        _MixedLedger(),
        config=BridgeConfig(workspace=tmp_path, max_output_chars=30_000),
    )
    role = _call(bridge, "claims", {"view": "role", "claim_ids": ["claim_root"]})
    claim = role["claims"][0]
    selected = claim["evidence"]
    iterations = [item["iteration"] for item in selected]

    assert len(selected) == 8
    assert iterations == sorted(iterations)
    assert 0 in iterations  # decisive evidence cannot disappear behind a long tail
    assert 1 in iterations  # failed/contradictory evidence remains visible
    assert 19 in iterations  # the newest observation remains visible
    assert claim["evidence_omitted_count"] == 12
    assert claim["evidence_selection_omissions"]["failed"] == 0
    failed = next(item for item in selected if item["iteration"] == 1)
    assert failed["validation_results"][0]["passed"] is False
    assert len(failed["validation_results_sha256"]) == 64


def test_role_claim_view_adapts_validation_detail_to_the_wire_budget(
    tmp_path: Path,
) -> None:
    contract = {
        "version": 1,
        "observable": "observable " + ("o" * 900),
        "expected_outcomes": "outcomes " + ("e" * 900),
        "decision_rule": "decision " + ("d" * 900),
        "required_observation": "required " + ("r" * 900),
        "uncertainty_criterion": "uncertainty " + ("u" * 900),
        "inconclusive_conditions": "inconclusive " + ("i" * 900),
        "validation_checks": [
            {"json_path": f"checks.check_{index}", "expected_value": True} for index in range(12)
        ],
        "execution_binding": {
            "capability": "qualified-simulator",
            "program_path": "guided/sim.py",
            "program_sha256": "a" * 64,
            "commissioning_argv": ["guided/sim.py", "--commission"],
            "allowed_scientific_argv": [
                ["guided/sim.py", "--science", str(index)] for index in range(7)
            ],
        },
    }
    evidence = []
    for evidence_index in range(7):
        evidence.append(
            {
                "path": f"analysis/result_{evidence_index}.json",
                "note": "Failed prospective observation.",
                "contract_version": 1,
                "observation_sufficient": False,
                "observation_note": "The registered observation was incomplete.",
                "validation_passed": False,
                "validation_results": [
                    {
                        "aspect": "diagnostics",
                        "json_path": f"checks.check_{check_index}",
                        "expected_value": True,
                        "actual_value": False,
                        "passed": False,
                        "error": "registered diagnostic mismatch " + ("x" * 200),
                    }
                    for check_index in range(12)
                ],
                "iteration": evidence_index,
                "provenance": {
                    "sha256": f"{evidence_index:064x}",
                    "tracked": True,
                    "evidence_eligible": True,
                    "execution_succeeded": True,
                    "command_argv": ["guided/sim.py", "--science", str(evidence_index)],
                },
            }
        )
    root = {
        "id": "claim_root",
        "statement": "A claim with a large prospective contract and repeated failed checks.",
        "kind": "scientific",
        "relation": "root",
        "parent_id": None,
        "status": "open",
        "rationale": "Operator supplied.",
        "repair": None,
        "evidence_contracts": [contract],
        "evidence": evidence,
        "closed_reason": None,
        "decisive_contract_version": None,
        "created_iteration": 0,
        "updated_iteration": 7,
    }

    class _GrowingLedger(_FakeKernel):
        def execute(
            self,
            action: dict[str, Any],
            *,
            iteration: int = 0,
            **_kwargs: Any,
        ) -> dict[str, Any]:
            del iteration, _kwargs
            if action["action"] == "list_claims":
                return {"claim_ledger": {"schema_version": "0.9.0"}, "claims": [root]}
            return {"accepted": action["action"]}

    bridge = CampaignMCPBridge(
        _GrowingLedger(),
        config=BridgeConfig(workspace=tmp_path, max_output_chars=30_000),
    )
    role = _call(bridge, "claims", {"view": "role", "claim_ids": ["claim_root"]})
    encoded = json.dumps(role, separators=(",", ":"))
    claim = role["claims"][0]

    assert role.get("truncated") is not True
    assert len(encoded) <= 30_000
    assert claim["evidence_contracts"] == [contract]
    assert len(claim["evidence"]) == 7
    assert all(item["validation_result_count"] == 12 for item in claim["evidence"])
    assert all(item["validation_results_omitted_count"] > 0 for item in claim["evidence"])
    assert all(len(item["validation_results_sha256"]) == 64 for item in claim["evidence"])


def test_bridge_never_retries_a_mutating_kernel_error(tmp_path: Path) -> None:
    class _FailingMutation(_FakeKernel):
        def execute_operation(
            self,
            operation_id: str,
            action: dict[str, Any],
            *,
            timeout_seconds: float | None = None,
        ) -> dict[str, Any]:
            del operation_id, timeout_seconds
            self.actions.append((dict(action), 1))
            raise ValueError("failure after mutation began")

    kernel = _FailingMutation()
    bridge = CampaignMCPBridge(kernel, config=BridgeConfig(workspace=tmp_path))
    with pytest.raises(ValueError, match="failure after mutation began"):
        _call(
            bridge,
            "write_workspace_file",
            {
                "operation_id": "write-probe-1",
                "path": "probe.txt",
                "content": "one invocation",
            },
        )
    assert len(kernel.actions) == 1


def test_bridge_refuses_mutation_without_idempotent_kernel_seam(tmp_path: Path) -> None:
    class _LegacyKernel(_FakeKernel):
        execute_operation = None

    kernel = _LegacyKernel()
    bridge = CampaignMCPBridge(kernel, config=BridgeConfig(workspace=tmp_path))
    with pytest.raises(MCPBridgeError, match="idempotency boundary"):
        _call(
            bridge,
            "write_workspace_file",
            {
                "operation_id": "write-probe-legacy",
                "path": "probe.txt",
                "content": "must not execute",
            },
        )
    assert kernel.actions == []


def test_hypothesis_file_is_forwarded_and_existing_root_is_exactly_guarded(
    tmp_path: Path,
) -> None:
    hypothesis_file = tmp_path / "hypothesis.txt"
    hypothesis_file.write_text("A new host-controlled hypothesis.\n")
    seen: dict[str, Any] = {}

    def factory(**kwargs: Any) -> _FakeKernel:
        seen.update(kwargs)
        return _FakeKernel()

    bridge = CampaignMCPBridge(
        config=BridgeConfig(workspace=tmp_path, hypothesis_file=hypothesis_file),
        kernel_factory=factory,
    )
    _call(bridge, "snapshot")
    assert seen["hypothesis"] == "A new host-controlled hypothesis."

    manifest = tmp_path / "mvp_manifest.json"
    manifest.write_text('{"hypothesis":"Existing immutable root"}')
    with pytest.raises(MCPBridgeError, match="does not exactly match"):
        _call(
            CampaignMCPBridge(
                config=BridgeConfig(workspace=tmp_path, hypothesis_file=hypothesis_file),
                kernel_factory=factory,
            ),
            "snapshot",
        )


def test_relative_campaign_root_is_exactly_guarded(tmp_path: Path) -> None:
    hypothesis_file = tmp_path / "hypothesis.txt"
    hypothesis_file.write_text("A conflicting host hypothesis.\n")
    campaign = tmp_path / "demo"
    campaign.mkdir()
    (campaign / "mvp_manifest.json").write_text('{"hypothesis":"Existing immutable campaign root"}')

    with pytest.raises(MCPBridgeError, match="does not exactly match"):
        _call(
            CampaignMCPBridge(
                config=BridgeConfig(
                    workspace=tmp_path,
                    campaign="demo",
                    hypothesis_file=hypothesis_file,
                ),
                kernel_factory=lambda **_kwargs: _FakeKernel(),
            ),
            "snapshot",
        )


def test_named_campaign_does_not_inherit_parent_workspace_manifest(
    tmp_path: Path,
) -> None:
    (tmp_path / "mvp_manifest.json").write_text('{"hypothesis":"An unrelated parent campaign"}')
    hypothesis_file = tmp_path / "hypothesis.txt"
    hypothesis_file.write_text("The named campaign has its own immutable root.\n")
    seen: dict[str, Any] = {}

    def factory(**kwargs: Any) -> _FakeKernel:
        seen.update(kwargs)
        return _FakeKernel()

    bridge = CampaignMCPBridge(
        config=BridgeConfig(
            workspace=tmp_path,
            campaign="named-campaign",
            hypothesis_file=hypothesis_file,
        ),
        kernel_factory=factory,
    )
    assert _call(bridge, "snapshot")["campaign"] == "fake"
    assert seen["hypothesis"] == "The named campaign has its own immutable root."


def test_operator_launch_and_manifest_hypotheses_are_both_verified(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "demo"
    operator_input = campaign / "operator_input"
    operator_input.mkdir(parents=True)
    hypothesis = "The operator launch root is immutable.\n"
    (operator_input / "hypothesis.txt").write_text(hypothesis)
    (operator_input / "launch.json").write_text(
        json.dumps(
            {
                "hypothesis_file": "hypothesis.txt",
                "hypothesis_sha256": hashlib.sha256(hypothesis.encode()).hexdigest(),
            }
        )
    )
    supplied = tmp_path / "supplied.txt"
    supplied.write_text(hypothesis)
    seen: dict[str, Any] = {}

    def factory(**kwargs: Any) -> _FakeKernel:
        seen.update(kwargs)
        return _FakeKernel()

    _call(
        CampaignMCPBridge(
            config=BridgeConfig(
                workspace=tmp_path,
                campaign="demo",
                hypothesis_file=supplied,
            ),
            kernel_factory=factory,
        ),
        "snapshot",
    )
    assert seen["hypothesis"] == hypothesis.strip()

    (campaign / "mvp_manifest.json").write_text(
        json.dumps({"hypothesis": "A different persisted root"})
    )
    with pytest.raises(MCPBridgeError, match="different root hypotheses"):
        _call(
            CampaignMCPBridge(
                config=BridgeConfig(
                    workspace=tmp_path,
                    campaign="demo",
                    hypothesis_file=supplied,
                ),
                kernel_factory=factory,
            ),
            "snapshot",
        )


def test_startup_fails_before_stdio_when_open_or_snapshot_fails(
    tmp_path: Path,
) -> None:
    class _BrokenSnapshot(_FakeKernel):
        def snapshot(self) -> dict[str, Any]:
            raise RuntimeError("snapshot unavailable")

    with pytest.raises(MCPBridgeError, match="startup/open/snapshot failed"):
        asyncio.run(
            CampaignMCPBridge(
                _BrokenSnapshot(),
                config=BridgeConfig(workspace=tmp_path),
            ).startup()
        )

    def broken_factory(**_kwargs: Any) -> _FakeKernel:
        raise RuntimeError("open unavailable")

    with pytest.raises(MCPBridgeError, match="startup/open/snapshot failed"):
        asyncio.run(
            CampaignMCPBridge(
                config=BridgeConfig(workspace=tmp_path),
                kernel_factory=broken_factory,
            ).startup()
        )


def test_only_one_root_bridge_can_own_a_campaign(tmp_path: Path) -> None:
    hypothesis = tmp_path / "hypothesis.txt"
    hypothesis.write_text("Only one root MCP host may mutate this campaign.\n")
    config = BridgeConfig(workspace=tmp_path, hypothesis_file=hypothesis)
    first = CampaignMCPBridge(config=config)
    second = CampaignMCPBridge(config=config)

    try:
        asyncio.run(first.startup())
        with pytest.raises(MCPBridgeError, match="active campaign"):
            asyncio.run(second.startup())
    finally:
        first.shutdown()

    # Releasing the first process-wide lease makes a clean MCP restart valid.
    asyncio.run(second.startup())
    second.shutdown()


def test_sdk_stdio_handshake_list_and_call_when_sdk_is_installed(tmp_path: Path) -> None:
    pytest.importorskip("mcp.client.stdio")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = Path(__file__).parents[1]
    env = {
        "PYTHONPATH": str(root / "src"),
        "SIMJECTURE_WORKSPACE": str(tmp_path),
        "SIMJECTURE_HYPOTHESIS_FILE": str(tmp_path / "hypothesis.txt"),
    }
    (tmp_path / "hypothesis.txt").write_text(
        "A stdio MCP handshake preserves the scientific tool boundary.\n"
    )
    # The child opens the real model-free kernel, so this verifies the declared
    # stdio entry point and a complete initialize/list/call exchange rather than
    # only invoking an in-process callback.
    parameters = StdioServerParameters(
        command=str(Path(sys.executable)),
        args=["-m", "conjecture_solver.mcp_server"],
        env=env,
        cwd=root,
    )

    async def handshake() -> None:
        # Connect twice to the same trailing-newline hypothesis file.  The
        # first connection creates the canonical launch/manifest; the second
        # is the real restart contract used by DSH reconnects.
        for _attempt in range(2):
            async with (
                stdio_client(parameters) as (read_stream, write_stream),
                ClientSession(read_stream, write_stream) as session,
            ):
                await session.initialize()
                listed = await session.list_tools()
                assert len(listed.tools) == 21
                assert {tool.name for tool in listed.tools} == set(TOOL_SCHEMAS)
                for tool in listed.tools:
                    schema = getattr(
                        tool,
                        "inputSchema",
                        getattr(tool, "input_schema", {}),
                    )
                    assert "iteration" not in schema
                    if tool.name in MUTATING_TOOLS:
                        assert "operation_id" in schema["required"]
                called = await session.call_tool("snapshot", {})
                assert getattr(called, "isError", getattr(called, "is_error", False)) is False
                structured = getattr(
                    called,
                    "structuredContent",
                    getattr(called, "structured_content", {}),
                )
                assert structured["hypothesis"].startswith("A stdio MCP")

    asyncio.run(handshake())
