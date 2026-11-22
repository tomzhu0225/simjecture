"""Prepare a pinned public checkpoint without loading or running the model."""

import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXISTING = Path(r"F:\CANNlab\TasteLeap\research_policy\comparisons\Qwen3.5-9B")
REVISION = "c202236235762e1c871ad0ccb60c8ee5ba337b9a"


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    manifest = json.loads((EXISTING / "download-manifest.json").read_bytes())
    if manifest["sha"] != REVISION:
        raise ValueError("The pinned model revision differs from the source manifest")
    destination = ROOT / "models" / "Qwen3.5-9B"
    destination.mkdir(parents=True, exist_ok=True)

    def fetch(item):
        name = item["rfilename"]
        if name.startswith("."):
            return None
        output = destination / name
        output.parent.mkdir(parents=True, exist_ok=True)
        expected = (item.get("lfs") or {}).get("sha256")
        existing = EXISTING / name
        if not output.exists() and existing.exists():
            if not expected or sha256(existing) == expected:
                os.link(existing, output)
        if not output.exists():
            partial = output.with_name(output.name + ".part")
            command = [
                "curl.exe",
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--retry",
                "3",
                "--retry-delay",
                "2",
                "--connect-timeout",
                "20",
                "--max-time",
                "10800",
                "--output",
                str(partial),
            ]
            if partial.exists():
                command += ["--continue-at", "-"]
            command += [
                "--proxy",
                "http://127.0.0.1:10808",
                f"https://huggingface.co/Qwen/Qwen3.5-9B/resolve/{REVISION}/{name}",
            ]
            subprocess.run(command, check=True)
            if expected and sha256(partial) != expected:
                raise ValueError(f"Checksum mismatch for {name}")
            os.replace(partial, output)
        digest = sha256(output)
        if expected and digest != expected:
            raise ValueError(f"Checksum mismatch for {name}")
        if item.get("size") is not None and output.stat().st_size != item["size"]:
            raise ValueError(f"Size mismatch for {name}")
        print(f"verified {name} {output.stat().st_size}", flush=True)
        return dict(path=name, bytes=output.stat().st_size, sha256=digest)

    with ThreadPoolExecutor(max_workers=4) as pool:
        files = [record for record in pool.map(fetch, manifest["siblings"]) if record]
    (destination / "verified-manifest.json").write_text(
        json.dumps(
            dict(
                repository="Qwen/Qwen3.5-9B",
                revision=REVISION,
                files=files,
                model_loaded=False,
                inference_performed=False,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
