"""Small client for a host-issued scientific assignment, with replay-safe request names.

This removes transport bookkeeping, not scientific choices or kernel validation.
It is a convenience adapter for trusted local agents, not an OS security boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .mcp_schemas import TOOL_SCHEMAS
from .role_assignments import ROLE_TOOLS


class ResearchClient:
    def __init__(self, binding: str | Path):
        self.binding_path = Path(binding).resolve()
        self.binding = json.loads(self.binding_path.read_text())
        self.root = self.binding_path.parent
        self.requests = self.root / ".client-requests"
        self.requests.mkdir(exist_ok=True)

    def prepare(self, tool: str, arguments: dict[str, Any], *, request_key: str | None = None):
        if tool not in ROLE_TOOLS[self.binding["role"]]:
            raise ValueError(f"Assigned researcher cannot call {tool}")
        args = json.loads(json.dumps(arguments, allow_nan=False))
        props = TOOL_SCHEMAS[tool]["properties"]
        if "active_claim_id" in props:
            args.setdefault("active_claim_id", self.binding["claim_id"])
        if "research_note" in props:
            args.setdefault("research_note", f"Researcher requested {tool}.")
        if tool == "read_skill" and args.get("path") is None:
            args.pop("path", None)
        if "operation_id" in props and "operation_id" not in args:
            # Identical requests replay. A named repetition gets a different key.
            raw = json.dumps(
                [tool, args, request_key], sort_keys=True, separators=(",", ":"), allow_nan=False
            )
            args["operation_id"] = (
                self.binding["assignment_id"]
                + ":client-"
                + hashlib.sha256(raw.encode()).hexdigest()[:24]
            )
        return args

    def call(
        self, tool: str, arguments: dict[str, Any] | None = None, *, request_key: str | None = None
    ):
        args = self.prepare(tool, arguments or {}, request_key=request_key)
        encoded = json.dumps(args, sort_keys=True, allow_nan=False)
        path = self.requests / (hashlib.sha256((tool + encoded).encode()).hexdigest() + ".json")
        path.write_text(encoded + "\n")
        b = self.binding
        command = [
            b.get("python", sys.executable),
            "-m",
            "conjecture_solver.oneshot",
            "--workspace",
            str(Path(b["campaign"]).parent),
            "--campaign",
            Path(b["campaign"]).name,
            "--assignment-id",
            b["assignment_id"],
            "--agent-id",
            b["agent_id"],
            "--session-id",
            b["session_id"],
            tool,
            "--arguments-file",
            str(path),
        ]
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        completed = subprocess.run(command, capture_output=True, text=True, env=env)
        payload = json.loads(completed.stdout)
        (path.with_suffix(".response.json")).write_text(json.dumps(payload, indent=2) + "\n")
        if completed.returncode or not payload.get("ok"):
            raise RuntimeError(payload.get("error") or completed.stderr or "Kernel call failed")
        return payload["result"]

    def write(self, path: str, content: str, *, request_key: str | None = None):
        return self.call(
            "write_workspace_file", {"path": path, "content": content}, request_key=request_key
        )

    def run_python(self, argv, *, inputs, claim_id=None, request_key=None):
        """Bind automatic retry identity to the current source and contract revision."""
        active = claim_id or self.binding["claim_id"]
        claim = self.call("claims", {"view": "role", "claim_ids": [active]})["claims"][0]
        versions = [c["version"] for c in claim.get("evidence_contracts", [])]
        source_hash = None
        if argv and not argv[0].startswith("-"):
            source_hash = self.call("read_workspace_file", {"path": argv[0]})["sha256"]
        identity = json.dumps(
            {
                "request_key": request_key,
                "program_sha256": source_hash,
                "contract_version": max(versions, default=0),
            },
            sort_keys=True,
        )
        return self.call(
            "run_python",
            {"argv": list(argv), "input_artifacts": inputs, "active_claim_id": active},
            request_key=identity,
        )

    def request_review(self, stage: str, claim_id: str | None = None, **arguments):
        names = {
            "contract": "contract-review-request.json",
            "qualification": "qualification-review-request.json",
            "scientific": "review-request.json",
        }
        if stage not in names:
            raise ValueError("Unknown review stage")
        payload = {"claim_id": claim_id or self.binding["claim_id"], **arguments}
        allowed = (
            {"claim_id"}
            if stage != "scientific"
            else {"claim_id", "contract_version", "case_for_sufficiency"}
        )
        if set(payload) != allowed:
            raise ValueError(f"Review request requires {sorted(allowed)}")
        path = self.root / names[stage]
        if path.exists() and json.loads(path.read_text()) != payload:
            raise ValueError("Pending request differs; let the host consume it before replacing")
        path.write_text(json.dumps(payload, indent=2) + "\n")
        return {"queued": str(path), "decision": "pending"}
