"""Redraw fresh v0.7.0 examples from frozen data linked to their reviewed audits.

No simulation, model call, or unpublished workspace is required.
"""

import hashlib
import json
from pathlib import Path

from fresh_plasma_figures import coupled_field_figures, island_field_figures


def check_bundle(demo):
    base = Path(__file__).resolve().parents[1] / "demos" / demo
    data, record = base / "fresh_v070_visual_data", base / "fresh_v070_record"
    manifest = json.loads((data / "manifest.json").read_text())

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    for name, expected in manifest["files"].items():
        path = (data / name).resolve()
        if not path.is_relative_to(data.resolve()) or sha(path) != expected:
            raise ValueError(f"Frozen visual input changed: {name}")
    if sha(record / "manifest.json") != manifest["record_manifest_sha256"]:
        raise ValueError("The linked scientific audit changed")
    review = record / "reviews" / (manifest["accepted_review"] + ".json")
    if sha(review) != manifest["accepted_review_sha256"]:
        raise ValueError("The linked independent claim review changed")
    if json.loads(review.read_text())["verdict"]["decision"] != "approved":
        raise ValueError("This figure requires an independently accepted claim verdict")


if __name__ == "__main__":
    check_bundle("resistive_mhd_island_coalescence")
    check_bundle("flash_warpx_kinetic_patch")
    island_field_figures.render()
    coupled_field_figures.render()
