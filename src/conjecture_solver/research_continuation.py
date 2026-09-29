"""Operator-authored phase handoffs and durable advisory steering.

These records provide context, never scientific acceptance or fresh evidence.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections import Counter
from pathlib import Path

from .research_service import ResearchService, put
from .study_status import read

MAX_FILE = 1024 * 1024
MAX_TOTAL = 16 * MAX_FILE


def selected_file(root, name):
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("Choose a workspace-relative file")
    path = root / "research" / relative
    current = root / "research"
    if current.is_symlink():
        raise ValueError("Research workspace cannot be a symlink")
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError("Inherited files cannot be symlinks")
    if not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ValueError("Inherited files must exist and be at most 1 MiB each")
    if relative.name in {
        "lab.py",
        "provider.json",
        "api-connection.json",
        "credentials.json",
    } or any(p.startswith(".") for p in relative.parts):
        raise ValueError("Do not inherit service clients or hidden configuration")
    return path


def preview(parent):
    parent = Path(parent).resolve()
    manifest = read(parent / "research.json")
    if not manifest:
        raise ValueError("Continuation currently requires a minimal study")
    files = []
    for p in sorted((parent / "research").rglob("*")):
        name = p.relative_to(parent / "research").as_posix()
        if len(files) >= 256:
            break
        if p.suffix not in {".py", ".md", ".json", ".txt", ".csv", ".par"}:
            continue
        try:
            selected_file(parent, name)
        except ValueError:
            continue
        if any(part.startswith(("_", ".")) for part in Path(name).parts):
            continue
        files.append(dict(path=name, bytes=p.stat().st_size))
    return dict(
        hypothesis=manifest["hypothesis"],
        files=files,
        capabilities=manifest.get("capabilities"),
        explanation=(
            "Copies selected working files and a frozen record summary. Prior "
            "results retain their original status; no approval is inherited."
        ),
    )


def attach(child, parent, files=()):
    parent = Path(parent).resolve()
    if parent == child.root:
        raise ValueError("A continuation needs a different study directory")
    if len(files) > 128 or len(set(files)) != len(files):
        raise ValueError("Choose at most 128 distinct files")
    previous = ResearchService(parent)
    # Collect a bounded snapshot before modifying the child. Parent remains untouched.
    with previous.lock():
        manifest_bytes = (parent / "research.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        payload = {}
        for name in files:
            data = selected_file(parent, name).read_bytes()
            if len(data) > MAX_FILE:
                raise ValueError("Inherited file grew beyond 1 MiB")
            payload[name] = data
        records = {
            kind: [json.loads(p.read_bytes()) for p in sorted((parent / kind).glob("*.json"))]
            for kind in ["commitments", "reviews", "methods"]
        }
        experiments = []
        for p in sorted((parent / "experiments").glob("*.json")):
            raw = p.read_bytes()
            e = json.loads(raw)
            experiments.append(
                {
                    k: e.get(k)
                    for k in ["id", "status", "stage", "binding", "artifacts", "scientific_status"]
                }
                | {"receipt_sha256": hashlib.sha256(raw).hexdigest()}
            )
        summary = dict(
            parent=str(parent),
            hypothesis=manifest["hypothesis"],
            operator_protocol=manifest.get("operator_protocol"),
            requirements=manifest.get("requirements", {}),
            steering=steering(parent),
            experiments=experiments,
            **records,
            authority=(
                "Historical context only. Unreviewed remains unreviewed; no "
                "evidence, method approval or fresh validation is imported."
            ),
        )
        notes = [read(p) for p in sorted((parent / "notebook").glob("*.json"))]
        notes.sort(key=lambda n: n.get("created_at", 0), reverse=True)
        parent_state = read(parent / "supervisor/state.json")
        brief = dict(
            parent=str(parent),
            hypothesis=manifest["hypothesis"][:2000],
            authority=summary["authority"],
            execution_counts=dict(Counter(e["status"] for e in experiments)),
            last_stop=parent_state.get("status"),
            last_error=parent_state.get("last_error"),
            recent_worker_notes=[
                {k: n.get(k) for k in ["id", "kind"]}
                | {"statement": str(n.get("statement", ""))[:800]}
                for n in notes[:5]
            ],
            reviews=[
                {k: q.get(k) for k in ["id", "claim", "status"]}
                | {"decision": (q.get("verdict") or {}).get("decision")}
                for q in records["reviews"][-10:]
            ],
            selected_files=list(payload),
            full_record="summary.json",
        )
        brief_raw = json.dumps(brief, indent=2).encode()
        raw = json.dumps(summary, indent=2).encode()
        if len(raw) + len(brief_raw) + sum(map(len, payload.values())) > MAX_TOTAL:
            raise ValueError(
                "Continuation snapshot exceeds 16 MiB; reduce selected files or "
                "prepare a bounded handoff"
            )
    descriptor = dict(
        parent=str(parent),
        created_at=time.time(),
        parent_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        snapshot_sha256=hashlib.sha256(raw).hexdigest(),
        brief_sha256=hashlib.sha256(brief_raw).hexdigest(),
        files={n: hashlib.sha256(b).hexdigest() for n, b in payload.items()},
    )
    with child.lock():
        current = read(child.root / "research.json")
        if current.get("continuation") or child._all("experiments"):
            raise ValueError("Continuation is attached once, before experiments")
        if (child.work / "inherited").exists() or (child.root / "continuation_input").exists():
            raise ValueError("Continuation would overwrite existing files")
        frozen = child.root / "continuation_input"
        frozen.mkdir()
        (frozen / "summary.json").write_bytes(raw)
        (frozen / "brief.json").write_bytes(brief_raw)
        for name, data in payload.items():
            for base in [frozen / "files", child.work / "inherited"]:
                target = base / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        (child.work / "CONTINUATION.md").write_text(
            f"# Continuation context\n\nParent: {parent}\n\n"
            "Start with ../continuation_input/brief.json. "
            "Use summary.json for full receipt references. "
            "Editable selected files are in inherited/. The frozen original is outside "
            "this workspace. No earlier result or method is automatically accepted here. "
            "Preserve uncertainty and collect fresh prospective validation.\n"
        )
        current["continuation"] = descriptor
        if "requirements" not in current and manifest.get("requirements"):
            current["requirements"] = manifest["requirements"]
        put(child.root / "research.json", current)
        child.manifest = current
    return descriptor


def steering(root):
    root = Path(root)
    delivered = read(root / "operator_steering" / "delivery.json")
    result = []
    for path in sorted((root / "operator_steering" / "messages").glob("*.json")):
        record = read(path)
        record["delivered_at"] = delivered.get(record["id"])
        result.append(record)
    return sorted(result, key=lambda r: (r["created_at"], r["id"]))


def submit(root, message, *, key=None):
    service = ResearchService(root)
    if not isinstance(message, str) or not message.strip() or len(message) > 8000:
        raise ValueError("Provide guidance between 1 and 8000 characters")
    if not isinstance(key, (str, type(None))) or (key and len(key) > 120):
        raise ValueError("Invalid steering request identifier")
    with service.lock():
        if time.time() >= service.manifest["deadline"] or read(
            service.root / "supervisor/state.json"
        ).get("status") in {"completed", "cancelled", "budget_exhausted"}:
            raise ValueError("This study has ended; use Continue investigation with a new budget")
        for record in steering(root):
            if key and record.get("request_key") == key:
                if record["message"] != message.strip():
                    raise ValueError(
                        "Steering request identifier already used for different guidance"
                    )
                return record
        if len(steering(root)) >= 64:
            raise ValueError("This phase already has 64 guidance entries; prepare a continuation")
        record = dict(
            id="steer_" + uuid.uuid4().hex,
            created_at=time.time(),
            author="operator",
            kind="advisory",
            message=message.strip(),
            request_key=key,
            scope=(
                "Planning guidance, not evidence or a retrospective contract "
                "change. New requirements/hypothesis/budget need a continuation "
                "phase."
            ),
        )
        (service.root / "operator_steering/messages").mkdir(parents=True, exist_ok=True)
        put(service.root / "operator_steering/messages" / (record["id"] + ".json"), record)
        return record


def deliver(service):
    with service.lock():
        records = steering(service.root)
        path = service.root / "operator_steering/delivery.json"
        seen = read(path)
        pending = [r for r in records if r["id"] not in seen][:4]
        for r in pending:
            seen[r["id"]] = time.time()
        if pending:
            put(path, seen)
    # Repeat the most recent delivered guidance after provider failures/restarts.
    recent = [r for r in records if r["id"] in seen and r not in pending][-4:]
    return recent + pending


def main():
    import argparse

    p = argparse.ArgumentParser(description="Send recorded advisory guidance to a minimal study")
    p.add_argument("--campaign", type=Path, required=True)
    p.add_argument("--message", required=True)
    p.add_argument("--request-key")
    a = p.parse_args()
    print(json.dumps(submit(a.campaign, a.message, key=a.request_key), indent=2))


def verify(service):
    descriptor = service.manifest.get("continuation")
    if not descriptor:
        return
    base = service.root / "continuation_input"
    records = {"summary.json": descriptor["snapshot_sha256"]}
    if descriptor.get("brief_sha256"):
        records["brief.json"] = descriptor["brief_sha256"]
    records.update({"files/" + n: h for n, h in descriptor["files"].items()})
    for name, digest in records.items():
        path = base / name
        if path.is_symlink() or not path.resolve().is_relative_to(base.resolve()):
            raise ValueError("Continuation snapshot path changed")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Continuation snapshot identity changed")
