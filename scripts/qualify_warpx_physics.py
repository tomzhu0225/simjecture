#!/usr/bin/env python3
"""Qualify the real WarpX/openPMD instrument on a fixed seed/resolution matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from conjecture_solver.adapters.base import JobState, NormalizedResult
from conjecture_solver.adapters.warpx import (
    SubprocessWarpXScheduler,
    WarpXAdapter,
    WarpXExecutionProfile,
    WarpXNumericalConfig,
    WarpXPhysicalConfig,
    WarpXQualifiedScope,
    WarpXRunnerKind,
    build_warpx_experiment,
    build_warpx_physics_qualification,
    qualify_warpx_picmi_compiler,
    warpx_physics_qualification_hash,
)
from conjecture_solver.benchmarks.kinetic_sufficiency import (
    GaussianComponent,
    GaussianMixture,
    solve_modes,
)

CALIBRATION_SEEDS = (1, 7, 19, 101)
CALIBRATION_RESOLUTIONS = (
    ("coarse", 64, 512, 0.05, 2),
    ("refined", 128, 512, 0.025, 4),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warpx-python", type=Path, default=Path(".runtime/warpx-cpu/bin/python"))
    parser.add_argument(
        "--work-root", type=Path, default=Path(".runtime/warpx-physics-qualification-v2")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/warpx_physics_qualification.json"),
    )
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    warpx_python = args.warpx_python.resolve()
    work_root = args.work_root.resolve()
    physical = WarpXPhysicalConfig(perturbation_amplitude=0.02)
    unqualified_profile = WarpXExecutionProfile(
        profile_id="warpx_26_07_matrix_calibration_unqualified",
        runner_kind=WarpXRunnerKind.LOCAL_CPU,
        warpx_version="26.07",
    )
    scheduler = SubprocessWarpXScheduler(
        work_root=work_root / "jobs",
        command=(
            sys.executable,
            str(project_root / "scripts" / "run_warpx_pair.py"),
            "--warpx-python",
            str(warpx_python),
        ),
        profile=unqualified_profile,
        timeout_seconds=300,
    )
    adapter = WarpXAdapter(scheduler)
    normalized_results: list[NormalizedResult] = []
    compile_run = None
    for (
        resolution_name,
        grid_cells,
        electron_ppc,
        time_step,
        diagnostic_steps,
    ) in CALIBRATION_RESOLUTIONS:
        for seed in CALIBRATION_SEEDS:
            numerical = WarpXNumericalConfig(
                grid_cells=grid_cells,
                electron_macroparticles_per_cell=electron_ppc,
                ion_macroparticles_per_cell=16,
                time_step_omega_pe=time_step,
                final_time_omega_pe=20.0,
                diagnostic_interval_steps=diagnostic_steps,
                random_seed=seed,
            )
            experiment = build_warpx_experiment(
                physical=physical,
                numerical=numerical,
                experiment_id=f"warpx_calibration_{resolution_name}_seed_{seed}_v2",
            )
            run = adapter.compile_input(experiment)
            if compile_run is None:
                compile_run = run
            job = adapter.submit(run, idempotency_key=f"{experiment.id}:submit")
            status = adapter.monitor(job)
            if status.state is not JobState.COMPLETED:
                raise RuntimeError(f"calibration job did not complete: {status.model_dump()}")
            normalized_results.append(adapter.normalize(adapter.retrieve(job)))

    if compile_run is None:
        raise RuntimeError("calibration matrix is empty")
    compile_record = qualify_warpx_picmi_compiler(
        compile_run,
        python_executable=warpx_python,
        work_directory=work_root / "compile",
        profile_id="warpx_26_07_picmi_v2_matrix_compile",
    )
    reference = GaussianMixture(components=(GaussianComponent(weight=1.0, drift=0.0, sigma=1.0),))
    analytic_reference = solve_modes(
        reference,
        wavenumber=physical.wavenumber_dimensionless,
    )[0].growth_rate
    analytic_candidate = solve_modes(
        physical.candidate.distribution(),
        wavenumber=physical.wavenumber_dimensionless,
    )[0].growth_rate
    scope = WarpXQualifiedScope(physical=physical)
    record = build_warpx_physics_qualification(
        compile_qualification=compile_record,
        calibration_results=normalized_results,
        scope=scope,
        analytic_reference_growth_rate=analytic_reference,
        analytic_candidate_growth_rate=analytic_candidate,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(record.model_dump_json(indent=2) + "\n")
    results_output = args.output.with_name(args.output.stem + "_results.json")
    results_output.write_text(
        json.dumps(
            [result.model_dump(mode="json") for result in normalized_results],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    qualification_hash = warpx_physics_qualification_hash(record)
    file_hash = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"passed={record.passed}")
    print(f"authorizes_scientific_evidence={record.authorizes_scientific_evidence}")
    print(f"qualification_hash={qualification_hash}")
    print(f"record_file_hash={file_hash}")
    print(f"record={args.output}")
    return 0 if record.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
