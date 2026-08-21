from __future__ import annotations

import json
import re
from pathlib import Path

BUNDLE = Path(__file__).parents[1] / "integrations" / "dsh"


def test_dsh_bundle_is_patch_only_and_pins_the_native_mcp_client() -> None:
    package = json.loads((BUNDLE / "package.json").read_text())
    assert package["name"] == "@simjecture/dsh-bundle"
    assert package["version"] == "0.2.0-rc.1"
    assert package["engines"]["node"] == ">=22.19.0"
    assert package["peerDependencies"] == {"@deepseek-ai/dsh": "0.1.1-rc.2"}
    assert package["dependencies"] == {
        "@deepseek-ai/dsh-mcp-client": "0.1.1-rc.2"
    }
    assert "scripts" not in package
    assert "python" not in json.dumps(package).lower()
    assert "warpx" not in json.dumps(package).lower()
    assert package["dsh"]["bundle"]["patch"] == "./cordis.patch.yml"


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


def test_dsh_readme_documents_provisioning_pack_install_and_dump_config() -> None:
    readme = (BUNDLE / "README.md").read_text().lower()
    for phrase in ("uv sync --extra dsh", "npm pack", "install", "dump-config"):
        assert phrase in readme
    assert "warpx" in readme
    assert "does not install" in readme or "neither runtime" in readme
