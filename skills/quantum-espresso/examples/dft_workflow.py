"""Configurable QE 7.4 scalar/collinear DFT workflow. No material defaults.

Run 'fetch' outside the offline sandbox, then 'run' with a fresh output folder.
All solver inputs, logs, hashes, XML-derived arrays and command receipts are kept.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC
from pathlib import Path

import numpy as np

HARTREE_EV = 27.211386245988
BOHR_ANGSTROM = 0.529177210903
HARTREE_BOHR3_KBAR = 294210.156965221


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


SMEARING_CODES = {
    "gaussian": 0,
    "gauss": 0,
    "mp": 1,
    "methfessel-paxton": 1,
    "mv": -1,
    "cold": -1,
    "marzari-vanderbilt": -1,
    "fd": -99,
    "fermi-dirac": -99,
}
OCCUPATIONS = {"fixed", "smearing", "tetrahedra", "tetrahedra_lin", "tetrahedra_opt"}


def electronic_settings(cfg):
    """Resolve physics settings without inferring a material from its label."""
    spin = cfg.get("spin")
    if spin not in {None, "nonmagnetic", "collinear"} or cfg.get("noncolin") or cfg.get("lspinorb"):
        raise ValueError("Noncollinear/SOC input and spinor postprocessing are not implemented")
    nspin = cfg.get("nspin", 2 if spin == "collinear" else 1)
    if isinstance(nspin, bool) or nspin not in (1, 2):
        raise ValueError("nspin must be 1 or 2; spinor processing is not implemented")
    if spin is not None and nspin != (2 if spin == "collinear" else 1):
        raise ValueError("Conflicting spin and nspin configuration")
    if "tot_magnetization" in cfg:
        raise ValueError(
            "Constrained two-Fermi magnetization is not implemented by this bands workflow"
        )
    occ = cfg["occupations"]
    dos_occ = cfg.get("dos_occupations", "tetrahedra" if occ == "fixed" else occ)
    band_occ = cfg.get("band_occupations", "fixed" if occ.startswith("tetrahedra") else occ)
    if (
        occ not in OCCUPATIONS
        or dos_occ not in OCCUPATIONS
        or band_occ not in {"fixed", "smearing"}
    ):
        raise ValueError("Invalid occupation mode; path bands cannot use tetrahedra")
    smear = cfg.get("smearing")
    width = cfg.get("degauss_ry")
    if "smearing" in (occ, dos_occ, band_occ) and (
        smear not in SMEARING_CODES or width is None or not math.isfinite(width) or width <= 0
    ):
        raise ValueError("Smearing occupations require smearing and positive degauss_ry")
    bz_sum = dos_occ if dos_occ.startswith("tetrahedra") else "smearing"
    dos_smear = cfg.get("dos_smearing", smear or "gaussian")
    dos_width = cfg.get("dos_degauss_ry", width)
    if bz_sum == "smearing" and (
        dos_smear not in SMEARING_CODES
        or dos_width is None
        or not math.isfinite(dos_width)
        or dos_width <= 0
    ):
        raise ValueError("Gaussian DOS integration requires dos_degauss_ry or degauss_ry")
    magnetization = {
        x["label"]: x["starting_magnetization"]
        for x in cfg["species"]
        if "starting_magnetization" in x
    }
    magnetization.update(cfg.get("starting_magnetization", {}))
    if not set(magnetization) <= {x["label"] for x in cfg["species"]}:
        raise ValueError("Starting magnetization species is not configured")
    if any(not math.isfinite(value) for value in magnetization.values()):
        raise ValueError("Invalid starting magnetization")
    if nspin == 1 and any(value != 0 for value in magnetization.values()):
        raise ValueError("Nonzero starting magnetization needs nspin=2")
    if "tot_charge" in cfg and not math.isfinite(cfg["tot_charge"]):
        raise ValueError("Invalid total charge")
    if "scf_nbnd" in cfg and (not isinstance(cfg["scf_nbnd"], int) or cfg["scf_nbnd"] < 1):
        raise ValueError("scf_nbnd must be a positive integer")
    if cfg.get("energy_reference", "auto") not in {"auto", "vbm", "fermi", "absolute"}:
        raise ValueError("Unknown energy_reference")
    if "energy_zero_ev" in cfg and not math.isfinite(cfg["energy_zero_ev"]):
        raise ValueError("Invalid energy_zero_ev")
    return dict(
        nspin=nspin,
        occupations=occ,
        dos_occupations=dos_occ,
        band_occupations=band_occ,
        smearing=smear,
        degauss_ry=width,
        dos_bz_sum=bz_sum,
        dos_smearing=dos_smear,
        dos_degauss_ry=dos_width,
        starting_magnetization=magnetization,
    )


CASE_DEFAULTS = {
    "occupations": "fixed",
    "pdos": True,
    "mixing_beta": 0.5,
    "electron_maxstep": 150,
    "energy_reference": "auto",
    "projection_states": [1],
    "plot_energy_ev": [-8, 8],
    "ecutwfc_ry": 50,
    "ecutrho_ry": 400,
    "conv_thr_ry": 1e-8,
    "forc_conv_thr_ry_bohr": 1e-4,
    "etot_conv_thr_ry": 1e-6,
    "press_conv_thr_kbar": 0.5,
    "cell_dofree": "all",
    "dos_delta_ev": 0.02,
    "command_timeout_seconds": 900,
    "scf_k": [6, 6, 6],
    "relax_k": [6, 6, 6],
    "dos_k": [8, 8, 8],
    "acceptance": {},
    "convergence": [],
    "convergence_acceptance": {},
}
LAUNCHER_DEFAULTS = {"memory_mib": 1024, "workspace_mib": 512, "wall_seconds": 3600}
OBSERVABLES = {
    "path_gap_ev",
    "max_force_ry_bohr",
    "mean_total_magnetization_muB_per_atom",
    "total_magnetization_muB_per_cell",
    "total_energy_ev",
}


def resolve_case(cfg):
    cfg = copy.deepcopy(cfg)
    sources = cfg.pop("_parameter_sources", {})
    for key in cfg:
        if key != "profiles" and not key.startswith("_"):
            sources.setdefault(key, "explicit case")
    for key, value in CASE_DEFAULTS.items():
        if key not in cfg:
            cfg[key] = copy.deepcopy(value)
            sources[key] = "builtin CASE_DEFAULTS"
    limits = cfg.get("launcher_limits", {})
    if not isinstance(limits, dict) or set(limits) - LAUNCHER_DEFAULTS.keys():
        raise ValueError("Unknown launcher_limits")
    for key, value in LAUNCHER_DEFAULTS.items():
        sources.setdefault(
            "launcher_limits." + key,
            sources.get("launcher_limits", "explicit case")
            if key in limits
            else "builtin LAUNCHER_DEFAULTS",
        )
        limits.setdefault(key, value)
        if isinstance(limits[key], bool) or not isinstance(limits[key], int) or limits[key] <= 0:
            raise ValueError("Launcher limits must be positive integers")
    if limits["memory_mib"] < 256 or limits["workspace_mib"] < 64:
        raise ValueError("Choose at least 256 MiB memory and 64 MiB workspace")
    cfg["launcher_limits"] = limits
    sources.setdefault("launcher_limits", "resolved per-field; see launcher_limits.*")
    settings = electronic_settings(cfg)
    for key in (
        "nspin",
        "dos_occupations",
        "band_occupations",
        "dos_smearing",
        "dos_degauss_ry",
        "starting_magnetization",
    ):
        if key not in cfg:
            cfg[key] = settings[key]
            sources[key] = "derived by electronic_settings from disclosed case/defaults"
    cfg["_parameter_sources"] = sources
    return cfg


def load_case(path, profile=None, mode=None):
    cfg = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if any(key.startswith("_") for key in cfg):
        raise ValueError("Reserved internal case fields")
    sources = {key: "explicit case" for key in cfg if key != "profiles"}
    if profile:
        defaults = cfg.get("profiles", {}).get(profile)
        if defaults is None:
            raise ValueError(f"Unknown profile {profile}")
        for key, value in defaults.items():
            if key not in cfg:
                cfg[key] = copy.deepcopy(value)
                sources[key] = f"profile {profile} (fill missing only)"
    cfg["_parameter_sources"] = sources
    cfg = resolve_case(cfg)
    return validate_case(cfg, mode)


def validate_case(cfg, mode=None):
    supported = set(CASE_DEFAULTS) | {
        "schema_version",
        "description",
        "functional",
        "species",
        "atoms",
        "cell_angstrom",
        "nbnd",
        "profiles",
        "path",
        "plot_energy_ev",
        "structure_source",
        "spin",
        "nspin",
        "noncolin",
        "lspinorb",
        "tot_magnetization",
        "tot_charge",
        "scf_nbnd",
        "smearing",
        "degauss_ry",
        "dos_occupations",
        "band_occupations",
        "dos_smearing",
        "dos_degauss_ry",
        "starting_magnetization",
        "energy_zero_ev",
        "launcher_limits",
        "steps",
    }
    unknown = {key for key in cfg if not key.startswith("_")} - supported
    if unknown:
        raise ValueError(f"Unsupported case parameters: {sorted(unknown)}")
    if cfg.get("schema_version") != "1":
        raise ValueError("Unsupported case schema")
    electronic_settings(cfg)
    if not isinstance(cfg.get("pdos", True), bool):
        raise ValueError("pdos must be a boolean")
    if cfg.get("cell_dofree") not in {"all", "shape"}:
        raise ValueError("Explicit ibrav=0 cells support cell_dofree all or shape in this driver")
    cell = np.asarray(cfg["cell_angstrom"], dtype=float)
    if cell.shape != (3, 3) or not np.all(np.isfinite(cell)) or np.linalg.det(cell) <= 0:
        raise ValueError("cell_angstrom must be a finite right-handed 3x3 lattice")
    species = cfg["species"]
    labels = [s["label"] for s in species]
    if len(set(labels)) != len(labels) or not labels:
        raise ValueError("Species labels must be unique and nonempty")
    for s in species:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", s["label"]):
            raise ValueError("Invalid species label")
        if Path(s["pseudo"]).name != s["pseudo"] or "'" in s["pseudo"]:
            raise ValueError("Pseudopotential must be a simple filename")
        if not re.fullmatch(r"[0-9a-f]{64}", s["sha256"]):
            raise ValueError("Each PP requires a SHA256")
        if not math.isfinite(s["mass"]) or s["mass"] <= 0:
            raise ValueError("Invalid species mass")
    if not cfg["atoms"]:
        raise ValueError("Empty structure")
    for atom in cfg["atoms"]:
        if atom["species"] not in labels:
            raise ValueError("Atom species has no pseudopotential mapping")
        pos = np.asarray(atom["fractional"], dtype=float)
        if pos.shape != (3,) or not np.all(np.isfinite(pos)):
            raise ValueError("Invalid atom coordinates")
    if not re.fullmatch(r"[A-Za-z0-9_+-]+", cfg["functional"]):
        raise ValueError("Invalid functional identifier")
    for field in (
        "ecutwfc_ry",
        "ecutrho_ry",
        "conv_thr_ry",
        "forc_conv_thr_ry_bohr",
        "etot_conv_thr_ry",
        "press_conv_thr_kbar",
        "dos_delta_ev",
    ):
        if not math.isfinite(cfg[field]) or cfg[field] <= 0:
            raise ValueError(f"Invalid {field}")
    if not math.isfinite(cfg.get("mixing_beta", 0.5)) or not 0 < cfg.get("mixing_beta", 0.5) <= 1:
        raise ValueError("mixing_beta must be in (0, 1]")
    if (
        not isinstance(cfg.get("electron_maxstep", 150), int)
        or cfg.get("electron_maxstep", 150) < 1
    ):
        raise ValueError("electron_maxstep must be positive")
    if (
        isinstance(cfg["command_timeout_seconds"], bool)
        or not isinstance(cfg["command_timeout_seconds"], (int, float))
        or not math.isfinite(cfg["command_timeout_seconds"])
        or cfg["command_timeout_seconds"] <= 0
    ):
        raise ValueError("command_timeout_seconds must be positive and finite")
    if not isinstance(cfg["nbnd"], int) or cfg["nbnd"] < 1:
        raise ValueError("nbnd must be positive")
    for name in ("relax_k", "scf_k", "dos_k"):
        if len(cfg[name]) != 3 or any(not isinstance(v, int) or v < 1 for v in cfg[name]):
            raise ValueError(f"Invalid {name}")
    if mode == "scf-only":
        return cfg
    if len(cfg["path"]) < 2:
        raise ValueError("A band path requires at least two vertices")
    for point in cfg["path"]:
        if len(point["k"]) != 3 or not np.all(np.isfinite(point["k"])):
            raise ValueError("Invalid path coordinate")
        if not isinstance(point["points"], int) or point["points"] < 1:
            raise ValueError("Invalid path sampling")
    return cfg


def canonical_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def validate_ranges(ranges, allowed):
    if not isinstance(ranges, dict) or set(ranges) - allowed:
        raise ValueError("Unsupported acceptance observable for selected steps")
    for limits in ranges.values():
        if (
            not isinstance(limits, list)
            or len(limits) != 2
            or any(
                isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
                for x in limits
            )
            or limits[0] > limits[1]
        ):
            raise ValueError("Acceptance must use finite ordered [lower, upper] bounds")


def build_plan(cfg, protocol, mode="full", convergence=False, backend="simjecture"):
    if backend not in {"simjecture", "standalone"}:
        raise ValueError("Unsupported execution backend")
    if mode not in {"full", "scf-only"}:
        raise ValueError("Only full or scf-only workflow modes are supported")
    if not isinstance(convergence, bool):
        raise ValueError("convergence selection must be boolean")
    cfg = validate_case(resolve_case(cfg), mode)
    sources = cfg.pop("_parameter_sources")
    cfg.pop("profiles", None)
    if not protocol.strip():
        raise ValueError("A nonempty research protocol is required")
    if mode == "scf-only" and convergence:
        raise ValueError("SCF-only with controls is not implemented; use a full plan")
    steps = (
        ["scf"]
        if mode == "scf-only"
        else ["relax", "scf", "nscf", "dos"]
        + (["pdos"] if cfg["pdos"] else [])
        + ["bands", "projections"]
    )
    if convergence:
        steps.append("controls")
        if not cfg["convergence"]:
            raise ValueError("Controls requested but convergence list is empty")
    if "steps" in cfg and cfg["steps"] != steps:
        raise ValueError("Unsupported or conflicting step combination; no silent mode substitution")
    allowed = OBSERVABLES - ({"path_gap_ev"} if mode == "scf-only" else set())
    if cfg["nspin"] == 1:
        allowed -= {"mean_total_magnetization_muB_per_atom", "total_magnetization_muB_per_cell"}
    if cfg["occupations"] != "fixed":
        allowed -= {"path_gap_ev"}
    validate_ranges(cfg["acceptance"], allowed)
    allowed_control_fields = {
        "ecutwfc_ry",
        "ecutrho_ry",
        "scf_k",
        "degauss_ry",
        "smearing",
        "starting_magnetization",
        "conv_thr_ry",
        "electron_maxstep",
        "mixing_beta",
        "scf_nbnd",
    }
    for control in cfg["convergence"]:
        if not isinstance(control, dict) or not control or set(control) - allowed_control_fields:
            raise ValueError("Unsupported SCF control parameters")
        if cfg["occupations"] != "smearing" and set(control) & {"degauss_ry", "smearing"}:
            raise ValueError("Smearing control is inactive for selected SCF occupations")
        if cfg["nspin"] == 1 and "starting_magnetization" in control:
            raise ValueError("Magnetic control requires collinear spin")
        validate_case(resolve_case(dict(cfg, **control)), "scf-only")
    targets = cfg["convergence_acceptance"]
    if targets and not convergence:
        raise ValueError("Convergence acceptance requires controls in the plan")
    if not isinstance(targets, dict):
        raise ValueError("convergence_acceptance must map control indices to bounds")
    for index, ranges in targets.items():
        if not ranges:
            raise ValueError("Empty control acceptance is not a precision target")
        if not index.isdigit() or int(index) >= len(cfg["convergence"]):
            raise ValueError("Unknown convergence control index")
        allowed_controls = {"delta_mev_per_atom"}
        if cfg["nspin"] == 2:
            allowed_controls.add("delta_abs_mean_total_moment_muB_per_atom")
        validate_ranges(ranges, allowed_controls)
    products = [
        "summary.json",
        "effective_case.json",
        "approved_plan.json",
        "scf/pw.in",
        "scf/pw.out",
        "scf/out/sample.save/data-file-schema.xml",
    ]
    if mode == "full":
        products += [
            "final_structure.json",
            "relax/pw.out",
            "dos/dos.dat",
            "bands/out/sample.save/atomic_proj.xml",
            "bands_dos_pdos.png",
            "bands.csv",
            "verified_projections.npz",
        ]
        products += (
            ["bands/bands.dat"]
            if cfg["nspin"] == 1
            else ["bands/bands_up.dat", "bands/bands_down.dat"]
        )
        if cfg["pdos"]:
            products += ["dos/pdos.pdos_tot", "dos/projwfc.out"]
        if convergence:
            products.append("convergence.json")
    body = {
        "schema_version": "qe-plan-1",
        "execution_backend": backend,
        "mode": mode,
        "convergence": convergence,
        "steps": steps,
        "expected_products": products,
        "inactive_parameters": [
            "path",
            "relax_k",
            "dos_k",
            "pdos",
            "dos_delta_ev",
            "projection_states",
            "press_conv_thr_kbar",
        ]
        if mode == "scf-only"
        else [],
        "effective_case": cfg,
        "parameter_sources": sources,
        "protocol": protocol,
        "protocol_sha256": hashlib.sha256(protocol.encode()).hexdigest(),
        "driver_sha256": digest(__file__),
        "acceptance_semantics": {
            "physical_targets": "requested" if cfg["acceptance"] else "not_requested",
            "numerical_accuracy": "targets_requested" if targets else "not_assessed",
            "algorithmic_completion": "mandatory regardless of physical targets",
        },
        "qe_defaults": {
            "scf_nbnd": cfg.get(
                "scf_nbnd", "QE automatic (fixed)" if cfg["occupations"] == "fixed" else cfg["nbnd"]
            ),
            "total_charge": cfg.get("tot_charge", "QE neutral default"),
            "unexposed_controls": (
                "Other unexposed controls use QE 7.4 defaults; "
                "advanced-method controls are not qualified"
            ),
            "ion_cell_dynamics": "BFGS for full; not requested for SCF-only",
            "symmetry": "uniform mesh symmetry; path nosym/noinv; ibrav=0",
        },
        "execution_limits": {
            "launcher": cfg["launcher_limits"],
            "standalone": "per-command timeout only; host resource supervision is external",
        },
    }
    if backend == "standalone":
        body["inactive_parameters"].append("launcher_limits")
    body["plan_sha256"] = canonical_hash(body)
    return body


def read_plan(path):
    plan = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    body = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if plan.get("schema_version") != "qe-plan-1" or canonical_hash(body) != plan.get("plan_sha256"):
        raise ValueError("Invalid or modified research plan")
    return plan


def confirm_plan(plan_path, output, expected_hash, confirmed_by):
    from datetime import datetime

    plan = read_plan(plan_path)
    if expected_hash != plan["plan_sha256"] or not confirmed_by.strip():
        raise ValueError("Explicit displayed plan hash and user identity are required")
    if plan["driver_sha256"] != digest(__file__):
        raise ValueError("Driver changed; preview and confirm a new plan")
    receipt = {
        "schema_version": "qe-confirmation-1",
        "plan_sha256": expected_hash,
        "confirmed_by": confirmed_by.strip(),
        "confirmed_at_utc": datetime.now(UTC).isoformat(),
        "statement": "User confirmed the displayed effective plan and disclosed defaults",
    }
    write_new(output, receipt)
    return receipt


def require_confirmation(
    cfg,
    protocol_path,
    plan_path,
    confirmation_path,
    mode=None,
    convergence=None,
    *,
    execution_context,
):
    if not protocol_path or not plan_path or not confirmation_path:
        raise ValueError("Research plan and user confirmation are required before computation")
    plan = read_plan(plan_path)
    mode = mode if mode is not None else plan["mode"]
    convergence = convergence if convergence is not None else plan["convergence"]
    protocol = Path(protocol_path).read_bytes().decode("utf-8")
    expected = build_plan(cfg, protocol, mode, convergence, backend=execution_context)
    receipt = json.loads(Path(confirmation_path).read_text(encoding="utf-8-sig"))
    if (
        expected != plan
        or receipt.get("schema_version") != "qe-confirmation-1"
        or receipt.get("plan_sha256") != plan["plan_sha256"]
        or not receipt.get("confirmed_by", "").strip()
        or not receipt.get("confirmed_at_utc")
    ):
        raise ValueError(
            "Plan/parameters/protocol/source changed or not confirmed; preview and reconfirm"
        )
    return plan, receipt


def current_execution_context():
    mount = Path("/opt/acs-capabilities/quantum-espresso-7.4/bin")
    return (
        "simjecture" if os.environ.get("QE_BIN") == str(mount) and mount.is_dir() else "standalone"
    )


def evaluate_acceptance(summary, cfg):
    observed = {
        "path_gap_ev": summary.get("path_gap_ev"),
        "max_force_ry_bohr": summary.get("max_force_ry_bohr"),
        "total_energy_ev": summary.get("total_energy_ev"),
        "mean_total_magnetization_muB_per_atom": summary["magnetization"][
            "mean_total_muB_per_atom"
        ],
        "total_magnetization_muB_per_cell": summary["magnetization"]["total_muB_per_cell"],
    }

    def check(ranges, values, prefix):
        for name, limits in ranges.items():
            value = values.get(name)
            if value is None or not math.isfinite(value):
                raise ValueError(f"Requested acceptance observable unavailable: {name}")
            summary["checks"][prefix + name] = limits[0] <= value <= limits[1]

    check(cfg["acceptance"], observed, "acceptance_")
    summary["physical_acceptance"] = "passed" if cfg["acceptance"] else "not_requested"
    for index, ranges in cfg["convergence_acceptance"].items():
        row = summary["convergence"][int(index)]
        values = {"delta_mev_per_atom": row["delta_mev_per_atom"]}
        if cfg["nspin"] == 2:
            values["delta_abs_mean_total_moment_muB_per_atom"] = abs(
                row["magnetization"]["mean_total_muB_per_atom"]
            ) - abs(observed["mean_total_magnetization_muB_per_atom"])
        check(ranges, values, "control_" + index + "_")
    summary["numerical_accuracy"] = (
        "targets_checked" if cfg["convergence_acceptance"] else "not_assessed"
    )


def verify_pseudos(cfg, directory):
    for s in cfg["species"]:
        path = Path(directory) / s["pseudo"]
        if not path.is_file() or digest(path) != s["sha256"]:
            raise ValueError(f"Pseudopotential missing or hash mismatch: {path}")


def fetch(cfg, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for s in cfg["species"]:
        path = directory / s["pseudo"]
        if path.exists():
            if digest(path) != s["sha256"]:
                raise ValueError(f"Refusing to replace mismatched pseudopotential {path}")
            continue
        if not s["url"].startswith("https://"):
            raise ValueError("Use an HTTPS pseudopotential source")
        with urllib.request.urlopen(s["url"], timeout=60) as response:
            content = response.read(16 * 1024**2 + 1)
        if len(content) > 16 * 1024**2 or hashlib.sha256(content).hexdigest() != s["sha256"]:
            raise ValueError("Pseudopotential download size/hash mismatch")
        path.write_bytes(content)
    verify_pseudos(cfg, directory)


def pw_input(cfg, calculation, cell, atoms, kmesh=None):
    settings = electronic_settings(cfg)
    occupation = (
        settings["dos_occupations"]
        if calculation == "nscf"
        else (settings["band_occupations"] if calculation == "bands" else settings["occupations"])
    )
    control = [
        "&CONTROL",
        f" calculation='{calculation}',",
        " prefix='sample', outdir='./out',",
        " pseudo_dir='../pseudo',",
        " tstress=.true., tprnfor=.true.,",
        f" etot_conv_thr={cfg['etot_conv_thr_ry']:.12g},",
        f" forc_conv_thr={cfg['forc_conv_thr_ry_bohr']:.12g},",
        "/",
    ]
    system = [
        "&SYSTEM",
        f" ibrav=0, nat={len(atoms)}, ntyp={len(cfg['species'])},",
        f" ecutwfc={cfg['ecutwfc_ry']}, ecutrho={cfg['ecutrho_ry']},",
        f" input_dft='{cfg['functional']}', nspin={settings['nspin']},",
        f" occupations='{occupation}',",
    ]
    if occupation == "smearing":
        system += [f" smearing='{settings['smearing']}', degauss={settings['degauss_ry']},"]
    if "tot_charge" in cfg:
        system += [f" tot_charge={cfg['tot_charge']},"]
    if settings["nspin"] == 2:
        for i, species in enumerate(cfg["species"], 1):
            if species["label"] in settings["starting_magnetization"]:
                value = settings["starting_magnetization"][species["label"]]
                system += [f" starting_magnetization({i})={value},"]
    if calculation in ("nscf", "bands"):
        system += [f" nbnd={cfg['nbnd']},"]
    elif "scf_nbnd" in cfg or settings["occupations"] != "fixed":
        system += [f" nbnd={cfg.get('scf_nbnd', cfg['nbnd'])},"]
    if calculation == "bands":
        system += [" nosym=.true., noinv=.true.,"]
    system += [
        "/",
        "&ELECTRONS",
        f" conv_thr={cfg['conv_thr_ry']:.12g},",
        f" electron_maxstep={cfg.get('electron_maxstep', 150)}, "
        f"mixing_beta={cfg.get('mixing_beta', 0.5)},",
        "/",
    ]
    if calculation in ("relax", "vc-relax"):
        system += ["&IONS", " ion_dynamics='bfgs',", "/"]
    if calculation == "vc-relax":
        system += [
            "&CELL",
            f" cell_dynamics='bfgs', cell_dofree='{cfg['cell_dofree']}',",
            f" press_conv_thr={cfg['press_conv_thr_kbar']},",
            "/",
        ]
    lines = control + system + ["ATOMIC_SPECIES"]
    lines += [f"{s['label']} {s['mass']} {s['pseudo']}" for s in cfg["species"]]
    lines += ["CELL_PARAMETERS angstrom"]
    lines += [" ".join(f"{v:.12f}" for v in row) for row in cell]
    lines += ["ATOMIC_POSITIONS crystal"]
    lines += [a["species"] + " " + " ".join(f"{v:.12f}" for v in a["fractional"]) for a in atoms]
    if calculation == "bands":
        lines += ["K_POINTS crystal_b", str(len(cfg["path"]))]
        lines += [" ".join(str(v) for v in p["k"]) + f" {p['points']}" for p in cfg["path"]]
    else:
        lines += ["K_POINTS automatic", " ".join(str(v) for v in kmesh) + " 0 0 0"]
    return "\n".join(lines) + "\n"


def read_pw_xml(path, calculation=None):
    root = ET.parse(path).getroot()
    if root.findtext("exit_status", "missing").strip() != "0":
        raise ValueError("PW XML exit_status is missing or nonzero")
    recorded_calculation = root.findtext("input/control_variables/calculation")
    if calculation is not None and recorded_calculation != calculation:
        raise ValueError("PW XML calculation does not match the requested stage")
    calculation = recorded_calculation
    conv = root.find("output/convergence_info")
    if conv is None:
        raise ValueError("Missing PW convergence_info")
    if calculation not in {"scf", "relax", "vc-relax", "nscf", "bands"}:
        raise ValueError("Missing or unsupported PW calculation type")
    # NSCF/path diagonalization does not perform an SCF loop; its flag can be false.
    required = [] if calculation in {"nscf", "bands"} else ["scf_conv"]
    if calculation in {"relax", "vc-relax"}:
        required.append("opt_conv")
    for kind in required:
        if conv.findtext(f"{kind}/convergence_achieved", "missing").strip().lower() not in {
            "true",
            "t",
            ".true.",
        }:
            raise ValueError(f"PW {kind} convergence is missing or not achieved")
    output = root.find("output")
    if output is None:
        raise ValueError("Missing QE output XML")

    def finite_number(text, scale=1):
        value = float(text) * scale
        if not math.isfinite(value):
            raise ValueError("Nonfinite PW observable")
        return value

    structure = output.find("atomic_structure")
    if structure is None or structure.find("cell") is None:
        raise ValueError("Missing PW atomic structure")
    cell_bohr = np.array(
        [[float(v) for v in structure.find(f"cell/a{i}").text.split()] for i in (1, 2, 3)]
    )
    if (
        cell_bohr.shape != (3, 3)
        or not np.isfinite(cell_bohr).all()
        or not math.isfinite(float(np.linalg.det(cell_bohr)))
        or np.linalg.det(cell_bohr) <= 0
    ):
        raise ValueError("Invalid PW cell")
    atoms = []
    for atom in structure.findall("atomic_positions/atom"):
        cart = np.fromstring(atom.text, sep=" ")
        if cart.shape != (3,) or not np.isfinite(cart).all():
            raise ValueError("Invalid PW atom coordinates")
        atoms.append(
            {
                "species": atom.attrib["name"],
                "fractional": (cart @ np.linalg.inv(cell_bohr)).tolist(),
            }
        )
    if not atoms:
        raise ValueError("Missing PW atoms")
    bs = output.find("band_structure")
    if bs is None:
        raise ValueError("Missing PW band structure")

    def truth(name):
        return bs.findtext(name, "false").strip().lower() in {"true", "t", ".true."}

    if truth("noncolin") or truth("spinorbit"):
        raise ValueError("Noncollinear/SOC XML spinors are not implemented")
    nspin = 2 if truth("lsda") else 1
    electrons = finite_number(bs.findtext("nelec"))
    nodes = bs.findall("ks_energies")
    energies = (
        np.array([np.fromstring(x.findtext("eigenvalues"), sep=" ") for x in nodes]) * HARTREE_EV
    )
    k = np.array([np.fromstring(x.findtext("k_point"), sep=" ") for x in nodes])
    weights = np.array([float(x.find("k_point").attrib["weight"]) for x in nodes])
    if (
        energies.ndim != 2
        or not energies.size
        or not np.isfinite(energies).all()
        or k.shape != (len(energies), 3)
        or not np.isfinite(k).all()
        or not np.isfinite(weights).all()
    ):
        raise ValueError("Invalid PW eigenvalue dimensions")
    if nspin == 2:
        up = bs.findtext("nbnd_up")
        down = bs.findtext("nbnd_dw")
        up = (
            int(up)
            if up is not None
            else (energies.shape[1] - int(down) if down else energies.shape[1] // 2)
        )
        counts = [up, int(down) if down is not None else energies.shape[1] - up]
    else:
        counts = [energies.shape[1]]
    if min(counts) < 1 or sum(counts) != energies.shape[1]:
        raise ValueError("Invalid PW spin-band dimensions")
    occupations = None
    if all(x.find("occupations") is not None for x in nodes):
        occupations = np.array([np.fromstring(x.findtext("occupations"), sep=" ") for x in nodes])
        if occupations.shape != energies.shape or not np.isfinite(occupations).all():
            raise ValueError("Invalid PW occupation dimensions")
    channels = []
    offset = 0
    for label, count in zip(["scalar"] if nspin == 1 else ["up", "down"], counts, strict=True):
        occ = None if occupations is None else occupations[:, offset : offset + count]
        nocc = None
        if occ is not None and np.all(
            np.isclose(occ, 0, atol=1e-6) | np.isclose(occ, 1, atol=1e-6)
        ):
            occupied = np.sum(occ > 0.5, axis=1)
            if np.all(occupied == occupied[0]) and np.all(occ[:, : int(occupied[0])] > 0.5):
                nocc = int(occupied[0])
        channels.append(
            dict(
                label=label,
                band_slice=[offset, offset + count],
                energies_ev=energies[:, offset : offset + count],
                occupations=occ,
                nocc=nocc,
            )
        )
        offset += count
    fermi = bs.findtext("fermi_energy")
    fermi = None if fermi is None else finite_number(fermi, HARTREE_EV)
    two = bs.findtext("two_fermi_energies")
    two = None if two is None else [finite_number(value, HARTREE_EV) for value in two.split()]
    total = finite_number(output.findtext("total_energy/etot"), HARTREE_EV)
    forces_text, stress_text = output.findtext("forces"), output.findtext("stress")
    forces = np.fromstring(forces_text, sep=" ").reshape(-1, 3) if forces_text else None
    stress = np.fromstring(stress_text, sep=" ").reshape(3, 3) if stress_text else None
    if forces is not None and (
        forces.shape != (len(atoms), 3) or not np.isfinite(forces).all()
    ):
        raise ValueError("Invalid PW forces")
    if stress is not None and not np.isfinite(stress).all():
        raise ValueError("Nonfinite PW stress")

    def moment(name):
        text = output.findtext("magnetization/" + name)
        return None if text is None else finite_number(text)

    total_moment, absolute_moment = moment("total"), moment("absolute")
    magnetization = {
        "total_muB_per_cell": total_moment,
        "absolute_muB_per_cell": absolute_moment,
        "mean_total_muB_per_atom": None if total_moment is None else total_moment / len(atoms),
        "mean_absolute_muB_per_atom": None
        if absolute_moment is None
        else absolute_moment / len(atoms),
        "number_of_atoms": len(atoms),
        "scope": "Integrated spin density; the per-atom mean is not a site-resolved moment",
    }
    smearing_term = output.findtext("total_energy/demet")
    return dict(
        magnetization=magnetization,
        smearing_term_ev=None
        if smearing_term is None
        else finite_number(smearing_term, HARTREE_EV),
        pressure_kbar=None if stress is None else float(np.trace(stress) / 3 * HARTREE_BOHR3_KBAR),
        cell_angstrom=cell_bohr * BOHR_ANGSTROM,
        atoms=atoms,
        energies_ev=energies,
        occupations=occupations,
        k=k,
        weights=weights,
        nspin=nspin,
        channels=channels,
        nocc=channels[0]["nocc"] if nspin == 1 else None,
        nelec=electrons,
        fermi_energy_ev=fermi,
        fermi_energies_ev=two,
        occupations_kind=bs.findtext("occupations_kind"),
        total_energy_ev=total,
        max_force_ry_bohr=None
        if forces is None
        else float(np.max(np.linalg.norm(forces, axis=1))) * 2,
    )


def spin_channels(data):
    return data.get(
        "channels",
        [
            dict(
                label="scalar",
                band_slice=[0, data["energies_ev"].shape[1]],
                energies_ev=data["energies_ev"],
                nocc=data.get("nocc"),
            )
        ],
    )


def spectral_reference(bands, scf, cfg):
    """A gap is optional; fractional occupations never become a rounded band index."""
    channels = spin_channels(bands)
    edges = dict(path_gap_ev=None, path_vbm_ev=None, path_cbm_ev=None)
    if cfg["occupations"] == "fixed" and all(
        x["nocc"] is not None and 0 < x["nocc"] < x["energies_ev"].shape[1] for x in channels
    ):
        vbm = max(float(x["energies_ev"][:, x["nocc"] - 1].max()) for x in channels)
        cbm = min(float(x["energies_ev"][:, x["nocc"]].min()) for x in channels)
        edges.update(path_gap_ev=cbm - vbm, path_vbm_ev=vbm, path_cbm_ev=cbm)
    mode = cfg.get("energy_reference", "auto")
    if "energy_zero_ev" in cfg:
        zero, origin = cfg["energy_zero_ev"], "configured"
    else:
        if mode == "auto":
            mode = "vbm" if edges["path_vbm_ev"] is not None else "fermi"
        zero = {"vbm": edges["path_vbm_ev"], "fermi": scf.get("fermi_energy_ev"), "absolute": 0.0}[
            mode
        ]
        origin = "final_scf_fermi" if mode == "fermi" else mode
        if zero is None or not math.isfinite(zero):
            raise ValueError(
                f"Requested {mode} energy reference unavailable; supply energy_zero_ev explicitly"
            )
    return edges, dict(value_ev=float(zero), origin=origin)


def postprocess_options(cfg):
    settings = electronic_settings(cfg)
    options = f" bz_sum='{settings['dos_bz_sum']}', DeltaE={cfg['dos_delta_ev']},"
    projection = f" DeltaE={cfg['dos_delta_ev']},"
    if settings["dos_bz_sum"] == "smearing":
        code = SMEARING_CODES[settings["dos_smearing"]]
        broadening = f" degauss={settings['dos_degauss_ry']}, ngauss={code},"
        options += broadening
        projection += broadening
    return options, projection


def verify_band_files(directory, bands):
    largest = 0.0
    channels = spin_channels(bands)
    for channel in channels:
        name = "bands.dat" if len(channels) == 1 else f"bands_{channel['label']}.dat"
        k, energy = read_filband(Path(directory) / name)
        expected = channel["energies_ev"]
        if k.shape != bands["k"].shape or not np.allclose(k, bands["k"], atol=1e-6, rtol=0):
            raise ValueError("bands.x k-point indexing differs from PW XML")
        if energy.shape != expected.shape:
            raise ValueError("bands.x spin-band dimensions differ from PW XML")
        delta = float(np.max(np.abs(energy - expected)))
        if not math.isfinite(delta) or delta > 0.00051:
            raise ValueError("bands.x energy indexing differs from PW XML")
        largest = max(largest, delta)
    return largest


def read_filband(path):
    lines = Path(path).read_text().splitlines()
    header = re.search(r"nbnd=\s*(\d+),\s*nks=\s*(\d+)", lines[0])
    if not header:
        raise ValueError("Invalid bands.x header")
    nbnd, nk = map(int, header.groups())
    values = np.fromstring(" ".join(lines[1:]), sep=" ")
    if len(values) != nk * (nbnd + 3):
        raise ValueError("Truncated bands.x table")
    table = values.reshape(nk, nbnd + 3)
    if not np.isfinite(table).all():
        raise ValueError("Nonfinite bands.x k points or energies")
    return table[:, :3], table[:, 3:]


def read_projections(path, reference):
    root = ET.parse(path).getroot()
    header = root.find("HEADER").attrib
    nk, nb = int(header["NUMBER_OF_K-POINTS"]), int(header["NUMBER_OF_BANDS"])
    ns = int(header.get("NUMBER_OF_SPIN_COMPONENTS", "1"))
    nw = int(header["NUMBER_OF_ATOMIC_WFC"])
    channels = spin_channels(reference)
    if (
        ns != len(channels)
        or nk != len(reference["k"])
        or any(x["energies_ev"].shape != (nk, nb) for x in channels)
    ):
        raise ValueError("Projection spin-band dimensions do not match PW bands")
    kpoints = root.findall("EIGENSTATES/K-POINT")
    energy_nodes = root.findall("EIGENSTATES/E")
    proj_nodes = root.findall("EIGENSTATES/PROJS")
    if len(kpoints) != ns * nk or len(energy_nodes) != ns * nk or len(proj_nodes) != ns * nk:
        raise ValueError("Incomplete projection spin/k-point sequence")
    weights = np.empty((nk, nw, reference["energies_ev"].shape[1]))
    for spin, channel in enumerate(channels):
        start, stop = channel["band_slice"]
        for ik in range(nk):
            index = spin * nk + ik
            k = np.fromstring(kpoints[index].text, sep=" ")
            energy = np.fromstring(energy_nodes[index].text, sep=" ") * HARTREE_EV / 2
            if k.shape != (3,) or not np.allclose(k, reference["k"][ik], atol=1e-7, rtol=0):
                raise ValueError("Projection k-point ordering mismatch")
            if energy.shape != (nb,) or not np.allclose(
                energy, channel["energies_ev"][ik], atol=1e-6, rtol=0
            ):
                raise ValueError("Projection band energies/order/units mismatch")
            wfc = proj_nodes[index].findall("ATOMIC_WFC")
            if len(wfc) != nw:
                raise ValueError("Incomplete projection state table")
            for iw, orbital in enumerate(wfc):
                if (
                    int(orbital.attrib["index"]) != iw + 1
                    or int(orbital.attrib.get("spin", "1")) != spin + 1
                ):
                    raise ValueError("Projection state/spin index mismatch")
                values = np.fromstring(orbital.text, sep=" ")
                if values.size != nb * 2:
                    raise ValueError("Incomplete complex projection amplitudes")
                weights[ik, iw, start:stop] = np.sum(values.reshape(nb, 2) ** 2, axis=1)
    if not np.all(np.isfinite(weights)) or np.min(weights) < 0:
        raise ValueError("Invalid projection weights")
    return weights


def run_command(binary, text, directory, timeout, receipts, label=None):
    directory.mkdir(parents=True, exist_ok=True)
    print(f"QE stage {directory.name}: {binary}", flush=True)
    filename = label or binary.replace(".x", "")
    inp = directory / (filename + ".in")
    inp.write_text(text)
    bindir = Path(os.environ.get("QE_BIN", Path(sys.executable).parent))
    executable = bindir / binary
    start = time.time()
    receipt = {
        "command": [str(executable), "-in", inp.name],
        "cwd": str(directory),
        "input_sha256": digest(inp),
        "start_unix": start,
    }
    receipts.append(receipt)
    try:
        with (directory / (filename + ".out")).open("w") as output:
            result = subprocess.run(
                receipt["command"],
                cwd=directory,
                stdout=output,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
        receipt.update(
            returncode=result.returncode,
            wall_seconds=time.time() - start,
            output_sha256=digest(directory / (filename + ".out")),
        )
        out = (directory / (filename + ".out")).read_text()
        if (
            result.returncode
            or "JOB DONE." not in out
            or re.search(r"convergence\s+not\s+achieved", out, re.I)
        ):
            raise RuntimeError(f"{binary} failed; inspect {directory / (filename + '.out')}")
        if binary == "pw.x":
            calculation = re.search(r"calculation\s*=\s*['\"]([^'\"]+)", text)
            if calculation is None:
                raise ValueError("Missing PW calculation")
            read_pw_xml(xml_at(directory), calculation.group(1))
            if re.search(
                r"maximum number of steps|bfgs.*failed|stopped on user request",
                out,
                re.I,
            ):
                raise ValueError("PW reports an incomplete or failed calculation")
    except subprocess.TimeoutExpired:
        receipt.update(timed_out=True, wall_seconds=time.time() - start)
        raise


def xml_at(directory):
    return directory / "out/sample.save/data-file-schema.xml"


def reference_qualification(root, relax_xml=None):
    """Reassess completion from evidence, never promote a cached summary alone."""
    root = Path(root)
    summary = json.loads((root / "summary.json").read_text())
    evidence = {}
    checks = summary.get("checks", {})
    if (
        summary.get("status") != "passed"
        or not checks
        or not all(value is True for value in checks.values())
    ):
        return {
            "status": "failed",
            "reason": "Recorded workflow checks did not pass",
            "evidence": evidence,
        }
    geometry = json.loads((root / "final_structure.json").read_text())
    for stage, path in (
        ("vc-relax", Path(relax_xml) if relax_xml else xml_at(root / "relax")),
        ("scf", xml_at(root / "scf")),
    ):
        if not path.is_file():
            return {
                "status": "unqualified",
                "reason": f"Missing {stage} XML evidence",
                "evidence": evidence,
            }
        evidence[stage] = {"path": str(path), "sha256": digest(path)}
        try:
            data = read_pw_xml(path, stage)
            if not np.allclose(data["cell_angstrom"], geometry["cell_angstrom"], atol=1e-7, rtol=0):
                raise ValueError("Evidence cell does not match analyzed final structure")
            if [a["species"] for a in data["atoms"]] != [
                a["species"] for a in geometry["atoms"]
            ] or not np.allclose(
                [a["fractional"] for a in data["atoms"]],
                [a["fractional"] for a in geometry["atoms"]],
                atol=1e-7,
                rtol=0,
            ):
                raise ValueError("Evidence atoms do not match analyzed final structure")
        except (ValueError, KeyError, ET.ParseError) as error:
            return {"status": "failed", "reason": f"{stage}: {error}", "evidence": evidence}
    return {
        "status": "qualified",
        "reason": "Completion and geometry evidence verified",
        "evidence": evidence,
    }


def atomic_pdos_files(root):
    """Resolve the complete atom/radial-wavefunction inventory from projwfc states."""
    log = (root / "dos/projwfc.out").read_text()
    rows = re.findall(
        r"state #\s*(\d+):\s*atom\s+(\d+)\s*\(\s*([^\s)]+)\s*\),?\s*wfc\s+(\d+)\s*\(l=\s*(\d+)",
        log,
    )
    if not rows or len({x[0] for x in rows}) != len(rows):
        raise ValueError("Missing or duplicate projwfc atomic-state inventory")
    expected = set()
    for _, atom, species, wfc, angular in rows:
        angular_index = int(angular)
        if angular_index >= len("spdfghi"):
            raise ValueError("Unsupported PDOS angular channel")
        expected.add(
            f"pdos.pdos_atm#{int(atom)}({species})_wfc#{int(wfc)}({'spdfghi'[angular_index]})"
        )
    actual = {p.name for p in (root / "dos").glob("pdos.pdos_atm*")}
    if actual != expected:
        raise ValueError(
            f"Atomic PDOS inventory mismatch: missing={expected - actual}, "
            f"unknown={actual - expected}"
        )
    return [root / "dos" / name for name in sorted(expected)]


def validate_tables(root, nspin=None, *, pdos_requested=True):
    dos = np.loadtxt(root / "dos/dos.dat")
    pdos = np.loadtxt(root / "dos/pdos.pdos_tot") if pdos_requested else None
    if nspin is None:
        nspin = 2 if dos.ndim == 2 and dos.shape[1] == 4 else 1
    if (
        dos.ndim != 2
        or dos.shape[1] != nspin + 2
        or (pdos_requested and (pdos.ndim != 2 or pdos.shape[1] != 1 + 2 * nspin))
    ):
        raise ValueError("DOS/PDOS columns do not match scalar/collinear spin layout")
    tables = [dos] + ([pdos] if pdos_requested else [])
    for file in atomic_pdos_files(root) if pdos_requested else []:
        table = np.loadtxt(file)
        # QE columns: E, LDOS per spin, then every m component per spin.
        angular = re.search(r"\(([spdfghi])\)$", file.name).group(1)
        expected_columns = 1 + nspin * (1 + 2 * "spdfghi".index(angular) + 1)
        if table.ndim != 2 or table.shape[1] != expected_columns:
            raise ValueError("Invalid atomic PDOS spin columns")
        if table.shape[0] != pdos.shape[0] or not np.allclose(
            table[:, 0], pdos[:, 0], rtol=0, atol=1e-8
        ):
            raise ValueError("Atomic PDOS energy grid differs from total PDOS")
        tables.append(table)
    if any(not np.isfinite(x).all() for x in tables):
        raise ValueError("Nonfinite DOS/PDOS")
    if any(not np.all(np.diff(x[:, 0]) > 0) for x in tables):
        raise ValueError("Unordered DOS energies")
    # Higher-order smearing kernels can have negative lobes; positivity is not universal.
    return dos, pdos


def plot_results(root, bands, proj, dos, pdos, cfg, energy_reference):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    k = bands["k"]
    distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(k, axis=0), axis=1))]
    zero = energy_reference["value_ev"]
    eigen = bands["energies_ev"] - zero
    channels = spin_channels(bands)
    states = cfg.get("projection_states", [1])
    if not states or any(not isinstance(x, int) or x < 1 or x > proj.shape[1] for x in states):
        raise ValueError("projection_states must be valid one-based atomic projector indices")
    fig, axes = plt.subplots(1, 3, figsize=(13, 5), gridspec_kw={"width_ratios": [1.4, 1, 1]})
    labels = []
    for spin, channel in enumerate(channels):
        start, stop = channel["band_slice"]
        color = ["#127c92", "#b54538"][spin]
        style = "-" if spin == 0 else "--"
        axes[0].plot([], [], color=color, linestyle=style, label=channel["label"])
        for ib in range(start, stop):
            axes[0].plot(distance, eigen[:, ib], color=color, linestyle=style, linewidth=0.7)
            size = 10 * proj[:, np.array(states) - 1, ib].sum(axis=1)
            axes[0].scatter(distance, eigen[:, ib], s=size, color=color, alpha=0.7)
            labels.append(f"{channel['label']}_band_{ib - start + 1}_ev_minus_reference")
        axes[1].plot(
            dos[:, 1 + spin],
            dos[:, 0] - zero,
            color=color,
            linestyle=style,
            label=f"DOS {channel['label']}",
        )
        if pdos is not None:
            axes[1].plot(
                pdos[:, 1 + len(channels) + spin],
                pdos[:, 0] - zero,
                linestyle=style,
                label=f"atomic PDOS {channel['label']}",
            )
    indices = [0]
    for vertex in cfg["path"][:-1]:
        indices.append(indices[-1] + vertex["points"])
    if indices[-1] != len(k) - 1:
        raise ValueError("Path point count does not match configured vertices")
    axes[0].set_xticks(distance[indices], [p["label"] for p in cfg["path"]])
    for x in distance[indices]:
        axes[0].axvline(x, color="0.8", linewidth=0.4)
    reference_label = energy_reference["origin"]
    axes[0].set_ylabel(f"Energy relative to {reference_label} (eV)")
    axes[0].set_title("Bands + atomic states " + ",".join(map(str, states)))
    axes[0].legend()
    axes[1].legend(fontsize=6)
    axes[1].set_xlabel("states/eV/cell")
    axes[1].set_title("Uniform k branch")
    if pdos is None:
        axes[2].text(0.5, 0.5, "PDOS not requested", ha="center")
    for file in atomic_pdos_files(root) if pdos is not None else []:
        table = np.loadtxt(file)
        for spin, channel in enumerate(channels):
            axes[2].plot(
                table[:, 1 + spin],
                table[:, 0] - zero,
                linewidth=0.7,
                linestyle="-" if spin == 0 else "--",
                label=file.name.replace("pdos.pdos_", "") + " " + channel["label"],
            )
    axes[2].set_title("Atomic-orbital LDOS")
    axes[2].set_xlabel("states/eV/cell")
    if pdos is not None:
        axes[2].legend(fontsize=5)
    for ax in axes:
        ax.axhline(0, color="0.6", linewidth=0.5)
        ax.set_ylim(cfg["plot_energy_ev"])
    fig.tight_layout()
    fig.savefig(root / "bands_dos_pdos.png", dpi=180)
    plt.close(fig)
    np.savetxt(
        root / "bands.csv",
        np.column_stack((distance, eigen)),
        delimiter=",",
        header="distance_2pi_alat," + ",".join(labels),
    )
    np.savez_compressed(
        root / "verified_projections.npz",
        k=k,
        energies_ev=bands["energies_ev"],
        weights=proj,
        spin_labels=np.array([x["label"] for x in channels]),
        band_slices=np.array([x["band_slice"] for x in channels]),
        energy_reference_ev=zero,
    )


def run(
    cfg,
    pseudo_dir,
    output,
    smoke=None,
    convergence=None,
    *,
    protocol=None,
    plan=None,
    confirmation=None,
):
    approved, receipt = require_confirmation(
        cfg,
        protocol,
        plan,
        confirmation,
        None if smoke is None else ("scf-only" if smoke else "full"),
        convergence,
        execution_context=current_execution_context(),
    )
    cfg = approved["effective_case"]
    smoke, convergence = approved["mode"] == "scf-only", approved["convergence"]
    root = Path(output).resolve()
    if root.exists():
        raise ValueError(f"Refusing to overwrite existing output {root}")
    verify_pseudos(cfg, pseudo_dir)
    root.mkdir(parents=True)
    receipts = []
    summary = {
        "schema_version": "1",
        "status": "running",
        "scope": "exploratory commissioning",
        "configuration": cfg,
        "source_sha256": digest(__file__),
        "commands": receipts,
        "pdos_status": "not_requested" if smoke or not cfg["pdos"] else "requested",
        "approved_plan_sha256": approved["plan_sha256"],
        "confirmation": receipt,
    }
    dump(root / "effective_case.json", cfg)
    dump(root / "approved_plan.json", approved)
    (root / "pseudo").mkdir()
    for s in cfg["species"]:
        shutil.copy2(Path(pseudo_dir) / s["pseudo"], root / "pseudo" / s["pseudo"])
    started = time.time()
    try:
        cell, atoms = cfg["cell_angstrom"], cfg["atoms"]
        timeout = cfg["command_timeout_seconds"]
        if smoke:
            run_command(
                "pw.x",
                pw_input(cfg, "scf", cell, atoms, cfg["scf_k"]),
                root / "scf",
                timeout,
                receipts,
            )
            scf = read_pw_xml(xml_at(root / "scf"))
            summary.update(
                max_force_ry_bohr=scf["max_force_ry_bohr"],
                pressure_kbar=scf["pressure_kbar"],
                total_energy_ev=scf["total_energy_ev"],
                nelec=scf["nelec"],
                spin_components=scf["nspin"],
                magnetization=scf["magnetization"],
                fermi_energy_ev=scf["fermi_energy_ev"],
                checks={
                    "completed": True,
                    "finite_energy": math.isfinite(scf["total_energy_ev"]),
                    "spin_layout_matches_configuration": scf["nspin"]
                    == electronic_settings(cfg)["nspin"],
                },
            )
        else:
            relax = root / "relax"
            run_command(
                "pw.x",
                pw_input(cfg, "vc-relax", cell, atoms, cfg["relax_k"]),
                relax,
                timeout,
                receipts,
            )
            if "End of BFGS Geometry Optimization" not in (relax / "pw.out").read_text():
                raise ValueError("Relaxation did not reach BFGS completion")
            geometry = read_pw_xml(xml_at(relax), "vc-relax")
            cell, atoms = geometry["cell_angstrom"], geometry["atoms"]
            dump(root / "final_structure.json", {"cell_angstrom": cell.tolist(), "atoms": atoms})
            run_command(
                "pw.x",
                pw_input(cfg, "scf", cell, atoms, cfg["scf_k"]),
                root / "scf",
                timeout,
                receipts,
            )
            scf = read_pw_xml(xml_at(root / "scf"))
            checkpoint_hash = digest(xml_at(root / "scf"))
            for name in ("dos", "bands"):
                branch = root / name
                branch.mkdir()
                shutil.copytree(root / "scf/out", branch / "out")
                run_command(
                    "pw.x",
                    pw_input(cfg, "nscf" if name == "dos" else "bands", cell, atoms, cfg["dos_k"]),
                    branch,
                    timeout,
                    receipts,
                )
            pp = "&{namelist}\n prefix='sample', outdir='./out',\n{options}\n/\n"
            run_command(
                "dos.x",
                pp.format(
                    namelist="DOS",
                    options=" fildos='dos.dat'," + postprocess_options(cfg)[0],
                ),
                root / "dos",
                timeout,
                receipts,
            )
            if cfg.get("pdos", True):
                run_command(
                    "projwfc.x",
                    pp.format(
                        namelist="PROJWFC",
                        options=" filpdos='pdos'," + postprocess_options(cfg)[1] + " lsym=.true.,",
                    ),
                    root / "dos",
                    timeout,
                    receipts,
                )
            channels = spin_channels(read_pw_xml(xml_at(root / "bands")))
            for spin, channel in enumerate(channels, 1):
                filename = "bands.dat" if len(channels) == 1 else f"bands_{channel['label']}.dat"
                options = f" filband='{filename}', lsym=.false., no_overlap=.true.,"
                if len(channels) > 1:
                    options += f" spin_component={spin},"
                run_command(
                    "bands.x",
                    pp.format(namelist="BANDS", options=options),
                    root / "bands",
                    timeout,
                    receipts,
                    label=None if len(channels) == 1 else f"bands_{channel['label']}",
                )
            run_command(
                "projwfc.x",
                pp.format(
                    namelist="PROJWFC",
                    options=" filproj='projections', lsym=.false., kresolveddos=.true.,",
                ),
                root / "bands",
                timeout,
                receipts,
            )
            bands = read_pw_xml(xml_at(root / "bands"))
            max_delta = verify_band_files(root / "bands", bands)
            proj = read_projections(root / "bands/out/sample.save/atomic_proj.xml", bands)
            dos, pdos = validate_tables(root, bands["nspin"], pdos_requested=cfg.get("pdos", True))
            edges, alignment = spectral_reference(bands, scf, cfg)
            plot_results(root, bands, proj, dos, pdos, cfg, alignment)
            volume = float(np.linalg.det(cell))
            summary.update(
                total_energy_ev=scf["total_energy_ev"],
                nelec=scf["nelec"],
                occupied_bands=scf["nocc"],
                magnetization=scf["magnetization"],
                smearing_term_ev=scf["smearing_term_ev"],
                scf_fermi_energy_ev=scf["fermi_energy_ev"],
                dos_fermi_energy_ev=read_pw_xml(xml_at(root / "dos"))["fermi_energy_ev"],
                lattice_volume_angstrom3=volume,
                **edges,
                spin_components=bands["nspin"],
                occupied_bands_by_spin={x["label"]: x["nocc"] for x in spin_channels(bands)},
                energy_reference=alignment,
                max_bands_xml_difference_ev=max_delta,
                projection_sum_range=[float(proj.sum(axis=1).min()), float(proj.sum(axis=1).max())],
                max_force_ry_bohr=scf["max_force_ry_bohr"],
                pressure_kbar=scf["pressure_kbar"],
                pdos_status="validated" if cfg.get("pdos", True) else "not_requested",
                checks={
                    "completed": True,
                    "spin_layout_matches_configuration": bands["nspin"]
                    == scf["nspin"]
                    == electronic_settings(cfg)["nspin"],
                    "relaxation_completed": True,
                    "checkpoint_preserved": digest(xml_at(root / "scf")) == checkpoint_hash,
                    "branches_independent": not any(
                        (root / left / "out/sample.save/data-file-schema.xml").samefile(
                            root / right / "out/sample.save/data-file-schema.xml"
                        )
                        for left, right in (("scf", "dos"), ("scf", "bands"), ("dos", "bands"))
                    ),
                    "bands_indices_verified": True,
                    "projection_indices_verified": True,
                    ("dos_pdos_finite" if cfg.get("pdos", True) else "dos_finite"): True,
                },
            )
            if convergence:
                rows = []
                for i, control in enumerate(cfg["convergence"]):
                    alternative = dict(cfg, **control)
                    directory = root / f"control_{i:02d}"
                    run_command(
                        "pw.x",
                        pw_input(alternative, "scf", cell, atoms, alternative["scf_k"]),
                        directory,
                        timeout,
                        receipts,
                    )
                    data = read_pw_xml(xml_at(directory))
                    rows.append(
                        {
                            "settings": control,
                            "energy_ev": data["total_energy_ev"],
                            "magnetization": data["magnetization"],
                            "smearing_term_ev": data["smearing_term_ev"],
                            "fermi_energy_ev": data["fermi_energy_ev"],
                            "delta_mev_per_atom": (data["total_energy_ev"] - scf["total_energy_ev"])
                            * 1000
                            / len(atoms),
                            "max_force_ry_bohr": data["max_force_ry_bohr"],
                            "pressure_kbar": data["pressure_kbar"],
                        }
                    )
                summary["convergence"] = rows
                dump(root / "convergence.json", rows)
        evaluate_acceptance(summary, cfg)
        summary["checks"]["requested_products_present"] = all(
            (root / name).is_file()
            for name in approved["expected_products"]
            if name != "summary.json"
        )
        if not all(summary["checks"].values()):
            raise ValueError("One or more declared checks failed")
        summary["status"] = "passed"
    except Exception as error:
        summary["physical_acceptance"] = "failed_or_unassessed"
        summary["numerical_accuracy"] = "failed_or_unassessed"
        summary.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        summary["wall_seconds"] = time.time() - started
        summary["output_bytes"] = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        dump(root / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("fetch", "plan", "confirm", "run"))
    parser.add_argument("--case")
    parser.add_argument("--protocol")
    parser.add_argument("--plan")
    parser.add_argument("--confirmation")
    parser.add_argument("--expect-sha256")
    parser.add_argument("--confirmed-by")
    parser.add_argument("--pseudo-dir")
    parser.add_argument("--output")
    parser.add_argument("--profile")
    parser.add_argument("--mode", choices=("full", "scf-only"))
    parser.add_argument("--backend", choices=("simjecture", "standalone"))
    parser.add_argument("--smoke", action="store_true", default=None)
    parser.add_argument("--convergence", action=argparse.BooleanOptionalAction, default=None)
    args = parser.parse_args()
    if args.backend is not None and args.action != "plan":
        parser.error("Execution backend is chosen during plan preview, never overridden at run")
    if args.action == "confirm":
        if not all((args.plan, args.confirmation, args.expect_sha256, args.confirmed_by)):
            parser.error("confirm requires plan, confirmation, displayed hash and user identity")
        confirm_plan(args.plan, args.confirmation, args.expect_sha256, args.confirmed_by)
        return
    if not args.case:
        parser.error("case is required")
    if args.smoke and args.mode not in (None, "scf-only"):
        parser.error("Conflicting workflow modes")
    mode = "scf-only" if args.smoke else args.mode
    if args.action == "run" and args.plan and mode is None:
        mode = read_plan(args.plan)["mode"]
    cfg = load_case(args.case, args.profile, mode)
    if args.action == "fetch":
        if not args.pseudo_dir:
            parser.error("fetch requires pseudo-dir")
        fetch(cfg, args.pseudo_dir)
    elif args.action == "plan":
        if not args.plan or not args.protocol:
            parser.error("plan requires plan output and research protocol")
        proposed = build_plan(
            cfg,
            Path(args.protocol).read_bytes().decode("utf-8"),
            mode or "full",
            bool(args.convergence),
            backend=args.backend or "simjecture",
        )
        write_new(args.plan, proposed)
        print(json.dumps(proposed, indent=2, allow_nan=False))
    elif not args.output or not args.pseudo_dir:
        parser.error("run requires output and pseudo-dir")
    else:
        run(
            cfg,
            args.pseudo_dir,
            args.output,
            None if mode is None else mode == "scf-only",
            args.convergence,
            protocol=args.protocol,
            plan=args.plan,
            confirmation=args.confirmation,
        )


if __name__ == "__main__":
    main()
