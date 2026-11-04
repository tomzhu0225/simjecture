"""Verify the retained FuZE excerpt and arithmetic, without running either solver."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

DEMO = Path("demos/fuze_mesh_solver_diagnostics")
FIELDS = {"Er", "Et", "Ez", "Br", "Bt", "Bz", "jr", "jt", "jz", "rho", "eb_covered", "Te", "Pe"}
TOLERANCE = 1e-10  # The recorded restart-regression criterion, not a physics tolerance.


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(a: float, b: float) -> None:
    require(math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-24), f"Inconsistent values: {a}, {b}")


def verify(repository: Path) -> dict:
    demo = repository / DEMO
    manifest = json.loads((demo / "manifest.json").read_text())
    expected = {
        f"{DEMO}/record/{name}.json" for name in ("flash", "restart", "axis", "study", "provenance")
    } | {f"docs/_static/demos/fuze/{name}.png" for name in ("flash-paused", "same-rng-axis")}
    require(set(manifest) == expected, "Incomplete retained-artifact inventory")
    for name, digest in manifest.items():
        path = repository / name
        require(path.resolve().is_relative_to(repository.resolve()), "Out-of-repository path")
        payload = path.read_bytes()
        require(hashlib.sha256(payload).hexdigest() == digest, f"Changed retained artifact: {name}")
        if path.suffix == ".json":
            require(not any(p in payload for p in (b"/home/", b"/mnt/", b"/tmp/")), "Host path")

    def read(name: str) -> dict:
        return json.loads((demo / "record" / f"{name}.json").read_text())

    flash = read("flash")
    mesh, archive = flash["mesh"], flash["archive"]
    require(sum(mesh["blocks_by_level"].values()) == archive["block_count"], "Leaf block count")
    require(mesh["leaf_cells"] == archive["leaf_cells"], "Leaf cell count")
    require(mesh["within_200000_budget"] == (mesh["leaf_cells"] <= 200000), "Cell budget")
    require(mesh["leaf_cells"] == 100 * archive["block_count"], "10 by 10 block accounting")
    for level, blocks in mesh["blocks_by_level"].items():
        zones = mesh["zone_cells_by_level"]
        require(
            zones["all_copper"][level] + zones["all_flow"][level] == 100 * blocks,
            "Copper/flow partition",
        )
    sizes = mesh["cell_edge_mm_by_level"]
    require(set(sizes) == set(mesh["blocks_by_level"]), "Mesh levels")
    for level, size in sizes.items():
        close(size, sizes["1"] / 2 ** (int(level) - 1))
    require(sorted(sizes.values(), reverse=True) == archive["sizes_mm"], "Archived mesh sizes")
    require(
        archive["solver_return_code"] == flash["execution"]["return_code"] == 0, "FLASH normal exit"
    )
    require(archive["finite_positive_thermodynamics"], "FLASH readback")
    require(not archive["automatic_continuation_enabled"], "Paused archive scope")
    require(archive["time_us"] < flash["execution"]["target_time_us"], "Unfinished loading target")

    restart = read("restart")
    rows = restart["matched_five_resumed_frames13field_L2"]
    require(
        len(rows) == len({row["plotfile_name"] for row in rows}) == 5,
        "Five independent resumed frames required",
    )
    for row in rows:
        errors = row["relative_L2"]
        require(set(errors) == FIELDS, "Incomplete 13-field regression")
        require(all(math.isfinite(v) and v >= 0 for v in errors.values()), "Invalid L2 value")
        require(row["passes1e_10"] == (max(errors.values()) < TOLERANCE), "Regression verdict")
    max_l2 = max(value for row in rows for value in row["relative_L2"].values())
    close(max_l2, restart["maximum_split_continuous_relative_L2"])
    require(restart["all_resumed_frames_pass1e_10"] == (max_l2 < TOLERANCE), "Restart verdict")
    snapshots = restart["snapshots"]
    require(
        snapshots["final_continuous_snapshot"] == snapshots["final_split_snapshot"],
        "Final RNG identities differ",
    )
    require(restart["snapshot_final_bytes_equal"], "Recorded RNG byte comparison")
    require(restart["restored_checksum_before_step29201_verified"], "Restore phase audit")
    missing, continuous, split = restart["runs"]
    require(
        missing["manifest"]["returncode"] != 0 and missing["completed_steps"] == 0,
        "Missing snapshot must be rejected before stepping",
    )
    guard = restart["corruption_guard"]
    require(
        guard["expected_native_rejection_passed"]
        and guard["returncode"] != 0
        and guard["completed_physical_steps"] == 0,
        "Corruption rejection",
    )
    for item in (continuous, split):
        require(item["manifest"]["returncode"] == 0 and item["CP"]["synchronized"], "Native run")
        require(not item["manifest"]["wall_stop_requested"], "Unfinished native run")
        close(sum(s["mass_kg"] for s in item["species"].values()), item["actual_mass_kg"])
    close(continuous["CP"]["time_s"], split["CP"]["time_s"])
    feed = next(item for item in restart["particle_comparison"] if item["species"] == "feed")
    require(
        feed["new_cohort_count"] == 400 and feed["new_cohort_all7_attributes_exact_equal"],
        "New feed cohort comparison",
    )
    for errors in (
        restart["default_off"]["gateoff_original_13field_L2"],
        restart["default_off"]["mode0_v2_13field_L2"],
    ):
        require(
            set(errors) == FIELDS
            and all(math.isfinite(v) and 0 <= v < TOLERANCE for v in errors.values()),
            "Default-off regression",
        )

    axis = read("axis")
    require(
        axis["decision"] == "do_not_adopt_axis_boundary_as_repair_or_resume_production",
        "Rejected axis candidate relabelled",
    )
    require(axis["same_start_CP_all_file_hashes_verified"], "Different starting checkpoints")
    require(
        axis["input_difference_only_axis"]
        == {"hybrid_pic_model.qdsmc_axis_regular_velocity": ["0", "1"]},
        "Confounded input comparison",
    )
    require(
        axis["actual_restores_before_step29201"][0] == axis["actual_restores_before_step29201"][1],
        "Different initial RNG state",
    )
    require(
        axis["final_snapshots"][0] == axis["final_snapshots"][1]
        and axis["final_snapshot_bytes_equal"],
        "Different final RNG identities",
    )
    baseline, candidate = axis["runs"]
    for item in axis["runs"]:
        require(item["manifest"]["returncode"] == 0 and item["CP"]["synchronized"], "Axis run")
        require(not item["manifest"]["wall_stop_requested"], "Axis wall stop")
        require(
            len(item["frames"]) == 15 and all(f["all13_finite"] for f in item["frames"]),
            "Axis saved-frame coverage",
        )
        close(sum(s["mass_kg"] for s in item["species"].values()), item["actual_mass_kg"])
    require(
        [f["time_us"] for f in baseline["frames"]] == [f["time_us"] for f in candidate["frames"]],
        "Unmatched physical times",
    )
    require(
        candidate["species"]["ions"]["macro_particles"]
        == baseline["species"]["ions"]["macro_particles"] + 1,
        "Retained-ion difference lost",
    )
    study = read("study")
    require(not study["formal_harness_adjudication"], "Exploratory record relabelled")
    builds = study["software"]["WarpX"]["builds"]
    require(
        builds["v7_rng_checkpoint_candidate"]["sha256"] == restart["default_off"]["build_sha256"],
        "RNG build identity",
    )
    require(
        builds["v8_rng_axis_composition"]["sha256"]
        == axis["composition_regressions"]["binary_sha256"],
        "Axis build identity",
    )
    comparisons = axis["composition_regressions"]["comparisons"]
    require(len(comparisons) == 4, "Four composition regressions required")
    for errors in comparisons.values():
        require(
            set(errors) == FIELDS
            and all(math.isfinite(v) and 0 <= v < TOLERANCE for v in errors.values()),
            "Composition regression",
        )
    axis_feed = next(item for item in axis["particle_comparison"] if item["species"] == "feed")
    require(
        axis_feed["new_count"] == 1200 and axis_feed["new_all7_attributes_exact"],
        "Same-RNG new feed cohort",
    )
    return {
        "retained_files_verified": len(manifest),
        "flash_leaf_cells": mesh["leaf_cells"],
        "flash_paused_time_us": archive["time_us"],
        "restart_maximum_relative_L2": max_l2,
        "axis_window_peak_Te_eV": [max(f["Te_max_eV"] for f in r["frames"]) for r in axis["runs"]],
        "axis_candidate_adopted": False,
        "scope": "Retained bytes and audit arithmetic only; no raw-field or solver verification.",
    }


if __name__ == "__main__":
    print(json.dumps(verify(Path(__file__).resolve().parents[2]), indent=2))
