"""Shared presentation assets for the local and hosted web interfaces."""

import json
from functools import cache
from pathlib import Path

PACKAGED_ENGLISH = Path(__file__).with_name("static") / "language/en.json"


def _read_catalog(path: Path) -> dict[str, str]:
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return {}
    if not isinstance(entries, dict):
        return {}
    return {key: text for key, text in entries.items() if isinstance(text, str) and text}


@cache
def _packaged_english() -> dict[str, str]:
    return _read_catalog(PACKAGED_ENGLISH)


def render_i18n_messages(static_root: Path) -> bytes:
    """Serve one complete default catalog, including on a cold start with damaged assets."""
    english = _packaged_english() | _read_catalog(static_root / "language/en.json")
    source = (static_root / "i18n-messages.js").read_text(encoding="utf-8")
    payload = json.dumps(english, separators=(",", ":")).replace("<", "\\u003c")
    return source.replace("/* ENGLISH_CATALOG */ {}", payload, 1).encode("utf-8")
