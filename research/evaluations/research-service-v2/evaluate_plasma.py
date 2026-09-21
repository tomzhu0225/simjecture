"""Recompute a common finite plasma decision from raw fields, independent of agent prose."""

import argparse
import hashlib
import json
from contextlib import suppress
from pathlib import Path

import numpy as np
from plasma_reference import analyze


def decide(cases):
    def select(mode, n, eta, A, interval=0.1, cfl=0.4):
        expected_bounds = {
            k: ("periodic" if mode else ("user" if k.startswith("x") else "outflow"))
            for k in [
                "xl_boundary_type",
                "xr_boundary_type",
                "yl_boundary_type",
                "yr_boundary_type",
            ]
        }
        candidates = [
            r
            for r in cases
            if "error" not in r
            and r.get("mode") == mode
            and r["n"] == n
            and abs(r["eta"] - eta) < 1e-12
            and abs(r["A"] - A) < 1e-12
            and abs(r.get("interval", -1) - interval) < 1e-12
            and abs(r.get("cfl", -1) - cfl) < 1e-12
            and abs(r.get("nu", -1) - 0.002) < 1e-12
            and abs(r.get("phase", -1)) < 1e-12
            and abs(r.get("wavelength", -1) - 0.5) < 1e-12
            and abs(r.get("gamma", -1) - 5 / 3) < 1e-12
            and r.get("boundaries") == expected_bounds
            and abs(r.get("seed", -1) - 1e-6) < 1e-15
            and all(
                r.get("physical_switches", {}).get(k, False)
                for k in [
                    "usehydro",
                    "usemagneticresistivity",
                    "useviscosity",
                    "useexplicitviscosity",
                ]
            )
            and abs(r["final_time"] - (2 if mode == 0 else 0.5)) < 1e-9
            and r["finite"]
            and r["min_density"] > 0
            and r["min_pressure"] > 0
        ]
        return candidates[-1] if candidates else None

    missing = []
    base = {}
    for n in [256, 384]:
        for eta in [0.001, 0.002, 0.004]:
            for A in [0.0, 0.2]:
                row = select(0, n, eta, A)
                if row is None:
                    missing.append(dict(mode=0, n=n, eta=eta, A=A))
                else:
                    base[n, eta, A] = row
    temporal = [select(0, 384, 0.002, A, interval=0.05, cfl=0.2) for A in [0.0, 0.2]]
    if any(r is None for r in temporal):
        missing.append({"kind": "time refinement pair"})
    controls = []
    for n, eta in [(64, 0.02), (128, 0.02), (128, 0.0)]:
        row = select(1, n, eta, 0.0)
        if row is None:
            missing.append(dict(kind="periodic control", n=n, eta=eta))
            continue
        error = abs(row["amplitude_ratio"] / row["analytic_diffusion_ratio"] - 1)
        controls.append(dict(n=n, eta=eta, relative_amplitude_error=error, passed=error <= 0.01))
    partial_grid_checks = []
    for eta in [0.001, 0.002, 0.004]:
        for A in [0.0, 0.2]:
            if (256, eta, A) in base and (384, eta, A) in base:
                change = abs(base[384, eta, A]["D"] / base[256, eta, A]["D"] - 1)
                partial_grid_checks.append(
                    dict(eta=eta, A=A, relative_D_grid_change=change, passed=change <= 0.05)
                )
    if missing:
        return dict(
            required_evidence_complete=False,
            missing=missing,
            controls=controls,
            completed_required_cases=len(base)
            + sum(r is not None for r in temporal)
            + len(controls),
            required_case_count=17,
            partial_grid_checks=partial_grid_checks,
            independently_decidable=False,
            disposition="unresolved",
        )

    def delta(n, eta):
        return abs(base[n, eta, 0.2]["D"] / base[n, eta, 0.0]["D"] - 1)

    time_error = abs(abs(temporal[1]["D"] / temporal[0]["D"] - 1) - delta(384, 0.002))
    comparisons = []
    for eta in [0.001, 0.002, 0.004]:
        change = max(abs(base[384, eta, A]["D"] / base[256, eta, A]["D"] - 1) for A in [0.0, 0.2])
        d = delta(384, eta)
        margin = abs(d - delta(256, eta)) + time_error
        comparisons.append(
            dict(
                eta=eta,
                delta=d,
                margin=margin,
                relative_D_grid_change=change,
                qualified=change <= 0.05,
                lower=max(0, d - margin),
                upper=d + margin,
            )
        )
    valid = all(c["passed"] for c in controls) and all(c["qualified"] for c in comparisons)
    verdict = "unresolved"
    if valid:
        if all(c["upper"] <= 0.05 for c in comparisons):
            verdict = "supported"
        elif any(c["lower"] > 0.05 for c in comparisons):
            verdict = "falsified"
    return dict(
        required_evidence_complete=True,
        independently_decidable=verdict != "unresolved",
        completed_required_cases=17,
        required_case_count=17,
        disposition=verdict,
        comparisons=comparisons,
        controls=controls,
        partial_grid_checks=partial_grid_checks,
        temporal_delta_allowance=time_error,
    )


def scan(directory, cache):
    output = []
    seen = set()
    version = hashlib.sha256(
        Path(__file__).with_name("plasma_reference.py").read_bytes()
    ).hexdigest()
    for snapshot in directory.rglob("sheet_*hdf5_plt_cnt_*"):
        d = snapshot.parent
        if d in seen:
            continue
        seen.add(d)
        files = sorted(d.glob("sheet_*hdf5_plt_cnt_*"))
        identity = hashlib.sha256(
            json.dumps(
                [version, [(str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in files]]
            ).encode()
        ).hexdigest()
        if identity in cache:
            result = cache[identity]
        else:
            try:
                result = analyze(d)
                result.pop("rows", None)
            except Exception as error:
                result = {"error": str(error)}
            cache[identity] = result
        output.append(dict(path=str(d.relative_to(directory)), **result))
    return output


def reported_values(directory, cases):
    """Audit reported integral values against raw fields; allow modest printed rounding."""
    comparisons = []

    def visit(value, path):
        if isinstance(value, list):
            for i, item in enumerate(value):
                visit(item, path + f"[{i}]")
        elif isinstance(value, dict):
            if all(k in value for k in ["n", "eta", "D"]) and (
                "A" in value or "amplitude" in value
            ):
                try:
                    n = int(value["n"])
                    eta = float(value["eta"])
                    A = float(value.get("A", value.get("amplitude")))
                    D = float(value["D"])
                    matching = [
                        r
                        for r in cases
                        if "error" not in r
                        and r.get("mode") == 0
                        and r["n"] == n
                        and abs(r["eta"] - eta) < 1e-12
                        and abs(r["A"] - A) < 1e-12
                        and abs(r["final_time"] - 2) < 1e-9
                    ]
                    if matching:
                        error = min(abs(D - r["D"]) / max(abs(r["D"]), 1e-30) for r in matching)
                        comparisons.append(
                            dict(
                                path=path,
                                relative_error=error,
                                passed=bool(np.isfinite(D) and error <= 0.001),
                            )
                        )
                except (TypeError, ValueError, OverflowError):
                    pass
            for key, item in value.items():
                visit(item, path + "." + key)

    for p in directory.rglob("benchmark-result.json"):
        with suppress(OSError, ValueError):
            visit(json.loads(p.read_text()), str(p.relative_to(directory)))
    return dict(
        comparisons=comparisons,
        all_compared_values_agree=all(x["passed"] for x in comparisons) if comparisons else None,
        relative_tolerance=0.001,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--reference", action="store_true")
    a = p.parse_args()
    cache_path = a.root / "field-analysis-cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    if a.reference:
        cases = []
        for entry in json.loads((a.root / "runs.json").read_text()):
            if entry["returncode"] == 0:
                for case in scan(Path(entry["path"]), cache):
                    cases.append(
                        dict(case, reference_path=entry["path"], reference_index=entry["index"])
                    )
        result = dict(cases=cases, decision=decide(cases))
        (a.root / "independent-decision.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result["decision"], indent=2))
    else:
        results = {}
        for entry in json.loads((a.root / "launch.json").read_text())["runs"]:
            if "finished_at" not in entry:
                continue
            directory = Path(entry["path"])
            cases = scan(directory, cache)
            results[directory.name] = dict(
                **decide(cases),
                raw_field_cases=cases,
                reported_integral_checks=reported_values(directory, cases),
            )
        (a.root / "plasma-independent-checks.json").write_text(json.dumps(results, indent=2) + "\n")
        for name, result in results.items():
            print(name, result["required_evidence_complete"], result["disposition"])
    cache_path.write_text(json.dumps(cache, indent=2) + "\n")


if __name__ == "__main__":
    main()
