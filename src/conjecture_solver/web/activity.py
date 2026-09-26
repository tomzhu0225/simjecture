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


def native_activity(path, turn, live):
    activity = None
    commands = {}
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
            activity = dict(
                state="running_command", label="Running a command", source="CLI activity"
            )
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
            if block.get("type") == "thinking":
                activity = dict(state="thinking", label="Thinking", source="CLI activity")
            if block.get("type") == "tool_use":
                activity = dict(
                    state="working",
                    label="Using " + str(block.get("name", "a tool")),
                    source="CLI activity",
                )
        if event.get("event") == "step_update":
            payload = event.get("step_update", event.get("payload", {}))
            step = payload.get("step_type")
            if step in {"thinking", "reasoning"}:
                activity = dict(state="thinking", label="Thinking", source="CLI activity")
            elif step == "tool":
                activity = dict(state="working", label="Using a tool", source="CLI activity")
    return activity, list(commands.values())
