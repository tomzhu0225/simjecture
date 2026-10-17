"""Complete immutable review files with bounded, read-only views."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from pathlib import Path

INLINE_SOURCE_BYTES = 32 * 1024
INLINE_PACKET_BYTES = 128 * 1024


def decode_page(block, max_bytes):
    """Finish a UTF-8 codepoint at the page edge (at most three extra bytes)."""
    end = min(len(block), max_bytes)
    while True:
        try:
            return block[:end].decode("utf-8"), end
        except UnicodeDecodeError as error:
            if error.reason == "unexpected end of data" and end < len(block):
                end += 1
                continue
            return block[:end].decode("utf-8", errors="replace"), end


def object_directory(root):
    root = Path(root).resolve()
    directory = root / "review_objects"
    if directory.is_symlink():
        raise ValueError("Review objects must be real contained files")
    directory.mkdir(exist_ok=True)
    return directory


def freeze_file(root, source, *, expected_sha256=None):
    from .research_service import sha

    source = Path(source)
    digest = sha(source)
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("Review source changed from its frozen binding")
    directory = object_directory(root)
    target = directory / digest
    if not target.exists():
        temporary = directory / ("." + uuid.uuid4().hex)
        try:
            shutil.copyfile(source, temporary)
            if sha(temporary) != digest:
                raise ValueError("Review source changed while freezing")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    if target.is_symlink() or sha(target) != digest:
        raise ValueError("Immutable review object changed")
    return dict(
        path=f"review_objects/{digest}", sha256=digest, bytes=target.stat().st_size, read_only=True
    )


def freeze_json(root, value):
    data = json.dumps(value, sort_keys=True, allow_nan=False).encode()
    digest = hashlib.sha256(data).hexdigest()
    directory = object_directory(root)
    path = directory / digest
    if not path.exists():
        temporary = directory / ("." + uuid.uuid4().hex)
        temporary.write_bytes(data)
        os.replace(temporary, path)
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Immutable review object changed")
    return dict(path=f"review_objects/{digest}", sha256=digest, bytes=len(data), read_only=True)


def source_views(root, workspace, bindings, names):
    sources, references = {}, {}
    for name in names:
        path = Path(workspace) / name
        reference = freeze_file(root, path, expected_sha256=bindings[name])
        references[name] = reference
        if reference["bytes"] <= INLINE_SOURCE_BYTES:
            sources[name] = path.read_text()
        reference["included_inline"] = name in sources
    return sources, references


def packet_view(root, packet):
    """Bound model input, never the authoritative packet or acceptance hash."""
    if len(json.dumps(packet).encode()) <= INLINE_PACKET_BYTES:
        return packet
    reference = freeze_json(root, packet)
    view = dict(
        packet_reference=reference,
        authority="Indexed view only. The complete packet and its hash remain authoritative.",
        retrieval=(
            "Read the reference with read_review_asset(sha256, json_path, offset, "
            "max_bytes), or use read-only native file tools on its study-relative path. "
            "Each field below has a JSON path into the complete packet. Do not infer "
            "missing evidence from an excerpt; retrieve relevant fields before deciding."
        ),
        fields={},
    )
    for key, value in packet.items():
        encoded = json.dumps(value).encode()
        if key == "target_claim" or (
            len(encoded) <= 4096 and len(json.dumps(view).encode()) + len(encoded) < 24000
        ):
            view[key] = value
        else:
            view["fields"][key] = dict(
                json_path=key,
                bytes=len(encoded),
                items=len(value) if isinstance(value, (list, dict)) else None,
            )
    return view


def read_asset(root, digest, *, json_path=None, offset=0, max_bytes=16384):
    from .evidence_paths import evidence_value
    from .research_audit import strict_json
    from .research_service import sha

    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("Choose a recorded review object SHA256")
    if (
        type(offset) is not int
        or offset < 0
        or type(max_bytes) is not int
        or not 1 <= max_bytes <= 65536
    ):
        raise ValueError("Use a nonnegative byte offset and a page of 1..65536 bytes")
    path = object_directory(root) / digest
    if path.is_symlink() or not path.is_file() or sha(path) != digest:
        raise ValueError("Review object missing or changed")
    if json_path:
        value = evidence_value(strict_json(path.read_text()), json_path)
        data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        total = len(data)
        block = data[offset : offset + max_bytes + 3]
    else:
        total = path.stat().st_size
        with path.open("rb") as stream:
            stream.seek(offset)
            block = stream.read(max_bytes + 3)
    content, consumed = decode_page(block, max_bytes)
    end = offset + consumed
    return dict(
        sha256=digest,
        json_path=json_path,
        offset=offset,
        bytes=consumed,
        total_bytes=total,
        next_offset=end if end < total else None,
        content=content,
        authority="Hash-verified excerpt; scientific sufficiency requires review",
    )
