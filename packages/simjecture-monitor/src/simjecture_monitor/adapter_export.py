"""Export an unchanged LoRA adapter with a portable, pinned base reference.

This only prepares files. It does not load a model, access a GPU or network,
verify workflow utility, or publish a release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def export_adapter(
    adapter,
    output,
    *,
    base_model,
    revision,
    expected_weights_sha256,
    expected_config_sha256,
):
    """Require the evaluated input identity and preserve every weight byte."""
    adapter, output = Path(adapter).resolve(), Path(output).resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", base_model):
        raise ValueError("Base model must be a repository ID, not a local cache path")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Pin the base to a full immutable repository revision")
    if output.is_relative_to(adapter):
        raise ValueError("Export outside the original adapter directory")
    names = {
        "adapter_model.safetensors": expected_weights_sha256,
        "adapter_config.json": expected_config_sha256,
    }
    for name, expected in names.items():
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Require the evaluated adapter's full SHA-256 hashes")
        if file_hash(adapter / name) != expected:
            raise ValueError(f"Evaluated adapter identity mismatch: {name}")
    original = json.loads((adapter / "adapter_config.json").read_text())
    if original.get("peft_type") != "LORA":
        raise ValueError("This exporter supports LoRA adapters only")
    portable = original | {"base_model_name_or_path": base_model, "revision": revision}
    output.mkdir(parents=True, exist_ok=False)
    try:
        shutil.copyfile(adapter / "adapter_model.safetensors", output / "adapter_model.safetensors")
        (output / "adapter_config.json").write_text(json.dumps(portable, indent=2) + "\n")
        if file_hash(output / "adapter_model.safetensors") != expected_weights_sha256:
            raise ValueError("Exported weights differ from the evaluated adapter")
        # Detect a changed source during copying as well as a wrong destination.
        if any(file_hash(adapter / name) != expected for name, expected in names.items()):
            raise ValueError("Original adapter changed during export")
        manifest = {
            "schema": "simjecture.adapter-export.v1",
            "base_model": base_model,
            "base_revision": revision,
            "original_adapter_sha256": names,
            "files": {
                name: {"sha256": file_hash(output / name), "bytes": (output / name).stat().st_size}
                for name in names
            },
            "configuration_changes": {
                key: {"before": original.get(key), "after": portable[key]}
                for key in ["base_model_name_or_path", "revision"]
                if original.get(key) != portable[key]
            },
            "validation": {
                "weight_bytes_preserved": True,
                "runtime_reload_verified": False,
                "workflow_release_gate": "not_assessed",
            },
            "scope": (
                "Portable adapter files only; runtime probes, provenance "
                "and release validation remain separate"
            ),
        }
        (output / "adapter_export.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return manifest
    except BaseException:
        shutil.rmtree(output)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--expected-weights-sha256", required=True)
    parser.add_argument("--expected-config-sha256", required=True)
    args = parser.parse_args()
    manifest = export_adapter(**vars(args))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
