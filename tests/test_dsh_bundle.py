from __future__ import annotations

import json
import re
from pathlib import Path

BUNDLE = Path(__file__).parents[1] / "integrations" / "dsh"


def test_dsh_bundle_pins_the_resumable_driver_and_native_mcp_client() -> None:
    package = json.loads((BUNDLE / "package.json").read_text())
    assert package["name"] == "@simjecture/dsh-bundle"
    assert package["version"] == "0.2.0-rc.2"
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
    assert "runner.js" in package["files"]
    assert "adjudicator.js" in package["files"]


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
    assert "simjecture_adjudicate" in patch
    assert "mcp__simjecture__finalize_campaign" in patch
    assert "id: compaction-basic" in patch
    assert "provider: deepseek-official" in patch
    assert "model: deepseek-v4-flash" in patch
    assert "thresholdRatio: 0.5" in patch
    assert "retainRatio: 0.03" in patch


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
    assert "chain-of-thought" in adjudicator
    assert "event.data.arguments" not in adjudicator
    assert "prepared.truncated === true" in adjudicator

    runner = (BUNDLE / "runner.js").read_text()
    assert "agentCtx.tools.restrict" in runner
    assert "INTERNAL_TOOL_NAMES" in runner


def test_dsh_readme_documents_provisioning_pack_install_and_dump_config() -> None:
    readme = (BUNDLE / "README.md").read_text().lower()
    for phrase in ("uv sync --extra dsh", "npm pack", "install", "dump-config"):
        assert phrase in readme
    assert "warpx" in readme
    assert "does not install" in readme or "neither runtime" in readme
