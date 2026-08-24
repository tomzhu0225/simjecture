from __future__ import annotations

import json
import re
from pathlib import Path

BUNDLE = Path(__file__).parents[1] / "integrations" / "dsh"


def test_dsh_bundle_pins_the_resumable_driver_and_native_mcp_client() -> None:
    package = json.loads((BUNDLE / "package.json").read_text())
    assert package["name"] == "@simjecture/dsh-bundle"
    assert package["version"] == "0.2.2"
    assert package["engines"]["node"] == ">=22.19.0"
    assert package["peerDependencies"] == {"@deepseek-ai/dsh": "0.1.1-rc.2"}
    assert package["dependencies"] == {
        "@deepseek-ai/dsh-agent": "0.1.1-rc.2",
        "@deepseek-ai/dsh-llm": "0.1.1-rc.2",
        "@deepseek-ai/dsh-mcp-client": "0.1.1-rc.2",
        "@deepseek-ai/dsh-session": "0.1.1-rc.2",
    }
    assert "scripts" not in package
    assert "python" not in json.dumps(package).lower()
    assert "warpx" not in json.dumps(package).lower()
    assert package["dsh"]["bundle"]["patch"] == "./cordis.patch.yml"
    assert package["exports"]["./runner"] == "./runner.js"
    assert package["exports"]["./adjudicator"] == "./adjudicator.js"
    assert package["exports"]["./roles"] == "./roles.js"
    assert package["exports"]["./job-waiter"] == "./job-waiter.js"
    assert package["exports"]["./context-elider"] == "./context-elider.js"
    for name in (
        "runner.js",
        "adjudicator.js",
        "roles.js",
        "job-waiter.js",
        "context-elider.js",
    ):
        assert name in package["files"]


def test_dsh_profile_declares_explicit_boundary_and_disables_bypasses() -> None:
    patch = (BUNDLE / "cordis.patch.yml").read_text()
    assert "name: '@deepseek-ai/dsh-mcp-client'" in patch
    assert "serverName: simjecture" in patch
    assert "transport: stdio" in patch
    assert "mode: native" in patch
    assert re.search(r"(?m)^- id: approval\n  config:\n    policy: never$", patch)
    assert "defaultPreset: simjecture" in patch
    assert re.search(
        r"(?m)^      simjecture:\n        sandbox: workspace-write\n"
        r"        approval: never$",
        patch,
    )
    assert "failOnStartupError: true" in patch
    for variable in (
        "SIMJECTURE_WORKSPACE",
        "SIMJECTURE_CAMPAIGN",
        "SIMJECTURE_HYPOTHESIS_FILE",
        "SIMJECTURE_CAPABILITIES",
        "SIMJECTURE_SKILLS",
        "SIMJECTURE_MCP_MAX_OUTPUT_CHARS",
        "SIMJECTURE_MCP_TIMEOUT_SECONDS",
        "SIMJECTURE_DSH_SESSION_ROOT",
    ):
        assert variable in patch
    disabled_model_rows = (
        "tool-bash",
        "tool-pwsh",
        "tool-jobs",
        "tool-fs",
        "tool-fs-search",
        "tool-str-replace-editor",
        "agent-instructions",
        "skill-filesystem",
        "tool-skill",
        "tool-subagent-control",
        "tool-subagent-list-agents",
        "tool-subagent",
        "tool-subagent-fork",
        "tool-subagent-report",
        "workflow-worker-thread",
        "tool-workflow",
        "tool-ralph",
        "tool-web",
        "tool-todo",
        "tool-goal",
    )
    for tool_id in disabled_model_rows:
        assert re.search(
            rf"(?m)^- id: {re.escape(tool_id)}\n  disabled: true$",
            patch,
        )
    assert "mcp__simjecture__finish" not in patch
    assert re.search(r"(?m)^- id: headless-runner\n  disabled: true$", patch)
    assert "name: '@simjecture/dsh-bundle/runner'" in patch
    assert "name: '@simjecture/dsh-bundle/adjudicator'" in patch
    assert "name: '@simjecture/dsh-bundle/roles'" in patch
    assert "name: '@simjecture/dsh-bundle/job-waiter'" in patch
    assert "name: '@simjecture/dsh-bundle/context-elider'" in patch
    assert patch.index("simjecture-job-waiter") < patch.index("simjecture-runner")
    assert patch.index("simjecture-roles") < patch.index("simjecture-runner")
    assert "simjecture_adjudicate" in patch
    assert "simjecture_falsify" in patch
    assert "simjecture_repair" in patch
    assert "mcp__simjecture__finalize_campaign" in patch
    assert "id: compaction-basic" in patch
    assert "provider: deepseek-official" in patch
    assert "model: deepseek-v4-flash" in patch
    assert "thresholdRatio: 0.5" in patch
    assert "retainRatio: 0.03" in patch
    assert "Lead Scientist" in patch
    assert re.search(r"do not run\s+experiments", patch)


def test_dsh_runner_uses_stable_resume_and_projects_no_reasoning_chunks() -> None:
    runner = (BUNDLE / "runner.js").read_text()
    assert "SIMJECTURE_DSH_SESSION_ID" in runner
    assert "agents.resume" in runner
    assert "agents.create" in runner
    assert "sessions.flush" in runner
    assert "llm/retry" in runner
    assert "compaction/summary" in runner
    assert "shadowed_nodes: event.data.shadowedSeqs.length" in runner
    assert "shadowed_tokens: event.data.shadowedTokenCount" in runner
    assert "usage: event.data.usage" in runner
    assert ".slice(0, 500)" in runner
    assert "assistant/chunk" not in runner
    assert "event.data.arguments" not in runner
    assert "block.type === 'tool-result'" in runner
    assert "resultBlock?.isError === true" in runner


def test_dsh_adjudicator_uses_a_fresh_tool_free_structured_child() -> None:
    adjudicator = (BUNDLE / "adjudicator.js").read_text()
    assert "@deepseek-ai/dsh-tools" not in adjudicator
    assert "defineTool" not in adjudicator
    assert "ctx.subagents.start('spawn'" in adjudicator
    assert "outputSchema: VERDICT_SCHEMA" in adjudicator
    assert "toolFilter: { allow: [] }" in adjudicator
    assert "persona: JUDGE_PERSONA" in adjudicator
    assert "mcp__simjecture__prepare_adjudication" in adjudicator
    assert "mcp__simjecture__record_adjudication" in adjudicator
    assert "under 1,200 characters" in adjudicator
    assert "chain-of-thought" in adjudicator
    assert "event.data.arguments" not in adjudicator
    assert "prepared.truncated === true" in adjudicator

    runner = (BUNDLE / "runner.js").read_text()
    assert "agentCtx.tools.restrict" in runner
    assert "LEAD_TOOL_NAMES" in runner


def test_dsh_scientific_roles_are_fresh_scoped_and_durably_verified() -> None:
    roles = (BUNDLE / "roles.js").read_text()
    assert "ctx.subagents.start('spawn'" in roles
    assert "start('fork'" not in roles
    assert "continuable" not in roles
    assert "outputSchema: role === 'falsifier' ? FALSIFIER_SCHEMA : REPAIR_SCHEMA" in roles
    assert "const: null" not in roles
    assert "toolFilter:" in roles
    assert "FALSIFIER_TOOL_NAMES" in roles
    assert "REPAIR_TOOL_NAMES" in roles
    assert "LEAD_TOOL_NAMES" in roles
    assert "child.ctx.tools.guard" in roles
    assert "the Falsifier cannot register scientific claims" in roles
    assert "one scientific repairs child" in roles
    assert "exactRoleClaims" in roles
    assert "view: 'role', claim_ids: [claimId]" in roles
    assert "Request exactly one role claim" in roles
    assert "view: 'summary', parent_id: parentId" in roles
    assert "claimIdsAfter.push(result.structured.child_claim_id)" in roles
    assert "CampaignKernel claim pagination made no progress" in roles
    assert "campaign_instruction_truncated" in roles
    assert "view=instruction" in roles
    assert "verifyFalsifierResult" in roles
    assert "verifyRepairResult" in roles
    assert "await run.dispose()" in roles
    assert "do not repeatedly poll" in roles
    assert "Plain run_python is not a named capability" in roles
    assert "read_workspace_file line windows" in roles
    assert "guided_commissioning" in roles
    assert "guided/protocol.json" in roles
    assert "declaredProtocolPath" in roles
    assert "protocol_path" in roles
    assert "compactGuidedCommissioning" in roles
    assert "assignment.guidedFilePaths.has(path)" in roles
    assert "Agent-authored workspace source may be reread after compaction" in roles
    assert "source reads require explicit start_line and line_count" in roles
    assert "source read overlaps a prior window" in roles
    assert "Never use\nrun_python merely to print or slice a file" in roles
    assert "never reread an overlapping guided-source window" in roles
    assert "reuse the durable contract, evidence, and workspace artifacts" in roles
    assert "Supported or closed commissioning claims are immutable" in roles
    assert "observation_sufficient=true" in roles
    assert "Falsifier adjudication handoff requires durable evidence" in roles
    assert "parent conversation" in roles
    assert "never request an unscoped full ledger" in " ".join(roles.split())
    assert "chain-of-thought" in roles
    assert "event.data.arguments" not in roles


def test_dsh_job_waiter_keeps_polling_below_the_model_surface() -> None:
    waiter = (BUNDLE / "job-waiter.js").read_text()
    assert "ctx.on('tools/execute'" in waiter
    assert waiter.count("await next()") == 1
    assert "exec.parent !== undefined" in waiter
    assert "arguments: { job_id: jobId, report }" in waiter
    assert "readStatus(ctx, exec, jobId, serial, false)" in waiter
    assert "readStatus(ctx, exec, jobId, serial, true)" in waiter
    for status in (
        "queued",
        "running",
        "cancel_requested",
        "succeeded",
        "failed",
        "cancelled",
        "outcome_unknown",
    ):
        assert f"'{status}'" in waiter
    assert "the durable job remains attached" in waiter
    assert "cancel_job" not in waiter
    assert "pause_pending" in waiter


def test_dsh_context_elision_is_age_gated_and_audit_preserving() -> None:
    elider = (BUNDLE / "context-elider.js").read_text()
    assert "ctx.on('agent/pre-step'" in elider
    assert "firstSeen" in elider
    assert "first < state.tick" in elider
    assert "compaction/prune" in elider
    assert "surfaceOp: { op: 'replace'" in elider
    assert "sourceEventSeqs" in elider
    assert "createHash('sha256')" in elider
    assert "Full arguments and results remain in the append-only DSH log" in elider
    assert "completed_tool_unit" in elider
    assert "large_tool_result" in elider
    for tool in (
        "write_workspace_file",
        "run_python",
        "run_workbench_capability",
        "run_evidence_capability",
    ):
        assert tool in elider


def test_dsh_readme_documents_provisioning_pack_install_and_dump_config() -> None:
    readme = (BUNDLE / "README.md").read_text().lower()
    for phrase in ("uv sync --extra dsh", "npm pack", "install", "dump-config"):
        assert phrase in readme
    assert "warpx" in readme
    assert "does not install" in readme or "neither runtime" in readme
