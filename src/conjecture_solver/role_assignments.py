"""Durable, host-issued scientific assignments shared by agent transports.

The caller must hold the campaign supervisor lease. Identity is supplied by
the supervisor, never by model tool arguments. This is a tool authorization
boundary, not an OS sandbox for a CLI with unrelated shell access.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .mcp_schemas import TOOL_SCHEMAS

READ_TOOLS = frozenset(
    {
        "snapshot",
        "claims",
        "list_skills",
        "read_skill",
        "read_workspace_file",
        "read_workspace_image",
        "list_workspace_files",
        "job_status",
    }
)
ROLE_TOOLS = {
    "lead_scientist": frozenset(
        {"snapshot", "claims", "read_workspace_image", "finalize_campaign"}
    ),
    "falsifier": READ_TOOLS
    | {
        "register_claim",
        "register_evidence_contract",
        "link_claim_evidence",
        "close_claim",
        "materialize_skill",
        "search_literature",
        "write_workspace_file",
        "run_python",
        "run_workbench_capability",
        "run_evidence_capability",
        "cancel_job",
    },
    "repair_scientist": (READ_TOOLS - {"job_status"})
    | {
        "register_claim",
        "register_evidence_contract",
        "search_literature",
    },
    "blocker_resolver": frozenset(
        {
            "snapshot",
            "claims",
            "register_evidence_contract",
            "record_terminal_observation",
            "link_claim_evidence",
        }
    ),
    # The supervisor prepares the case and records the tool-free judge's verdict.
    "judge": frozenset(),
}


def identifier(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ValueError("identity must be 1-128 letters, digits, dots, underscores or hyphens")
    return value


class AssignmentStore:
    def __init__(self, campaign: Path):
        self.path = campaign / "role_assignments.json"
        self.data = (
            json.loads(self.path.read_text())
            if self.path.exists()
            else {
                "schema_version": 1,
                "assignments": {},
            }
        )
        if self.data.get("schema_version") != 1:
            raise ValueError("unsupported assignment schema")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".assignments-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(self.data, stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def issue(self, spec: dict[str, Any]) -> dict[str, Any]:
        required = {"assignment_id", "agent_id", "role", "claim_id", "max_operations"}
        if set(spec) != required:
            raise ValueError(f"assignment requires exactly {sorted(required)}")
        for key in ("assignment_id", "agent_id", "claim_id"):
            identifier(spec[key])
        if spec["role"] not in ROLE_TOOLS:
            raise ValueError("unknown scientific role")
        budget = spec["max_operations"]
        if type(budget) is not int or not 1 <= budget <= 10000:
            raise ValueError("max_operations must be between 1 and 10000")
        existing = self.data["assignments"].get(spec["assignment_id"])
        if existing is not None:
            if existing["spec"] != spec:
                raise ValueError("assignment identity is immutable; issue a new assignment")
            return existing
        if spec["role"] not in {"lead_scientist", "judge"}:
            for item in self.data["assignments"].values():
                if (
                    item["spec"]["claim_id"].casefold() == spec["claim_id"].casefold()
                    and item["spec"]["role"] not in {"lead_scientist", "judge"}
                    and not item.get("handoff")
                ):
                    raise ValueError("claim already has an unfinished scientific assignment")
        record = {"spec": dict(spec), "operations": {}, "children": [], "sessions": []}
        self.data["assignments"][spec["assignment_id"]] = record
        self.save()
        return record

    def bind(self, assignment_id: str, agent_id: str, session_id: str) -> dict[str, Any]:
        identifier(session_id)
        record = self.data["assignments"].get(identifier(assignment_id))
        if record is None or record["spec"]["agent_id"] != agent_id:
            raise ValueError("assignment does not belong to this agent")
        if session_id not in record["sessions"]:
            record["sessions"].append(session_id)
            self.save()
        return record

    def authorize(self, record: dict[str, Any], name: str, args: dict[str, Any]) -> None:
        spec = record["spec"]
        role = spec["role"]
        if name not in ROLE_TOOLS[role]:
            raise ValueError(f"{role} cannot call {name}")
        if record.get("handoff") and name not in READ_TOOLS:
            raise ValueError("assignment has ended; issue a new assignment to continue")
        target = spec["claim_id"].casefold()
        allowed = {target, *record["children"]}
        claim = str(args.get("claim_id", "")).casefold()
        if name == "claims" and role != "lead_scientist":
            ids = args.get("claim_ids", [])
            if args.get("view") != "role" or len(ids) != 1 or ids[0].casefold() not in allowed:
                raise ValueError("request one assigned claim with view=role")
        if name == "register_claim":
            parent = str(args.get("parent_id", "")).casefold()
            if role == "falsifier":
                if args.get("kind") == "scientific" or parent not in allowed:
                    raise ValueError("falsifier may register only commissioning descendants")
            elif (
                args.get("kind") != "scientific"
                or args.get("relation") != "repairs"
                or parent != target
                or claim == target
                or not isinstance(args.get("repair"), dict)
                or (record["children"] and claim not in record["children"])
            ):
                raise ValueError("repair scientist may register only one repairs child")
        elif name in {
            "register_evidence_contract",
            "link_claim_evidence",
            "close_claim",
            "record_terminal_observation",
        }:
            if claim not in allowed:
                raise ValueError("claim is outside this assignment")
            if role == "repair_scientist" and claim not in record["children"]:
                raise ValueError("repair scientist may contract only its registered child")
            if role == "blocker_resolver" and (
                claim != target
                or (
                    name == "register_evidence_contract"
                    and args.get("evidence_purpose") != "terminal_record"
                )
            ):
                raise ValueError("blocker resolver requires an assigned terminal record")
            if name == "close_claim" and claim == target and args.get("status") != "falsified":
                raise ValueError("scientific support requires an independent judge")
        active = str(args.get("active_claim_id", "")).casefold()
        if name.startswith("run_") and active not in allowed:
            raise ValueError("execution requires an assigned active_claim_id")
        if name in {"job_status", "cancel_job", "record_terminal_observation"}:
            job_ids = args.get("job_ids", [args.get("job_id")])
            owned = {
                op.get("job_id")
                for item in self.data["assignments"].values()
                if item["spec"]["claim_id"].casefold() == target
                for op in item["operations"].values()
            } - {None}
            if not set(job_ids) <= owned:
                raise ValueError("job is outside this assignment")

    def reserve(self, record: dict[str, Any], name: str, args: dict[str, Any]) -> str | None:
        if "operation_id" not in TOOL_SCHEMAS[name]["properties"]:
            return None
        operation = args["operation_id"]
        if not operation.startswith(record["spec"]["assignment_id"] + ":"):
            raise ValueError("operation_id must start with assignment_id followed by ':'")
        fingerprint = hashlib.sha256(
            json.dumps(
                [name, args],
                sort_keys=True,
                allow_nan=False,
            ).encode()
        ).hexdigest()
        previous = record["operations"].get(operation)
        if previous is not None:
            if previous["fingerprint"] != fingerprint:
                raise ValueError("operation_id already names different arguments")
            return operation
        if len(record["operations"]) >= record["spec"]["max_operations"]:
            raise ValueError("assignment operation budget exhausted")
        record["operations"][operation] = {"fingerprint": fingerprint, "status": "dispatched"}
        self.save()
        return operation

    def handoff(
        self, record: dict[str, Any], result: dict[str, Any], claims: list[dict[str, Any]]
    ) -> dict[str, Any]:
        expected = {"assignment_id", "claim_id", "outcome", "evidence_paths", "next_test"}
        if set(result) != expected:
            raise ValueError(f"handoff requires exactly {sorted(expected)}")
        spec = record["spec"]
        if (
            result["assignment_id"] != spec["assignment_id"]
            or result["claim_id"] != spec["claim_id"]
        ):
            raise ValueError("handoff belongs to a different assignment")
        if result["outcome"] not in {"falsified", "registered", "inconclusive", "blocked"}:
            raise ValueError("handoff cannot assert support or scientific completion")
        if (
            not isinstance(result["evidence_paths"], list)
            or not all(isinstance(path, str) for path in result["evidence_paths"])
            or not isinstance(result["next_test"], (str, type(None)))
        ):
            raise ValueError("invalid handoff evidence_paths or next_test")
        target = next((claim for claim in claims if claim["id"] == spec["claim_id"]), None)
        if target is None:
            raise ValueError("assigned claim is missing")
        if result["outcome"] == "falsified" and (
            spec["role"] != "falsifier" or target["status"] != "falsified"
        ):
            raise ValueError("falsification handoff requires a kernel-accepted counterexample")
        if result["outcome"] == "registered" and (
            spec["role"] != "repair_scientist" or not record["children"]
        ):
            raise ValueError("repair handoff requires a registered repairs child")
        evidence = {item["path"] for claim in claims for item in claim.get("evidence", [])}
        if not set(result["evidence_paths"]) <= evidence:
            raise ValueError("handoff evidence must already be linked in the kernel")
        if record.get("handoff") is not None and record["handoff"] != result:
            raise ValueError("handoff is immutable")
        record["handoff"] = result
        self.save()
        return result

    def completed(
        self,
        record: dict[str, Any],
        operation: str | None,
        name: str,
        args: dict[str, Any],
        result: Any,
    ) -> None:
        if operation is None:
            return
        entry = record["operations"][operation]
        entry["status"] = "returned"
        if isinstance(result, dict) and result.get("ok") is not False:
            if name == "register_claim":
                child = args["claim_id"].casefold()
                if child not in record["children"]:
                    record["children"].append(child)
            if isinstance(result.get("job_id"), str):
                entry["job_id"] = result["job_id"]
        self.save()
