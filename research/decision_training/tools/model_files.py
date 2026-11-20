"""Link/copy and verify only the pinned Qwen3.5-9B base; no model inference."""

import argparse
import hashlib
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "config/model-manifest.json").read_bytes())
    args.directory.mkdir(parents=True, exist_ok=True)
    for item in manifest["files"]:
        name = item["path"]
        if Path(name).name != name:
            raise ValueError("Unexpected model manifest path")
        path = args.directory / name
        if args.download and not path.exists():
            from huggingface_hub import hf_hub_download
            hf_hub_download(manifest["repository"], filename=name, revision=manifest["revision"],
                            local_dir=str(args.directory))
        if not path.is_file() or path.stat().st_size != item["bytes"]:
            raise ValueError("Missing model file or size mismatch: " + name)
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != item["sha256"]:
                raise ValueError("Pinned model SHA-256 mismatch: " + name)
    target = args.directory / "verified-manifest.json"
    temporary = target.with_suffix(".partial")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n")
    os.replace(temporary, target)
    print(json.dumps(dict(verified=True, repository=manifest["repository"], revision=manifest["revision"],
                          files=len(manifest["files"]), inference_performed=False)))


if __name__ == "__main__":
    main()
