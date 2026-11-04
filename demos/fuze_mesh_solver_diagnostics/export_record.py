"""Extract completed local FuZE audits and two figures; never execute a solver."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

DEMO = Path("demos/fuze_mesh_solver_diagnostics")
ASSETS = Path("docs/_static/demos/fuze")


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def select(data: dict, *keys: str) -> dict:
    return {key: data[key] for key in keys}


def snapshot(data: dict) -> dict:
    return {key: value for key, value in data.items() if key != "path"}


def run(data: dict) -> dict:
    result = select(data, "label", "manifest")
    result["completed_steps"] = (
        data["completed_steps"] if "completed_steps" in data else data["completed_physical_steps"]
    )
    result["manifest"] = select(
        data["manifest"], "source_revision", "returncode", "wall_stop_requested"
    )
    if "CP" in data:
        result.update(select(data, "CP", "species", "actual_mass_kg"))
    return result


def frame(data: dict) -> dict:
    return select(
        data,
        "time_us",
        "all13_finite",
        "Bmax_T",
        "Te_max_eV",
        "axis2mm_z100_110cm_magnetic_proxy_J",
        "ionUz_moment_abs_max_m_s",
    )


def export(flash: Path, warpx: Path, warpx_project: Path, repository: Path) -> None:
    record = repository / DEMO / "record"
    assets = repository / ASSETS
    record.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)
    sources = {}
    products = []

    def read(root: Path, group: str, pattern: str) -> dict:
        matches = sorted(root.glob(pattern))
        if len(matches) != 1:
            raise ValueError(f"Expected one completed source for {group}:{pattern}")
        path = matches[0]
        sources[f"{group}:{path.relative_to(root).as_posix()}"] = sha(path)
        return json.loads(path.read_text())

    def write(name: str, data: dict) -> None:
        payload = json.dumps(data, indent=2, allow_nan=False) + "\n"
        if any(prefix in payload for prefix in ("/home/", "/mnt/", "/tmp/")):
            raise ValueError(f"Private host path in excerpt: {name}")
        path = record / name
        path.write_text(payload)
        products.append(path)

    mesh = read(flash, "flash", "01_results/mesh_v5_summary.json")
    archive = read(flash, "flash", "03_visualization/checkpoint_archive_checks.json")
    execution = read(flash, "flash", "01_results/130*/provenance.json")
    redistribution = read(flash, "flash", "01_results/20_mpi_qualification.json")
    if execution["return_code"] != 0 or archive["automatic_continuation_enabled"]:
        raise ValueError("FLASH excerpt requires the normally paused archive.")
    write(
        "flash.json",
        {
            "mesh": {key: value for key, value in mesh.items() if key != "plot"},
            "archive": {key: value for key, value in archive.items() if key != "checkpoint"},
            "execution": select(
                execution,
                "mode",
                "binary_sha256",
                "initial_time_us",
                "target_time_us",
                "ranks",
                "quota_cores",
                "return_code",
            ),
            "solver_argv": execution["command"][execution["command"].index("-np") - 4 :],
            "redistribution": {
                **select(redistribution, "initial_time_us", "ranks", "quota_cores", "scope"),
                "final_checks": {
                    key: value
                    for key, value in redistribution["final_checks"].items()
                    if key != "checkpoint"
                },
            },
        },
    )

    continuity = read(
        warpx, "warpx", "rng_continuity_reviews/562*/RNG_CONTINUITY_ACTUAL_REVIEW.json"
    )
    corruption = read(warpx, "warpx", "rng_integrity_controls/564*/CORRUPTION_GUARD_REVIEW.json")
    default_off = read(
        warpx, "warpx", "rng_checkpoint_validation/559*/DEFAULT_OFF_ACTUAL_REVIEW.json"
    )
    write(
        "restart.json",
        {
            **select(
                continuity,
                "source_job",
                "restored_checksum_before_step29201_verified",
                "snapshot_final_bytes_equal",
                "matched_five_resumed_frames13field_L2",
                "all_resumed_frames_pass1e_10",
                "maximum_split_continuous_relative_L2",
                "particle_comparison",
                "limits",
            ),
            "runs": [run(item) for item in continuity["actual_runs"]],
            "snapshots": {
                key: snapshot(continuity[key])
                for key in (
                    "midpoint_snapshot",
                    "final_continuous_snapshot",
                    "final_split_snapshot",
                )
            },
            "default_off": select(
                default_off, "gateoff_original_13field_L2", "mode0_v2_13field_L2", "build_sha256"
            ),
            "corruption_guard": {
                **select(
                    corruption, "expected_native_rejection_passed", "completed_physical_steps"
                ),
                "returncode": corruption["manifest"]["returncode"],
            },
        },
    )

    axis = read(warpx, "warpx", "rng_axis_same_state_reviews/573*/ACTUAL_REVIEW.json")
    composition = read(warpx, "warpx", "rng_axis_validation/569*/ACTUAL_REVIEW.json")
    write(
        "axis.json",
        {
            **select(
                axis,
                "source_job",
                "decision",
                "same_start_CP_all_file_hashes_verified",
                "input_difference_only_axis",
                "actual_restores_before_step29201",
                "final_snapshot_bytes_equal",
                "particle_comparison",
                "axis0_replay_maxL2",
                "axis0_replay_all_pass1e_10",
                "spatial_mapping",
                "limits",
                "actual_interpretation",
            ),
            "start_snapshot": snapshot(axis["start_snapshot"]),
            "final_snapshots": [snapshot(item) for item in axis["final_snapshots"]],
            "runs": [
                {
                    **run(item),
                    "axis": item["axis"],
                    "frames": [frame(value) for value in item["all_saved_frames"]],
                }
                for item in axis["actual_runs"]
            ],
            "composition_regressions": select(composition, "binary_sha256", "comparisons"),
        },
    )
    builds = {}
    for version in ("v7_rng_checkpoint_candidate", "v8_rng_axis_composition"):
        build = read(warpx, "warpx", f"build_{version}/BUILD_STATUS.json")
        builds[version] = select(build, "sha256", "scope")
    write(
        "study.json",
        {
            "record_type": (
                "Operator-assisted local exploratory development; retrospective excerpt."
            ),
            "snapshot_date": "2026-11-04",
            "contributor": "LCB119",
            "human_framing": (
                "Develop FuZE gas loading and plasma calculations, place refinement near "
                "electrodes and the axis within a cell budget, and investigate solver/restart "
                "anomalies."
            ),
            "agent_work": (
                "Local code development, bounded simulations, readback audits and figures."
            ),
            "review": (
                "Working-assistant audits and operator steering; no formal claim adjudication."
            ),
            "formal_harness_adjudication": False,
            "software": {
                "Simjecture": (
                    "0.7.0 installed workspace; exact application Git commit not retained."
                ),
                "FLASH": (
                    "4.8, PARAMESH, local FuZE application overlays; executable hash in flash.json."
                ),
                "WarpX": {
                    "base_source_revision": continuity["actual_runs"][1]["manifest"][
                        "source_revision"
                    ],
                    "runtime": "Modified native RZ CUDA, non-MPI, PETSc, embedded boundaries.",
                    "builds": builds,
                },
            },
            "scope": (
                "Separate FLASH loading and WarpX solver-development branches, not a coupled run. "
                "No accepted discharge/pinch prediction, general solver repair or "
                "convergence claim."
            ),
        },
    )

    for root, group, source, target in (
        (flash, "flash", "03_visualization/paused_density_and_mesh.png", "flash-paused.png"),
        (
            warpx_project,
            "warpx-project",
            "hybrid_reproduction/visible_exports/cs3_same_rng_axis_14p60_14p75us.png",
            "same-rng-axis.png",
        ),
    ):
        original = root / source
        sources[f"{group}:{source}"] = sha(original)
        destination = assets / target
        shutil.copyfile(original, destination)
        products.append(destination)
    write(
        "provenance.json",
        {
            "source_file_sha256": sources,
            "export": (
                "Whitelisted JSON fields copied without changing numeric values; host paths, "
                "resource samples and raw fields omitted. Axis frames retain six diagnostic "
                "fields. "
                "Figures copied byte-for-byte. See export_record.py for exact selections. "
                "Source hashes identify local files; they do not make omitted raw data verifiable."
            ),
        },
    )
    manifest = {path.relative_to(repository).as_posix(): sha(path) for path in sorted(products)}
    (repository / DEMO / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flash", type=Path, required=True, help="Local flash_AMR directory")
    parser.add_argument("--warpx", type=Path, required=True, help="Local case_015_prescribed_CS3")
    parser.add_argument(
        "--warpx-project", type=Path, required=True, help="WarpX project files directory"
    )
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    export(args.flash, args.warpx, args.warpx_project, args.repository)
