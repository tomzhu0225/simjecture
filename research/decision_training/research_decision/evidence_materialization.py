"""Hash-checked small numerical outputs for independent, blinded assessment."""

import hashlib
from pathlib import Path

from .case import TERMINAL, receipts
from .storage import write_json


def materialize(case):
    from conjecture_solver.research_service import Lab

    case = Path(case)
    directory = case / "assessment-artifacts"
    directory.mkdir(exist_ok=True)
    index = []
    for receipt in receipts(case):
        if receipt["status"] not in TERMINAL:
            continue
        artifacts = receipt.get("remote_artifacts") or receipt.get("artifacts") or {}
        binding = receipt.get("binding", {})
        declared = dict(artifacts)
        for name, sha in binding.get("inputs", {}).items():
            source = case / "experiments" / receipt["id"] / "workspace" / name
            if source.exists():
                declared[name] = dict(sha256=sha, bytes=source.stat().st_size)
        for name in sorted(set(receipt.get("outputs", [])) | set(binding.get("inputs", {}))):
            item = declared.get(name)
            if not item or not 0 <= item.get("bytes", 0) <= 512 * 1024:
                continue
            if Path(name).suffix.lower() not in {
                ".json",
                ".csv",
                ".txt",
                ".md",
                ".py",
                ".cpp",
                ".h",
                ".hpp",
                ".f90",
                ".yaml",
                ".toml",
            }:
                continue
            filename = "artifact-" + item["sha256"][:24] + Path(name).suffix.lower()
            target = directory / filename
            if not target.exists():
                if name in receipt.get("outputs", []):
                    Lab(case).fetch_remote(experiment=receipt["id"], path=name)
                source = case / "experiments" / receipt["id"] / "workspace" / name
                data = source.read_bytes()
                if hashlib.sha256(data).hexdigest() != item["sha256"]:
                    raise ValueError("Assessment artifact identity differs")
                target.write_bytes(data)
            index.append(
                dict(
                    receipt_id=receipt["id"],
                    logical_name=name,
                    file=filename,
                    sha256=item["sha256"],
                    bytes=item["bytes"],
                )
            )
    write_json(directory / "index.json", index)
    return index
