#!/usr/bin/env python3
"""Executable contract fixture; it is deliberately not a physics simulator."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def case(name: str, growth: float, classification: str) -> dict[str, object]:
    ratio = math.exp(14.0 * growth)
    return {
        "case_name": name,
        "solver_converged": True,
        "finite_values": True,
        "diagnostic_samples": 201,
        "effective_growth_rate_omega_pe": growth,
        "early_rms_amplitude_v_m": 1.0,
        "late_rms_amplitude_v_m": ratio,
        "amplitude_ratio": ratio,
        "early_window_sample_count": 41,
        "late_window_sample_count": 41,
        "classification": classification,
        "fundamental_amplitude_initial_v_m": 1.0,
        "fundamental_amplitude_final_v_m": 2.0,
        "initial_density_normalized": 1.0,
        "initial_mean_velocity_normalized": 0.0,
        "initial_variance_normalized": 1.0,
        "relative_energy_drift": 0.001,
        "relative_gauss_residual": 0.002,
        "relative_charge_imbalance": 0.001,
        "diagnostic_manifest_hash": "a" * 64,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--work-directory", type=Path, required=True)
    args = parser.parse_args()
    package = json.loads(args.package.read_text())
    assert package["adapter_name"] == "warpx_picmi"
    assert package["payload"]["contract_version"] == "warpx_picmi_pair_v1"
    assert args.work_directory.is_dir()
    result = {
        "contract_version": "warpx_picmi_pair_v1",
        "runtime_warpx_version": "26.7",
        "reference": case("unit_maxwellian_reference", -0.15, "damped"),
        "candidate": case("symmetric_mixture_candidate", 0.25, "unstable"),
    }
    args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
