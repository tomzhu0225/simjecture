"""Check retained bytes and recompute comparisons; no solver or model API calls."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from pathlib import Path


def close(actual: float, expected: float) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-11, abs_tol=1e-14):
        raise AssertionError((actual, expected))


def verify(repository: Path) -> dict:
    demo = repository / "demos/qin1_multiphysics"
    manifest = json.loads((demo / "manifest.json").read_text())
    for name, expected in manifest.items():
        path = repository / name
        if not path.resolve().is_relative_to(repository.resolve()):
            raise AssertionError(f"Out-of-repository path: {name}")
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected:
            raise AssertionError(f"Changed retained artifact: {name}")
        if path.suffix in {".json", ".html"} and b"/home/" in payload:
            raise AssertionError(f"Private host path: {name}")

    def read(name: str) -> dict:
        return json.loads((demo / "record" / name).read_text())

    em = read("em.json")
    for case in em["cases"].values():
        close(max(case["B7_T"]), case["peak_B7_T"])
        close(max(case["array_current_kA"]), case["peak_Iarray_kA"])
        close(max(case["coil_current_kA"]), case["peak_Icoil_kA"])
    for comparison in em["matched_comparisons"].values():
        old = em["cases"][comparison["reference"]]
        new = em["cases"][comparison["candidate"]]
        close(new["peak_B7_T"] / old["peak_B7_T"] - 1, comparison["B7_gain"])
        close(new["peak_Iarray_kA"] / old["peak_Iarray_kA"], comparison["array_retention"])
        close(
            new["patch"]["3"]["mean_pressure_proxy_MPa"]
            / old["patch"]["3"]["mean_pressure_proxy_MPa"]
            - 1,
            comparison["disk_mean_pressure_proxy_gain"],
        )

    plasma = read("plasma.json")
    plan = read("comparison-plan.json")
    cases = {case["case"]: case for case in plasma["records"]}
    reference = cases["thin-on-compact-220ns"]["common_metrics"]
    tolerances = {
        v
        for k, v in plan["quantitative_claim_gates"].items()
        if k.startswith("relative_forward_flux_")
    }
    assert len(tolerances) == 1
    flux_tolerance = tolerances.pop()
    edge_tolerance = plan["secondary_density_edge"][
        "prospective_mesh_dt_ppc_floor_domain_displacement_tolerance_mm"
    ]
    for control in plasma["sensitivity"]:
        measured = cases[control["case"]]["common_metrics"]
        flux_change = (
            measured["fixed_plane"]["positive_bulk_mass_flux_kg_s"]
            / reference["fixed_plane"]["positive_bulk_mass_flux_kg_s"]
            - 1
        )
        edge_shift = 1e3 * (measured["density_edge"]["x_m"] - reference["density_edge"]["x_m"])
        close(flux_change, control["relative_flux_change"])
        close(edge_shift, control["density_edge_shift_mm"])
        assert control["flux_within_10percent"] == (abs(flux_change) < flux_tolerance)
        assert control["edge_within_1mm"] == (abs(edge_shift) < edge_tolerance)
    checks = read("checks.json")
    for execution in checks["plasma_executions"]:
        case = cases[execution["case"]]
        assert execution["full_220ns_request_completed"] == case["complete_requested_220ns"]
        assert execution["finite_200ns_available"] == (
            case["common_time_available"] and case["common_metrics"]["finite"]
        )
    assert not checks["physical_shot_validated"] and not checks["bow_shock_verified"]
    assert not read("study.json")["formal_harness_adjudication"]

    html = (repository / "docs/_static/demos/qin1/viewer.html").read_text()
    embedded = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    assert embedded is not None
    viewer = json.loads(embedded.group(1))
    cells = math.prod(viewer["shape_yx"])
    sources = {item["case"]: item for item in read("raw-source-identities.json")["records"]}
    for case in viewer["cases"]:
        comparison = cases[case["name"]]
        assert len(case["frames"]) == len(viewer["time_ns"])
        for frame in case["frames"]:
            for field in ("density", "velocity", "B"):
                assert len(base64.b64decode(frame[field], validate=True)) == 4 * cells
        assert case["frames"][-1]["readout"] == comparison["common_metrics"]["fixed_plane"]
        assert case["frames"][-1]["edge"] == comparison["common_metrics"]["density_edge"]
        assert case["frames"][-1]["source"] == sources[case["name"]]["source_file"]
        assert case["input_sha256"] == sources[case["name"]]["input_sha256"]
    return {
        "retained_files_verified": len(manifest),
        "matched_EM_comparisons_recomputed": len(em["matched_comparisons"]),
        "plasma_controls_recomputed": len(plasma["sensitivity"]),
        "failed_flux_checks": sum(
            not item["flux_within_10percent"] for item in plasma["sensitivity"]
        ),
        "passed_edge_checks": sum(item["edge_within_1mm"] for item in plasma["sensitivity"]),
        "viewer_cases_checked": len(viewer["cases"]),
        "scope": (
            "Retained excerpt integrity and arithmetic only; no raw-field verification, "
            "solver rerun or scientific acceptance."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(verify(Path(__file__).resolve().parents[2]), indent=2))
