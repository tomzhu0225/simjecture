"""Publish a bounded excerpt of an existing Qin-1 campaign; never run solvers."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

FIGURES = (
    "paired_feed_geometry",
    "paired_feed_fields",
    "plasma_hardware_overlap",
    "plasma_sensitivity",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(campaign: Path, repository: Path) -> None:
    demo = repository / "demos/qin1_multiphysics"
    record = demo / "record"
    assets = repository / "docs/_static/demos/qin1"
    record.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)
    source_files: dict[str, str] = {}

    def read(name: str) -> dict:
        path = campaign / name
        source_files[name] = sha(path)
        return json.loads(path.read_text())

    def write(name: str, data: dict) -> None:
        text = json.dumps(data, indent=2, allow_nan=False) + "\n"
        if "/home/" in text or "/tmp/" in text:
            raise ValueError(f"Private host path in public excerpt: {name}")
        (record / name).write_text(text)

    design = read("design-results.json")
    audit = read("reports/campaign-evidence-audit.json")
    if not audit["final"] or audit["unfinished_records"] or audit["live_campaign_native_pids"]:
        raise ValueError("Export requires terminal campaign records.")
    write(
        "em.json",
        {
            "scope": design["scope"],
            "cases": {
                name: {key: value for key, value in case.items() if key != "case"}
                for name, case in design["cases"].items()
            },
            "matched_comparisons": design["paired_matched_comparisons"],
        },
    )
    write("plasma.json", read("plasma-comparison.json"))
    write("comparison-plan.json", read("plasma/comparison-plan.json"))
    write("model.json", read("plasma/plumes/thin-on-compact-220ns/plan.json"))
    write("raw-source-identities.json", read("reports/common-window-source-manifest.json"))

    imports = {}
    for name, item in audit["static_imports"].items():
        imports[name] = {
            k: v for k, v in item.items() if k not in {"case", "data", "source_EM_case"}
        }
    executions = []
    for item in audit["plasma_records"]:
        execution = item["execution"]
        executions.append(
            {
                "case": item["case"],
                "full_220ns_request_completed": item["full_220ns_request_completed"],
                "all_saved_fields_finite": item["all_saved_fields_finite"],
                "finite_200ns_available": item["finite_200ns_available"],
                "last_saved_ns": item["last_saved_ns"],
                "returncode": execution.get(
                    "returncode", execution.get("exit_code_observed_from_process_tool")
                ),
                "reason": execution.get(
                    "reason", "Native process completed; analysis recorded separately."
                ),
            }
        )
    write(
        "checks.json",
        {
            "scope": (
                "Recorded numerical and execution checks; no formal harness claim review "
                "or physical-shot validation."
            ),
            "selected_CAD_checks": audit["selected_CAD_checks"],
            "matched_EM_records": audit["matched_EM_records"],
            "static_imports": imports,
            "field_off_control": audit["field_off_control"],
            "plasma_executions": executions,
            "physical_shot_validated": False,
            "bow_shock_verified": False,
        },
    )
    runtime = read("plasma/native-runtime.json")
    static_control = read("plasma/commissioning/static-A-n32/control.json")
    if static_control["binary_sha256"] != runtime["sha256"]:
        raise ValueError("Control and production binary identities differ.")
    build_path = campaign.parent / "optimization-20261023/solver-stable-gram/build-record.json"
    build = json.loads(build_path.read_text())
    source_files["../optimization-20261023/solver-stable-gram/build-record.json"] = sha(build_path)
    write(
        "study.json",
        {
            "study_dates": ["2026-10-23", "2026-10-24"],
            "workflow": (
                "Operator-assisted host execution using Simjecture tools and skills, "
                "custom coupling/analysis scripts and a native WarpX binary."
            ),
            "formal_harness_adjudication": False,
            "human_framing": (
                "Improve a Qin-1 wire-array/magnetic-obstacle design for plasma deflection "
                "and a clear boundary; select the 2026 short-circuit condition; "
                "Al or W wires with other source parameters unknown; "
                "authorize overnight exploration."
            ),
            "agent_work": (
                "CAD variants, coupled EM/circuit solves, field transfer, native 3D plasma "
                "controls, analysis, recovery and illustrated reporting."
            ),
            "review": (
                "Numerical controls, artifact checks and report inspection by the working "
                "assistant; no separate formal scientific adjudication."
            ),
            "software": {
                "CAD_and_mesh": "Gmsh/OpenCASCADE; FreeCAD was not used for these geometry edits.",
                "Elmer": {
                    "version": "26.2.1",
                    "source_commit": build["base_source_commit"],
                    "isolated_core_sha256": build["core_sha256"],
                },
                "WarpX": {
                    "version": static_control["softwareVersion"],
                    "binary_sha256": runtime["sha256"],
                    "model": "Native 3D CUDA hybrid PIC; not the packaged 2D PICMI capability.",
                },
                "visualization": "Python, PyVista/VTK and Matplotlib",
                "FLASH": "Local source assessed; no FLASH plasma evolution in this study.",
            },
            "selected_design": {
                "turns": 3,
                "mean_diameter_mm": 8,
                "copper_diameter_mm": 1.5,
                "pitch_mm": 2.5,
                "feeds": "paired; fixture and clearance changes required",
            },
            "coupling": (
                "One-way: full retained-device magnetic field at 500 ns, held fixed on a "
                "separate plasma clock. No plasma-to-circuit feedback."
            ),
            "source_anchor": {
                "voltage_kV": "+/-40",
                "short_circuit_peak_kA": 370,
                "rise_10_90_ns": 275,
                "doi": "10.7498/aps.75.20260383",
                "status": (
                    "Published anchor selected by operator; effective capacitance and "
                    "fixture mapping remain assumptions."
                ),
            },
            "public_excerpt": (
                "Selected numerical histories, comparison metrics, checks, source identities, "
                "figures and viewer. Raw fields, CAD, installed solvers and private host paths "
                "are not distributed here; this is not a turnkey solver rerun."
            ),
        },
    )
    for name in FIGURES:
        for suffix in ("png", "pdf"):
            path = campaign / "plots" / f"{name}.{suffix}"
            source_files[str(path.relative_to(campaign))] = sha(path)
            shutil.copyfile(path, assets / path.name)
    viewer_path = campaign / "Qin1_Results_Viewer.html"
    source_files[viewer_path.name] = sha(viewer_path)
    viewer = viewer_path.read_text()
    old_link = 'href="Qin1_Overnight_Optimization_and_Plasma_Report.pdf"'
    if viewer.count(old_link) != 1:
        raise ValueError("Unexpected original viewer report link.")
    viewer = viewer.replace(old_link, 'href="../../../demos/qin1-hardware-plasma.html"')
    viewer = viewer.replace(">the PDF report</a>", ">the case study</a>")
    if "/home/" in viewer:
        raise ValueError("Private host path in viewer.")
    (assets / "viewer.html").write_text(viewer)
    write(
        "provenance.json",
        {
            "scope": (
                "Editorial public excerpt of the completed local study. Figures and numerical "
                "values are retained; absolute host paths and unrelated runtime/session details "
                "are omitted."
            ),
            "source_file_sha256": source_files,
            "viewer_edit": (
                "Only the report link and its label change; embedded frames and readouts "
                "are unchanged."
            ),
            "raw_source_availability": (
                "The identified raw diagnostics remain with the original local campaign; "
                "hashes alone do not verify unavailable files."
            ),
        },
    )
    files = sorted(record.glob("*.json")) + sorted(assets.glob("*"))
    manifest = {str(path.relative_to(repository)): sha(path) for path in files}
    (demo / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Exported {len(files)} files; no solver execution.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    export(args.campaign.resolve(), args.repository.resolve())
