"""One-shot JSON adapter for remote supervisors such as Simote.

The normal ``simjecture-mcp`` process remains the preferred interactive
transport.  This entry point opens the same CampaignMCPBridge for one call,
prints one bounded JSON result, and releases its campaign lease.  It lets an
SSH supervisor expose the official Simjecture tool contract without copying
SSH or model credentials into an agent process.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .mcp_schemas import validate_tool_arguments
from .mcp_server import BridgeConfig, CampaignMCPBridge, MCPBridgeError
from .role_assignments import ROLE_TOOLS, AssignmentStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="simjecture-call")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--campaign")
    parser.add_argument("--hypothesis-file", type=Path)
    parser.add_argument("--arguments-file", type=Path)
    parser.add_argument("--issue-assignment-file", type=Path)
    parser.add_argument("--assignment-id")
    parser.add_argument("--agent-id")
    parser.add_argument("--session-id")
    parser.add_argument("--handoff-file", type=Path)
    parser.add_argument("--list", action="store_true", dest="list_tools")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("tool", nargs="?")
    return parser


def _read_arguments(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("tool arguments must be a JSON object")
    return payload


async def _run(args: argparse.Namespace) -> Any:
    if args.probe:
        executable = shutil.which("bwrap")
        if executable is None:
            return {"ready": False, "sandbox": "bubblewrap", "reason": "bwrap is not installed"}
        try:
            result = subprocess.run(
                [
                    executable,
                    "--unshare-all",
                    "--die-with-parent",
                    "--clearenv",
                    "--ro-bind",
                    "/",
                    "/",
                    "--proc",
                    "/proc",
                    "--dev",
                    "/dev",
                    "--",
                    sys.executable,
                    "-I",
                    "-c",
                    "pass",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return {"ready": False, "sandbox": "bubblewrap", "reason": str(error)[:1000]}
        return {
            "ready": result.returncode == 0,
            "sandbox": "bubblewrap",
            "reason": result.stderr.strip()[:1000] if result.returncode else None,
        }
    bridge = CampaignMCPBridge(
        config=BridgeConfig(
            workspace=args.workspace,
            campaign=args.campaign,
            hypothesis_file=args.hypothesis_file,
        )
    )
    try:
        scoped = bool(args.assignment_id)
        if any((args.agent_id, args.session_id)) and not scoped:
            raise ValueError("agent-id and session-id require assignment-id")
        if scoped and (not args.agent_id or not args.session_id or args.issue_assignment_file):
            raise ValueError(
                "assigned calls require agent-id and session-id and cannot issue roles"
            )
        if args.list_tools and not scoped:
            return {"tools": await bridge.list_tools()}
        if args.handoff_file and not scoped:
            raise ValueError("handoff requires an assignment")
        if not args.tool and not (
            args.list_tools or args.issue_assignment_file or args.handoff_file
        ):
            raise ValueError("a tool name is required unless --list is used")
        await bridge.startup()
        assignments = AssignmentStore(bridge._campaign_candidates()[0])
        if args.issue_assignment_file:
            spec = _read_arguments(args.issue_assignment_file)
            ledger = await bridge.call_tool(
                "claims",
                {
                    "view": "role",
                    "claim_ids": [spec.get("claim_id", "")],
                },
            )
            claims = ledger.get("claims", [])
            if not claims:
                raise ValueError("assignment requires an existing claim")
            if spec.get("role") == "repair_scientist" and claims[0]["status"] != "falsified":
                raise ValueError("repair scientist requires a falsified parent")
            issued = assignments.issue(spec)
            return {"spec": issued["spec"], "operations_used": len(issued["operations"])}
        record = None
        if scoped:
            record = assignments.bind(args.assignment_id, args.agent_id, args.session_id)
            if args.handoff_file:
                claims = []
                for claim_id in [record["spec"]["claim_id"], *record["children"]]:
                    ledger = await bridge.call_tool(
                        "claims",
                        {
                            "view": "role",
                            "claim_ids": [claim_id],
                        },
                    )
                    claims.extend(ledger["claims"])
                return assignments.handoff(record, _read_arguments(args.handoff_file), claims)
            if args.list_tools:
                return {
                    "tools": [
                        tool
                        for tool in await bridge.list_tools()
                        if tool["name"] in ROLE_TOOLS[record["spec"]["role"]]
                    ]
                }
        arguments = validate_tool_arguments(args.tool, _read_arguments(args.arguments_file))
        operation = None
        if record is not None:
            if args.tool not in {
                "snapshot",
                "claims",
                "list_skills",
                "read_skill",
            } and args.session_id not in record.get("reconciled_sessions", []):
                raise ValueError("read snapshot in this session before scientific work")
            assignments.authorize(record, args.tool, arguments)
            operation = assignments.reserve(record, args.tool, arguments)
        result = await bridge.call_tool(args.tool, arguments)
        if args.tool == "prepare_adjudication" and not result.get("already_recorded"):
            packet = result.get("packet")
            digest = hashlib.sha256(
                json.dumps(
                    packet,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            if packet is None or digest != result.get("case_sha256"):
                raise ValueError("adjudication packet was truncated in transport; review refused")
        if record is not None:
            assignments.completed(record, operation, args.tool, arguments, result)
        if args.tool == "snapshot" and isinstance(result, dict):
            report_path = bridge._campaign_candidates()[0] / "mvp_report.json"
            result["terminal_report"] = None
            if report_path.is_file():
                report = json.loads(report_path.read_text(encoding="utf-8"))
                if not isinstance(report, dict):
                    raise ValueError("terminal report must be a JSON object")
                result["terminal_report"] = {
                    "status": report.get("status"),
                    "finished_at": report.get("finished_at"),
                    "final_answer": str(report.get("final_answer", ""))[:4000],
                }
            if record is not None:
                sessions = record.setdefault("reconciled_sessions", [])
                if args.session_id not in sessions:
                    sessions.append(args.session_id)
                    assignments.save()
            visible = [
                item
                for item in assignments.data["assignments"].values()
                if record is None or item is record
            ]
            result["role_assignment_count"] = len(visible)
            result["role_assignments_truncated"] = len(visible) > 24
            result["role_assignments"] = [
                {
                    **item["spec"],
                    "operations_used": len(item["operations"]),
                    "sessions": item["sessions"][-8:],
                    "session_count": len(item["sessions"]),
                    "children": item["children"][-24:],
                    "child_count": len(item["children"]),
                }
                | {"handoff": item.get("handoff")}
                for item in visible[-24:]
            ]
        return result
    finally:
        bridge.shutdown()


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = asyncio.run(_run(args))
    except (MCPBridgeError, ValueError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
