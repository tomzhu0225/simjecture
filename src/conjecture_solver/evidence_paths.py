"""A small, deterministic path grammar for JSON evidence (never eval/JSONPath code)."""

from __future__ import annotations

import re
from typing import Any

EVIDENCE_PATH_PATTERN = (
    r"^(?:\$\.)?[A-Za-z0-9_-]+(?:(?:\.[A-Za-z0-9_-]+)|(?:\[(?:0|[1-9][0-9]*)\]))*$"
)


def evidence_path_parts(path: str) -> tuple[str, ...]:
    if len(path) > 1024 or re.fullmatch(EVIDENCE_PATH_PATTERN, path) is None:
        raise ValueError(
            "Use object keys and nonnegative array indices; wildcards/expressions are unsupported"
        )
    path = path.removeprefix("$.")
    return tuple(re.sub(r"\[([0-9]+)\]", r".\1", path).split("."))


def evidence_value(document: Any, path: str) -> Any:
    current = document
    for key in evidence_path_parts(path):
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and re.fullmatch(r"0|[1-9][0-9]*", key):
            index = int(key)
            if index >= len(current):
                raise KeyError(path)
            current = current[index]
        else:
            raise KeyError(path)
    return current
