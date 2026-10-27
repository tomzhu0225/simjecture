"""Interpret the configured one-atom bcc Fe commissioning case, never a core adapter."""

import argparse
import json
import re
import runpy
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("result", type=Path)
parser.add_argument("--relax-xml", type=Path, help="Explicit preserved optimization XML evidence")
parser.add_argument(
    "--output", type=Path, help="New reassessment report; existing paths are refused"
)
args = parser.parse_args()
root = args.result
output = args.output or root / "fe_reference_reassessment.json"
if output.exists():
    parser.error("Use a new reassessment output; historical reports are preserved")
workflow = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "skills/quantum-espresso/examples/dft_workflow.py")
)
qualification = workflow["reference_qualification"](root, args.relax_xml)
if qualification["status"] != "qualified":
    report = {
        "scope": "Completion reassessment only; historical observations are not requalified",
        "qualification": qualification,
        "checks": {"workflow_passed": False},
    }
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False))
    raise SystemExit(1)
summary = json.loads((root / "summary.json").read_text())
structure = json.loads((root / "final_structure.json").read_text())
cfg = summary["configuration"]
cell = np.asarray(structure["cell_angstrom"])
a = float((2 * np.linalg.det(cell)) ** (1 / 3))
mag = summary["magnetization"]
mean = mag["mean_total_muB_per_atom"]
controls = summary.get("convergence", [])
higher_cutoffs = [r for r in controls if r["settings"].get("ecutwfc_ry", 0) > cfg["ecutwfc_ry"]]
cutoff = min(higher_cutoffs, key=lambda r: r["settings"]["ecutwfc_ry"]) if higher_cutoffs else None
krows = [
    r
    for r in controls
    if "scf_k" in r["settings"]
    and all(x > y for x, y in zip(r["settings"]["scf_k"], cfg["scf_k"], strict=True))
]
kgrid = min(krows, key=lambda r: np.prod(r["settings"]["scf_k"])) if krows else None
widths = [r for r in controls if "degauss_ry" in r["settings"]]
starts = [r for r in controls if "starting_magnetization" in r["settings"]]


def moment_delta(row):
    value = row["magnetization"]["mean_total_muB_per_atom"]
    return abs(abs(value) - abs(mean))


mapping = {
    int(n): int(ell)
    for n, ell in re.findall(
        r"state #\s*(\d+):[^\n]*l=\s*(\d+)", (root / "bands/projwfc.out").read_text()
    )
}
states = cfg["projection_states"]
dos = np.loadtxt(root / "dos/dos.dat")
fermi = summary["energy_reference"]["value_ev"]
dos_at_fermi = [float(np.interp(fermi, dos[:, 0], dos[:, i])) for i in (1, 2)]
spin_data = np.load(root / "verified_projections.npz")
branch_checks = []
for row in starts:
    initial = next(iter(row["settings"]["starting_magnetization"].values()))
    final = row["magnetization"]["mean_total_muB_per_atom"]
    branch_checks.append(
        {
            "initial_polarization": initial,
            "final_mean_total_muB_per_atom": final,
            "delta_mev_per_atom": row["delta_mev_per_atom"],
            "absolute_moment_difference_muB_per_atom": moment_delta(row),
            "same_or_spin_reversed_branch": bool(
                moment_delta(row) <= 0.05
                and abs(row["delta_mev_per_atom"]) <= 3
                and np.sign(initial) == np.sign(final)
            ),
        }
    )
checks = {
    "workflow_passed": qualification["status"] == "qualified",
    "one_atom_bcc_reference": len(structure["atoms"]) == 1,
    "broad_PBE_lattice_range": 2.7 <= a <= 3.0,
    "broad_FM_moment_range": mean is not None and 1.8 <= mean <= 2.6,
    "two_spin_outputs": summary["spin_components"] == 2
    and spin_data["spin_labels"].tolist() == ["up", "down"],
    "no_insulator_gap_gate": summary["path_gap_ev"] is None,
    "finite_spectral_weight_at_scf_fermi": all(np.isfinite(dos_at_fermi))
    and sum(dos_at_fermi) > 1e-4,
    "configured_markers_match_Fe_d_states": bool(states)
    and all(mapping.get(x) == 2 for x in states),
    "higher_cutoff_2mev_per_atom": cutoff is not None and abs(cutoff["delta_mev_per_atom"]) <= 2,
    "denser_k_3mev_per_atom": kgrid is not None and abs(kgrid["delta_mev_per_atom"]) <= 3,
    "cutoff_and_k_moment_stability_005muB": cutoff is not None
    and kgrid is not None
    and moment_delta(cutoff) <= 0.05
    and moment_delta(kgrid) <= 0.05,
    "smaller_width_moment_stability_005muB": bool(widths)
    and all(moment_delta(row) <= 0.05 for row in widths),
    "multiple_starting_polarizations_checked": len(starts) >= 3
    and all(row["same_or_spin_reversed_branch"] for row in branch_checks),
}
report = {
    "scope": "bcc Fe PBE instrument commissioning; not held-out scientific evidence",
    "qualification": qualification,
    "measured": {
        "conventional_lattice_angstrom": a,
        "magnetization": mag,
        "final_scf_fermi_energy_ev": fermi,
        "spin_DOS_at_scf_fermi_states_per_ev_cell": dos_at_fermi,
        "spin_band_slices": spin_data["band_slices"].tolist(),
        "path_k_points": int(spin_data["k"].shape[0]),
        "selected_projector_l": {str(x): mapping.get(x) for x in states},
    },
    "reference_context": {
        "PBE_FLAPW_lattice_angstrom": 2.83,
        "PBE_FLAPW_mean_moment_muB_per_atom": 2.22,
        "delta_lattice_angstrom": a - 2.83,
        "delta_mean_total_moment_muB_per_atom": mean - 2.22,
        "source": "https://arxiv.org/pdf/1005.0297 (Rahman et al., PRB81,184423,2010)",
        "comparability": (
            "Different all-electron/PP method, grids and smearing; "
            "broad physical-scale context only"
        ),
    },
    "numerical_controls": controls,
    "starting_polarization_results": branch_checks,
    "checks": checks,
    "limitations": [
        (
            "Total and absolute moments integrate different spin-density quantities; "
            "per-atom means are not site moments."
        ),
        "Smearing width is a numerical parameter, not a physical magnetic temperature.",
        (
            "Variational energies at different smearing widths are not judged by "
            "the same-functional cutoff/k tolerance."
        ),
        (
            "Finite broadened DOS on a selected grid/path does not prove the complete "
            "zero-temperature Fermi surface."
        ),
        "These checks do not establish all stress, lattice, DOS or magnetic-phase error bounds.",
        "No SOC/noncollinear or autonomous LLM/API validation is implied.",
    ],
}
output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
