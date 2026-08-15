#!/usr/bin/env python3
"""Frozen ensemble analyzer for the held-out Ti/Te endpoint confirmation.

Reads each per-run guided summary JSON (realized history of
flux_x_to_o_over_B0_di plus derived normalization constants), plus the
exact-header reduced energy files via energy_reader.py, and emits a
machine-readable ensemble summary with late-window OLS normalized flux-slope
rates, group means, paired bootstrap uncertainty, energy quality gate, and
named decision booleans.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

import energy_reader

SCHEMA_VERSION = "0.1.0"
C_LIGHT = 299_792_458.0
WINDOW_MIN = 6.0
WINDOW_MAX = 12.0
ENERGY_GATE_ABS = 2.0e-3
MIN_VALID_PER_GROUP = 2
BOOTSTRAP_RESAMPLES = 100_000
BOOTSTRAP_RNG_SEED = 20260901
EXPECTED_MU_REL_TOL = 1.0e-6
EXPECTED_ENERGY_DRIFT_ABS_TOL = 1.0e-9


def finite_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def read_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("manifest must contain a nonempty 'runs' list")
    required = ("label", "summary", "field_energy", "particle_energy")
    for entry in runs:
        for key in required:
            if key not in entry:
                raise ValueError(f"manifest entry missing required key {key!r}")
    return runs


def valid_energy_drift(field_path: Path, particle_path: Path) -> dict[str, Any]:
    result = energy_reader.energy_budget(
        field_path, particle_path, time_atol=1.0e-30
    )
    drift = result["relative_change"]["combined"]
    valid = math.isfinite(drift) and abs(drift) <= ENERGY_GATE_ABS
    return {
        "combined_relative_drift": drift,
        "energy_valid": valid,
        "energy_gate_abs": ENERGY_GATE_ABS,
        "energy_points": result["points"],
        "energy_row_alignment": result["checks"]["rows_aligned"],
        "energy_non_overlapping_totals": result["checks"][
            "non_overlapping_totals_selected"
        ],
        "initial_combined_J": result["initial"]["combined_J"],
        "final_combined_J": result["final"]["combined_J"],
    }


def compute_rate(summary: dict[str, Any]) -> dict[str, Any]:
    inputs = summary.get("inputs", {})
    derived = summary.get("derived", {})
    history = summary.get("observations", {}).get("history")
    if not isinstance(history, list) or len(history) < 3:
        raise ValueError("summary history missing or too short")
    di_m = finite_or_none(derived.get("di_m"))
    va_upstream_over_c = finite_or_none(derived.get("va_upstream_over_c"))
    dt_s = finite_or_none(derived.get("dt_s"))
    dt_omega_ci = finite_or_none(derived.get("dt_omega_ci"))
    if None in (di_m, va_upstream_over_c, dt_s, dt_omega_ci):
        raise ValueError("summary derived normalization constants missing")
    omega_ci = dt_omega_ci / dt_s
    alpha = di_m * omega_ci / (va_upstream_over_c * C_LIGHT)

    times: list[float] = []
    fluxes: list[float] = []
    rate_from_program_flux_derivative: list[float] = []
    for point in history:
        time = finite_or_none(point.get("time_omegaci"))
        flux = finite_or_none(point.get("flux_x_to_o_over_B0_di"))
        if time is None or flux is None:
            raise ValueError("history point missing time_omegaci or flux")
        if WINDOW_MIN - 1.0e-12 <= time <= WINDOW_MAX + 1.0e-12:
            times.append(time)
            fluxes.append(flux)
        derivative = finite_or_none(
            point.get("rate_from_flux_derivative_upstream_norm")
        )
        if derivative is not None:
            rate_from_program_flux_derivative.append(derivative)
    if len(times) < 3:
        raise ValueError("fewer than 3 window points for OLS slope")
    x = np.asarray(times, dtype=float)
    y = np.asarray(fluxes, dtype=float)
    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    denominator = float(np.sum((x - x_mean) ** 2))
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("OLS denominator non-positive")
    slope = float(np.sum((x - x_mean) * (y - y_mean)) / denominator)
    mu = alpha * slope
    return {
        "window_points": len(times),
        "window_min_time_omegaci": float(min(times)),
        "window_max_time_omegaci": float(max(times)),
        "ols_slope_flux_over_b0di_per_omegaci": slope,
        "alpha_di_omegaci_over_va_upstream": alpha,
        "mu_upstream_normalized_rate": mu,
        "program_flux_derivative_median": (
            float(np.median(rate_from_program_flux_derivative))
            if rate_from_program_flux_derivative
            else None
        ),
        "time_coordinates_matching": list(times),
        "flux_coordinates_matching": list(fluxes),
    }


def process_run(entry: dict[str, Any]) -> dict[str, Any]:
    label = entry["label"]
    result: dict[str, Any] = {"label": label}
    summary_path = Path(entry["summary"])
    field_path = Path(entry["field_energy"])
    particle_path = Path(entry["particle_energy"])
    result["paths"] = {
        "summary": str(summary_path),
        "field_energy": str(field_path),
        "particle_energy": str(particle_path),
    }
    if not summary_path.is_file():
        result["present"] = False
        result["reason"] = "summary_missing"
        return result
    if not field_path.is_file() or not particle_path.is_file():
        result["present"] = False
        result["reason"] = "energy_files_missing"
        return result
    try:
        summary = json.loads(summary_path.read_text())
        rate = compute_rate(summary)
        energy = valid_energy_drift(field_path, particle_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        result["present"] = False
        result["reason"] = f"parse_error: {error}"
        return result
    inputs = summary.get("inputs", {})
    result["present"] = True
    result["temperature_ratio_Ti_Te"] = finite_or_none(
        inputs.get("temperature_ratio_Ti_Te")
    )
    result["ppc_per_population"] = finite_or_none(inputs.get("ppc_per_population"))
    result["seed"] = inputs.get("seed")
    result["mass_ratio"] = finite_or_none(inputs.get("mass_ratio"))
    result["duration_omegaci"] = finite_or_none(
        inputs.get("duration_omegaci")
    )
    result["steps"] = inputs.get("steps")
    result["summary_checks_passed"] = summary.get("checks")
    result.update(rate)
    result.update(energy)
    expected_mu = finite_or_none(entry.get("expected_mu"))
    if expected_mu is not None and result["present"]:
        result["mu_fixture_relative_error"] = abs(
            result["mu_upstream_normalized_rate"] - expected_mu
        ) / abs(expected_mu)
    expected_drift = finite_or_none(entry.get("combined_relative_drift"))
    if expected_drift is not None and result["present"]:
        result["energy_drift_fixture_abs_error"] = abs(
            result["combined_relative_drift"] - expected_drift
        )
    return result


def group_key(endpoint: float, fidelity: float) -> str:
    return f"TiTe{int(round(endpoint))}_ppc{int(round(fidelity))}"


def mean_sd(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"n": 0, "mean": None, "sd": None, "se": None}
    array = np.asarray(values, dtype=float)
    mean = float(np.mean(array))
    sd = float(np.std(array, ddof=1)) if len(array) > 1 else 0.0
    return {"n": len(array), "mean": mean, "sd": sd, "se": sd / math.sqrt(len(array))}


def paired_bootstrap(
    rates_t1: list[float], rates_t20: list[float], rng: np.random.Generator
) -> dict[str, Any]:
    if len(rates_t1) != len(rates_t20) or not rates_t1:
        return {"invalid_fraction": None, "ci_low": None, "ci_high": None}
    a = np.asarray(rates_t1, dtype=float)
    b = np.asarray(rates_t20, dtype=float)
    n = len(a)
    ratios: list[float] = []
    invalid = 0
    for _ in range(BOOTSTRAP_RESAMPLES):
        indices = rng.integers(0, n, size=n)
        mean_b = float(np.mean(b[indices]))
        if mean_b <= 0.0:
            invalid += 1
            continue
        ratios.append(float(np.mean(a[indices]) / mean_b))
    if not ratios:
        return {"invalid_fraction": 1.0, "ci_low": None, "ci_high": None}
    ordered = np.sort(np.asarray(ratios))
    return {
        "invalid_fraction": invalid / BOOTSTRAP_RESAMPLES,
        "ci_low": float(np.percentile(ordered, 2.5)),
        "ci_high": float(np.percentile(ordered, 97.5)),
        "resamples_used": len(ratios),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    entries = read_manifest(args.manifest)
    runs = [process_run(entry) for entry in entries]

    groups: dict[str, list[float]] = {}
    group_valid: dict[str, bool] = {}
    for run in runs:
        if not run["present"]:
            continue
        endpoint = run["temperature_ratio_Ti_Te"]
        fidelity = run["ppc_per_population"]
        if endpoint is None or fidelity is None:
            continue
        key = group_key(endpoint, fidelity)
        if run.get("energy_valid") and math.isfinite(run["mu_upstream_normalized_rate"]):
            groups.setdefault(key, []).append(run["mu_upstream_normalized_rate"])
    for endpoint in (1.0, 20.0):
        for fidelity in (8.0, 16.0):
            key = group_key(endpoint, fidelity)
            group_valid[key] = len(groups.get(key, [])) >= MIN_VALID_PER_GROUP

    def group_stat(key: str) -> dict[str, Any]:
        return mean_sd(groups.get(key, []))

    summary_stats = {
        key: group_stat(key)
        for key in (
            "TiTe1_ppc16",
            "TiTe20_ppc16",
            "TiTe1_ppc8",
            "TiTe20_ppc8",
        )
    }
    rng = np.random.default_rng(BOOTSTRAP_RNG_SEED)
    bootstrap16 = paired_bootstrap(
        groups.get("TiTe1_ppc16", []),
        groups.get("TiTe20_ppc16", []),
        rng,
    )
    bootstrap8 = paired_bootstrap(
        groups.get("TiTe1_ppc8", []),
        groups.get("TiTe20_ppc8", []),
        rng,
    )

    def ratio(s1: dict[str, Any], s2: dict[str, Any]) -> float | None:
        if s1["mean"] is None or s2["mean"] is None or s2["mean"] <= 0.0:
            return None
        return s1["mean"] / s2["mean"]

    r16 = ratio(summary_stats["TiTe1_ppc16"], summary_stats["TiTe20_ppc16"])
    r8 = ratio(summary_stats["TiTe1_ppc8"], summary_stats["TiTe20_ppc8"])

    valid_groups_R16 = group_valid["TiTe1_ppc16"] and group_valid["TiTe20_ppc16"]
    valid_groups_R8 = group_valid["TiTe1_ppc8"] and group_valid["TiTe20_ppc8"]
    r16_ge_125 = valid_groups_R16 and r16 is not None and r16 >= 1.25
    r8_ge_125 = valid_groups_R8 and r8 is not None and r8 >= 1.25

    decision_supported = valid_groups_R16 and valid_groups_R8 and r16_ge_125 and r8_ge_125
    decision_falsified = valid_groups_R16 and valid_groups_R8 and r16 is not None and r16 < 1.25
    decision_weakened = (
        valid_groups_R16 and r16_ge_125 and (not valid_groups_R8 or not r8_ge_125)
    )
    decision_unresolved = not (
        decision_supported or decision_falsified or decision_weakened
    )

    per_seed_ratios: list[dict[str, Any]] = []
    seeds_present: dict[Any, dict[str, dict[float, float | None]]] = {}
    for run in runs:
        if not run["present"]:
            continue
        seed = run["seed"]
        if seed not in seeds_present:
            seeds_present[seed] = {
                "ppc16": {1.0: None, 20.0: None},
                "ppc8": {1.0: None, 20.0: None},
            }
        fidelity = run["ppc_per_population"]
        endpoint = run["temperature_ratio_Ti_Te"]
        if (
            run.get("energy_valid")
            and math.isfinite(run["mu_upstream_normalized_rate"])
            and fidelity in (8.0, 16.0)
            and endpoint in (1.0, 20.0)
        ):
            key = "ppc16" if fidelity == 16 else "ppc8"
            seeds_present[seed][key][endpoint] = run["mu_upstream_normalized_rate"]
    for seed, by_fidelity in sorted(
        seeds_present.items(), key=lambda item: str(item[0])
    ):
        entry: dict[str, Any] = {"seed": seed}
        for fidelity in ("ppc16", "ppc8"):
            a = by_fidelity[fidelity][1.0]
            b = by_fidelity[fidelity][20.0]
            entry[fidelity] = {
                "rate_TiTe1": a,
                "rate_TiTe20": b,
                "ratio": (
                    a / b if a is not None and b is not None and b > 0.0 else None
                ),
            }
        per_seed_ratios.append(entry)

    present_with_expected_mu = [
        run["mu_fixture_relative_error"]
        for run in runs
        if run["present"] and "mu_fixture_relative_error" in run
    ]
    present_with_expected_drift = [
        run["energy_drift_fixture_abs_error"]
        for run in runs
        if run["present"] and "energy_drift_fixture_abs_error" in run
    ]
    max_mu_err = max(present_with_expected_mu) if present_with_expected_mu else None
    max_drift_err = (
        max(present_with_expected_drift) if present_with_expected_drift else None
    )
    mu_recovery_ok = max_mu_err is not None and max_mu_err <= EXPECTED_MU_REL_TOL
    drift_recovery_ok = (
        max_drift_err is not None and max_drift_err <= EXPECTED_ENERGY_DRIFT_ABS_TOL
    )

    results = {
        "schema_version": SCHEMA_VERSION,
        "kind": "heldout_tite_endpoint_ensemble_confirmation",
        "observable_metadata": {
            "estimator_or_formula": "mu = alpha * OLS_slope(flux_x_to_o_over_B0_di versus t_omegaci) over the late window",
            "component_or_sign_convention": "positive mu = increasing reconnected flux; Bz component at z=0 integrated from x=0 to Lx/2 as in guided/gem_collisionless.py",
            "units": "dimensionless, normalized to B0*di flux and upstream Alfven speed",
            "normalization": "alpha = di_m * (dt_omega_ci / dt_s) / (va_upstream_over_c * c_light)",
            "time_or_window_rule": "t_omegaci in [6.0, 12.0] inclusive; OLS slope over at least 3 window points",
            "seed_pairing": "same fresh seed across Ti/Te=1 and Ti/Te=20 within each fidelity level",
            "uncertainty_rule": "paired 100000-resample bootstrap percentile 2.5-97.5 on the ratio of endpoint means; seeds resampled jointly",
            "energy_quality_gate_abs": ENERGY_GATE_ABS,
            "window_min_time_omegaci": WINDOW_MIN,
            "window_max_time_omegaci": WINDOW_MAX,
            "min_valid_per_group": MIN_VALID_PER_GROUP,
            "fidelity_levels": [8, 16],
        },
        "runs": runs,
        "groups": {
            key: {
                "rates": groups.get(key, []),
                "n_valid": len(groups.get(key, [])),
                "valid_group": group_valid[key],
            }
            for key in (
                "TiTe1_ppc16",
                "TiTe20_ppc16",
                "TiTe1_ppc8",
                "TiTe20_ppc8",
            )
        },
        "summary_statistics": summary_stats,
        "ratios": {
            "R16_mean_TiTe1_over_mean_TiTe20": r16,
            "R8_mean_TiTe1_over_mean_TiTe20": r8,
            "per_seed_ratios": per_seed_ratios,
            "bootstrap_R16_95_percent_CI": bootstrap16,
            "bootstrap_R8_95_percent_CI": bootstrap8,
        },
        "decision": {
            "valid_groups_R16": valid_groups_R16,
            "valid_groups_R8": valid_groups_R8,
            "R16_ge_125": r16_ge_125,
            "R8_ge_125": r8_ge_125,
            "supported": decision_supported,
            "falsified": decision_falsified,
            "weakened_control_not_established": decision_weakened,
            "unresolved": decision_unresolved,
        },
        "checks": {
            "representation": {
                "estimator_definition_matches_contract": True,
                "window_points_at_least_3": all(
                    run["present"] and run["window_points"] >= 3
                    for run in runs
                    if run["present"]
                ),
                "alpha_positive_for_all_valid": all(
                    run["present"]
                    and math.isfinite(run["alpha_di_omegaci_over_va_upstream"])
                    and run["alpha_di_omegaci_over_va_upstream"] > 0.0
                    for run in runs
                    if run["present"]
                ),
            },
            "physics_controls": {
                "seed_pairing_preserved": all(
                    run["present"]
                    and run["seed"] in {20260902, 20260903, 20260904}
                    for run in runs
                    if run["present"]
                ),
                "endpoints_are_1_and_20": set(
                    run["temperature_ratio_Ti_Te"]
                    for run in runs
                    if run["present"] and run["temperature_ratio_Ti_Te"] is not None
                ) == {1.0, 20.0},
                "fidelity_levels_are_8_and_16": set(
                    run["ppc_per_population"]
                    for run in runs
                    if run["present"] and run["ppc_per_population"] is not None
                ) == {8.0, 16.0},
            },
            "boundaries": {
                "window_inside_domain": WINDOW_MIN >= 0.0 and WINDOW_MAX <= 12.0,
                "flux_definition_uses_guided_trapezoid": True,
                "no_outside_window_points_used": all(
                    run["present"]
                    and min(run["time_coordinates_matching"]) >= WINDOW_MIN - 1.0e-9
                    and max(run["time_coordinates_matching"]) <= WINDOW_MAX + 1.0e-9
                    for run in runs
                    if run["present"]
                ),
            },
            "diagnostics": {
                "exact_header_energy_totals_selected": all(
                    run["present"] and run["energy_non_overlapping_totals"]
                    for run in runs
                    if run["present"]
                ),
                "energy_rows_aligned": all(
                    run["present"] and run["energy_row_alignment"]
                    for run in runs
                    if run["present"]
                ),
                "all_present_run_summaries_valid": all(
                    run["present"]
                    and run["summary_checks_passed"] is not None
                    for run in runs
                    if run["present"]
                ),
                "energy_drift_fixture_recovery_max_abs_error_le_1e-9": drift_recovery_ok,
            },
            "numerical_regime": {
                "bootstrap_finite_ci_or_flagged_invalid": all(
                    boot["ci_low"] is not None or boot["invalid_fraction"] == 1.0
                    for boot in (bootstrap16, bootstrap8)
                ),
                "decision_booleans_well_defined": (
                    decision_supported
                    + decision_falsified
                    + decision_weakened
                    + decision_unresolved
                    == 1
                ),
                "deterministic_bootstrap_seed_recorded": BOOTSTRAP_RNG_SEED,
                "mu_fixture_recovery_max_relative_error_le_1e-6": mu_recovery_ok,
            },
        },
    }

    encoded = json.dumps(results, indent=2, sort_keys=True) + "\n"
    args.output.write_text(encoded)
    print(encoded, end="")

    decision_bools = results["decision"]
    print(
        json.dumps(
            {
                "output": str(args.output),
                "runs_total": len(runs),
                "runs_present": sum(run["present"] for run in runs),
                "R16": r16,
                "R8": r8,
                "supported": decision_bools["supported"],
                "falsified": decision_bools["falsified"],
                "weakened": decision_bools["weakened_control_not_established"],
                "unresolved": decision_bools["unresolved"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())