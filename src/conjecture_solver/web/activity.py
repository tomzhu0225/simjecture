"""Public activity from built-in and native agents; never expose hidden reasoning text."""

from __future__ import annotations

import json
from pathlib import Path


def read_events(path, limit=512000):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        return []
    with path.open("rb") as stream:
        size = path.stat().st_size
        stream.seek(max(0, size - limit))
        raw = stream.read(limit)
    if size > limit:
        raw = raw.partition(b"\n")[2]
    events = []
    for line in raw.decode(errors="replace").splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except ValueError:
            continue
    return events


def describe_tool(name, arguments):
    """Describe public operations; never surface model reasoning blocks."""
    args = arguments if isinstance(arguments, dict) else {}
    normalized = str(name).lower()
    path = (
        args.get("target_file")
        or args.get("file_path")
        or args.get("path")
        or args.get("target_directory")
    )
    if normalized in {"read_file", "read_skill"}:
        label = "Reading skill" if normalized == "read_skill" else "Reading file"
        detail = path or args.get("name", "")
    elif normalized in {"grep", "search", "glob"}:
        label, detail = (
            "Searching files",
            str(args.get("pattern", "")) + (" in " + str(path) if path else ""),
        )
    elif normalized in {"write", "write_file", "search_replace", "apply_patch"}:
        label, detail = "Editing file", path or "Project files"
    elif normalized in {"list_dir", "list_directory"}:
        label, detail = "Inspecting folder", path or "Project files"
    elif normalized in {"run_terminal_command", "terminal", "bash", "command_execution"}:
        label = "Running command"
        detail = args.get("description") or str(args.get("command", "")).split("\n", 1)[0]
    elif normalized in {"run_simulation", "simulation_status"}:
        label = "Launching simulation" if normalized == "run_simulation" else "Checking simulation"
        detail = args.get("name") or args.get("identifier", "")
    elif "web" in normalized or normalized == "fetch_page":
        label, detail = "Searching or reading the web", args.get("query") or args.get("url", "")
    elif normalized == "progress_update":
        label, detail = "Progress update", args.get("message", "")
    else:
        label, detail = "Using " + str(name), args.get("description", "")
    return dict(label=label, detail=str(detail)[:300])


def public_tool_output(content):
    if isinstance(content, str):
        try:
            value = json.loads(content)
        except ValueError:
            return content[-24000:]
        if isinstance(value, dict):
            output = value.get(
                "output_for_prompt", value.get("stdout", value.get("output", content))
            )
            if isinstance(output, list) and all(
                isinstance(v, int) and 0 <= v < 256 for v in output
            ):
                return bytes(output).decode(errors="replace")[-24000:]
            return str(output)[-24000:]
        return content[-24000:]
    return str(content)[-24000:]


def native_activity(path, turn, live):
    activity = None
    commands = {}
    actions = {}
    for event in read_events(path):
        item = event.get("item", {})
        kind = item.get("type")
        if kind == "reasoning" or event.get("type") == "thinking":
            activity = dict(state="thinking", label="Thinking", source="CLI activity")
        elif kind == "command_execution":
            identifier = str(item.get("id") or len(commands))
            status = (
                "running"
                if event.get("type") != "item.completed"
                else ("succeeded" if item.get("exit_code", 0) == 0 else "failed")
            )
            commands[identifier] = dict(
                id="native-" + turn + "-" + identifier,
                name=item.get("command", "CLI command")[:90],
                command=item.get("command", ""),
                status=status if live or status != "running" else "interrupted",
                output=str(item.get("aggregated_output", ""))[-24000:],
                native=True,
                source_turn=turn,
                kind="command",
                live=live and status == "running",
                scientific_status="exploration",
            )
            descriptor = describe_tool("command_execution", item)
            activity = dict(state="running_command", source="CLI activity", **descriptor)
            actions[identifier] = dict(id=identifier, status=status, **descriptor)
        elif kind in {"file_change", "web_search", "mcp_tool_call"}:
            activity = dict(
                state="working",
                label={
                    "file_change": "Editing files",
                    "web_search": "Searching",
                    "mcp_tool_call": "Using a tool",
                }[kind],
                source="CLI activity",
            )
        elif kind == "agent_message":
            activity = dict(state="responding", label="Writing a response", source="CLI activity")
        # Anthropic-compatible public stream events (Grok and some CLI adapters).
        stream = event.get("event") if isinstance(event.get("event"), dict) else event
        delta = stream.get("delta", {})
        if delta.get("type") in {"thinking_delta", "reasoning_delta"}:
            activity = dict(state="thinking", label="Thinking", source="CLI activity")
        elif delta.get("type") == "text_delta":
            activity = dict(state="responding", label="Writing a response", source="CLI activity")
        blocks = (
            event.get("message", {}).get("content", [])
            if isinstance(event.get("message"), dict)
            else []
        )
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "thinking":
                activity = dict(state="thinking", label="Thinking", source="CLI activity")
            if block.get("type") == "tool_use":
                name, arguments = block.get("name", "tool"), block.get("input", {})
                identifier = str(block.get("id") or len(actions))
                descriptor = describe_tool(name, arguments)
                actions[identifier] = dict(id=identifier, status="running", **descriptor)
                activity = dict(state="working", source="CLI activity", **descriptor)
                if name in {"run_terminal_command", "bash", "terminal"}:
                    commands[identifier] = dict(
                        id="native-" + turn + "-" + identifier,
                        name=descriptor["detail"][:90] or "CLI command",
                        command=arguments.get("command", ""),
                        status="running",
                        output="",
                        native=True,
                        source_turn=turn,
                        kind="command",
                        live=live,
                        scientific_status="exploration",
                    )
            elif block.get("type") == "tool_result":
                identifier = str(block.get("tool_use_id"))
                status = "failed" if block.get("is_error") else "completed"
                if identifier in actions:
                    actions[identifier]["status"] = status
                if identifier in commands:
                    commands[identifier].update(
                        status="failed" if block.get("is_error") else "succeeded",
                        live=False,
                        output=public_tool_output(block.get("content", "")),
                    )
        if event.get("event") == "step_update":
            payload = event.get("step_update", event.get("payload", {}))
            step = payload.get("step_type")
            if step in {"thinking", "reasoning"}:
                activity = dict(state="thinking", label="Thinking", source="CLI activity")
            elif step == "tool":
                activity = dict(state="working", label="Using a tool", source="CLI activity")
    if activity is not None:
        activity["recent_actions"] = list(actions.values())[-8:]
    if not live:
        for command in commands.values():
            if command["status"] == "running":
                command.update(status="interrupted", live=False)
    return activity, list(commands.values())
