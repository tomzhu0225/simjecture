"""Durable JSON publication and case-local file ownership checks."""

import json
import os
import uuid
from pathlib import Path


def read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_bytes()) if path.exists() else default


def write_json(path, value, *, immutable=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if immutable and path.exists():
        if path.read_text(encoding="utf-8") != payload:
            raise ValueError(f"Immutable research record changed: {path.name}")
        return
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if immutable:
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_text(encoding="utf-8") != payload:
                    raise ValueError("Concurrent publication disagreed on immutable data") from None
        else:
            os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def owned_path(root, value):
    root = Path(root).resolve()
    target = (root / value).resolve()
    if not target.is_relative_to(root) or target == root:
        raise ValueError("Research path escapes its owned workspace")
    return target
