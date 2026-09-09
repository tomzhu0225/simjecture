from __future__ import annotations

import asyncio
import json

import pytest

from conjecture_solver.oneshot import _read_arguments, _run, build_parser


def test_arguments_file_requires_an_object(tmp_path):
    path = tmp_path / "arguments.json"
    path.write_text(json.dumps({"view": "summary"}))
    assert _read_arguments(path) == {"view": "summary"}
    path.write_text(json.dumps(["not", "an", "object"]))
    with pytest.raises(ValueError, match="JSON object"):
        _read_arguments(path)


def test_list_mode_does_not_require_a_tool(tmp_path):
    args = build_parser().parse_args(["--workspace", str(tmp_path), "--list"])
    assert args.list_tools is True
    assert args.tool is None


def test_readiness_failure_does_not_create_a_campaign(tmp_path, monkeypatch):
    monkeypatch.setattr("conjecture_solver.oneshot.shutil.which", lambda _: None)
    workspace = tmp_path / "uncreated"
    args = build_parser().parse_args(["--workspace", str(workspace), "--probe"])
    assert asyncio.run(_run(args)) == {
        "ready": False,
        "sandbox": "bubblewrap",
        "reason": "bwrap is not installed",
    }
    assert not workspace.exists()


def test_real_campaign_assignment_survives_process_reopen(tmp_path, monkeypatch):
    from conjecture_solver.mcp_server import CampaignMCPBridge

    original_open = CampaignMCPBridge._open_kernel

    async def offline_open(bridge):
        kernel = await original_open(bridge)
        kernel.host.literature_search = None
        return kernel

    monkeypatch.setattr(CampaignMCPBridge, "_open_kernel", offline_open)
    hypothesis = tmp_path / "hypothesis.txt"
    hypothesis.write_text("The numerical experiment conserves its declared invariant.")
    workspace = tmp_path / "campaigns"
    base = ["--workspace", str(workspace), "--campaign", "shared"]

    def call(flags):
        return asyncio.run(_run(build_parser().parse_args([*base, *flags])))

    snapshot = call(["--hypothesis-file", str(hypothesis), "snapshot"])
    assert snapshot["hypothesis"] == hypothesis.read_text()
    assert snapshot["terminal_report"] is None
    spec = {
        "assignment_id": "falsify-1",
        "agent_id": "grok-worker",
        "role": "falsifier",
        "claim_id": "claim_root",
        "max_operations": 3,
    }
    spec_file = tmp_path / "assignment.json"
    spec_file.write_text(json.dumps(spec))
    issued = call(["--issue-assignment-file", str(spec_file)])
    assert issued["spec"] == spec
    identity = [
        "--assignment-id",
        "falsify-1",
        "--agent-id",
        "grok-worker",
        "--session-id",
        "task-1",
    ]
    tools = call([*identity, "--list"])
    assert "record_adjudication" not in {tool["name"] for tool in tools["tools"]}
    resumed = call([*identity, "snapshot"])
    assert resumed["role_assignments"][0]["sessions"] == ["task-1"]
    args_file = tmp_path / "args.json"
    args_file.write_text(
        json.dumps(
            {
                "operation_id": "falsify-1:instrument",
                "claim_id": "claim_instrument",
                "kind": "instrument",
                "relation": "instrument_of",
                "parent_id": "claim_root",
                "statement": "The numerical instrument reproduces the exact constant solution.",
                "rationale": "Commission the instrument before a decisive scientific test.",
            }
        )
    )
    registered = call([*identity, "--arguments-file", str(args_file), "register_claim"])
    assert call([*identity, "--arguments-file", str(args_file), "register_claim"]) == registered
    after_replay = call([*identity, "snapshot"])
    assert after_replay["role_assignments"][0]["operations_used"] == 1
    assert after_replay["role_assignments"][0]["children"] == ["claim_instrument"]
    args_file.write_text(
        json.dumps(
            {
                "operation_id": "falsify-1:close",
                "claim_id": "claim_root",
                "status": "supported",
                "reason": "The agent says it is supported.",
            }
        )
    )
    with pytest.raises(ValueError, match="independent judge"):
        call([*identity, "--arguments-file", str(args_file), "close_claim"])
    handoff = tmp_path / "handoff.json"
    handoff.write_text(
        json.dumps(
            {
                "assignment_id": "falsify-1",
                "claim_id": "claim_root",
                "outcome": "inconclusive",
                "evidence_paths": [],
                "next_test": "Commission the instrument before claiming evidence.",
            }
        )
    )
    call([*identity, "--handoff-file", str(handoff)])
    recovered = call(["snapshot"])
    assert recovered["role_assignments"][0]["handoff"]["outcome"] == "inconclusive"
    assert not (workspace / "shared" / "mvp_report.json").exists()


def test_truncated_judge_packet_is_refused_before_review(tmp_path, monkeypatch):
    from conjecture_solver.mcp_server import CampaignMCPBridge

    async def clipped_packet(bridge, name, args):
        assert name == "prepare_adjudication"
        return {"packet": {"evidence": "clipped"}, "case_sha256": "0" * 64}

    monkeypatch.setattr(CampaignMCPBridge, "call_tool", clipped_packet)
    hypothesis = tmp_path / "hypothesis.txt"
    hypothesis.write_text("The numerical experiment conserves its declared invariant.")
    arguments = tmp_path / "arguments.json"
    arguments.write_text(
        json.dumps(
            {
                "operation_id": "judge-1",
                "claim_id": "claim_root",
                "contract_version": 1,
                "case_for_sufficiency": "The frozen evidence is ready for independent review.",
            }
        )
    )
    parsed = build_parser().parse_args(
        [
            "--workspace",
            str(tmp_path / "campaign"),
            "--hypothesis-file",
            str(hypothesis),
            "--arguments-file",
            str(arguments),
            "prepare_adjudication",
        ]
    )
    with pytest.raises(ValueError, match="truncated in transport"):
        asyncio.run(_run(parsed))
