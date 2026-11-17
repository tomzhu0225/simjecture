"""Remote-only preparation download, with pinned local checksums and resumable files."""

import hashlib
import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    root = Path(__file__).resolve().parent
    model = root / "models/Qwen3.5-9B"
    manifest = json.loads((root / "expected-model-manifest.json").read_bytes())

    def download(item):
        destination = model / item["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and sha256(destination) == item["sha256"]:
            return
        partial = destination.with_name(destination.name + ".part")
        for attempt in range(12):
            offset = partial.stat().st_size if partial.exists() else 0
            if offset == item["bytes"]:
                break
            if offset > item["bytes"]:
                raise ValueError("Unexpected oversized partial model file")
            url = (
                f"https://hf-mirror.com/Qwen/Qwen3.5-9B/resolve/{manifest['revision']}/{item['path']}"
                f"?download=true&offset={offset}&attempt={attempt}"
            )
            command = [
                "curl",
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--connect-timeout",
                "20",
                "--max-time",
                "600",
                "--speed-limit",
                "1024",
                "--speed-time",
                "90",
                "--continue-at",
                "-",
                "--output",
                str(partial),
                url,
            ]
            print("download", item["path"], offset, flush=True)
            result = subprocess.run(command, capture_output=True, check=False)
            print(
                "result",
                item["path"],
                result.returncode,
                partial.stat().st_size if partial.exists() else 0,
                result.stderr.decode(errors="replace")[-300:],
                flush=True,
            )
            if result.returncode:
                time.sleep(min(30, 2 * (attempt + 1)))
        if (
            not partial.exists()
            or partial.stat().st_size != item["bytes"]
            or sha256(partial) != item["sha256"]
        ):
            raise ValueError("Remote download integrity failure for " + item["path"])
        os.replace(partial, destination)
        print("verified", item["path"], flush=True)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(download, manifest["files"]))
    (model / "verified-manifest.json").write_text(json.dumps(manifest, indent=2))
    (root / "remote-model-ready.json").write_text(
        json.dumps(
            dict(status="verified", model_loaded=False, training_updates=0, revision=manifest["revision"])
        )
    )
    print("ALL_MODEL_FILES_VERIFIED", flush=True)


if __name__ == "__main__":
    main()
