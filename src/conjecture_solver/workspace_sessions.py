"""Per-conversation transport continuity, separated by model and connection."""

import hashlib
import json
from pathlib import Path


def route_key(config):
    fields = {k: config.get(k) for k in ("backend", "model", "base_url", "api_key")}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def load_session(directory, config):
    path = Path(directory) / "agent-session.json"
    try:
        session = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return session if session.get("route") == route_key(config) else {}


def save_session(directory, config, **state):
    from .web.workspace import private_json

    private_json(Path(directory) / "agent-session.json", {"route": route_key(config), **state})
