"""Si-only interpretation of a completed generic workflow; no absolute-energy comparison."""

import argparse
import json
import runpy
from pathlib import Path

import numpy as np

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("result", type=Path)
p.add_argument("--relax-xml", type=Path, help="Explicit preserved optimization XML evidence")
p.add_argument("--output", type=Path, help="New reassessment report; existing paths are refused")
args = p.parse_args()
root = args.result
output = args.output or root / "si_reference_reassessment.json"
if output.exists():
    p.error("Use a new reassessment output; historical reports are preserved")
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
data = np.load(root / "verified_projections.npz")
energy = data["energies_ev"]
nocc = summary["occupied_bands"]
cell = np.asarray(structure["cell_angstrom"])
a = float((4 * np.linalg.det(cell)) ** (1 / 3))
lengths = np.linalg.norm(cell, axis=1)
angles = [
    float(
        np.degrees(np.arccos(np.clip(np.dot(cell[i], cell[j]) / (lengths[i] * lengths[j]), -1, 1)))
    )
    for i, j in ((0, 1), (0, 2), (1, 2))
]
vertices = [0]
for point in cfg["path"][:-1]:
    vertices.append(vertices[-1] + point["points"])
x = next(vertices[i] for i, point in enumerate(cfg["path"]) if point["label"] == "X")
gamma_direct = float(energy[0, nocc] - energy[0, nocc - 1])
gamma_x = float(energy[x, nocc] - energy[0, nocc - 1])
controls = summary.get("convergence", [])
cutoff = next((r for r in controls if r["settings"].get("ecutwfc_ry") == 60), None)
denser = [
    r
    for r in controls
    if "scf_k" in r["settings"]
    and all(a > b for a, b in zip(r["settings"]["scf_k"], cfg["scf_k"], strict=True))
]
kgrid = min(denser, key=lambda r: np.prod(r["settings"]["scf_k"])) if denser else None
kcheck = "k_" + "x".join(map(str, cfg["scf_k"])) + "_to_"
kcheck += "x".join(map(str, kgrid["settings"]["scf_k"])) if kgrid else "unmeasured"
kcheck += "_2mev_per_atom"
report = {
    "scope": "Si PBE exploratory reference; not held-out scientific evidence",
    "qualification": qualification,
    "measured": {
        "conventional_lattice_angstrom": a,
        "path_sampled_indirect_gap_ev": summary["path_gap_ev"],
        "gamma_direct_gap_ev": gamma_direct,
        "gamma_to_x_endpoint_ev": gamma_x,
    },
    "primitive_metric": {
        "lengths_angstrom": lengths.tolist(),
        "angles_degrees": angles,
        "relative_length_spread": float(np.ptp(lengths) / np.mean(lengths)),
        "max_angle_departure_from_60_degrees": max(abs(x - 60) for x in angles),
    },
    "external_comparison": {
        "PBE_lattice_angstrom": 5.466,
        "delta_lattice_angstrom": a - 5.466,
        "lattice_source": "https://arxiv.org/abs/0903.4037 (Table II, different implementation)",
        "GPAW_gamma_direct_ev": 2.559,
        "GPAW_gamma_x_endpoint_ev": 0.707,
        "band_source": "https://gpaw.readthedocs.io/tutorialsexercises/electronic/pbe0/pbe0.html",
        "comparability": (
            "Different PP, lattice and basis; physical scale only; no tight numerical identity"
        ),
    },
    "checks": {
        "workflow_passed": qualification["status"] == "qualified",
        "broad_PBE_lattice_range": 5.44 <= a <= 5.50,
        "50_to_60_Ry_2mev_per_atom": None
        if cutoff is None
        else abs(cutoff["delta_mev_per_atom"]) <= 2,
        kcheck: None if kgrid is None else abs(kgrid["delta_mev_per_atom"]) <= 2,
    },
    "limitations": [
        "Sampled path gap does not prove the global band extremum.",
        "Pairwise energy checks do not establish a complete stress, lattice or DOS error bound.",
        (
            "PBE gaps are not experimental quasiparticle gaps; "
            "absolute total energies are not cross-compared."
        ),
    ],
}
output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))

# A printed report is not a qualification pass when a required control is absent or fails.
raise SystemExit(0 if all(value is True for value in report["checks"].values()) else 1)
