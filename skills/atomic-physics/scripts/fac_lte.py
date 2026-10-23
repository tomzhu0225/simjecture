"""Inspect verbose FAC EN/TR tables and synthesize restricted LTE line opacity.

This is an isolated-ion Saha–Boltzmann diagnostic, not a complete material
EOS or opacity generator. Gaussian bin integrals preserve narrow-line area.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from scipy.constants import c, e, h, m_e, physical_constants
from scipy.special import logsumexp, ndtr

AMU_KG = physical_constants["atomic mass constant"][0]
R_E_M = physical_constants["classical electron radius"][0]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fac_blocks(path, kind):
    """Yield single-ion verbose FAC blocks; reject missing/truncated records."""
    with Path(path).open() as stream:
        first = stream.readline().strip()
        if not first.startswith("FAC "):
            raise ValueError(f"Not a FAC table: {path}")
        header, block, records = {"version": first}, {}, []
        for line in stream:
            line = line.strip()
            if not line:
                continue
            if "=" in line:
                key, value = (x.strip() for x in line.split("=", 1))
                if key == "NELE":
                    if block:
                        yield _checked_block(header, block, records, kind, path)
                    block, records = {key: value}, []
                elif block:
                    block[key] = value
                else:
                    header[key] = value
            elif line.split()[0].lstrip("-").isdigit():
                if not block:
                    raise ValueError(f"Data before a block in {path}")
                records.append(line)
        if not block:
            raise ValueError(f"No records in {path}")
        yield _checked_block(header, block, records, kind, path)


def _checked_block(header, block, records, kind, path):
    if int(header.get("Verbose", 0)) != 1 or int(header.get("Type", -1)) != kind:
        raise ValueError(f"Expected verbose FAC type {kind}: {path}")
    count_key = "NLEV" if kind == 1 else "NTRANS"
    if len(records) != int(block[count_key]):
        raise ValueError(f"Truncated {count_key} in {path}")
    return header.copy(), block, records


def read_levels(path):
    blocks = list(_fac_blocks(path, 1))
    header = blocks[0][0]
    if len(blocks) != int(header["NBlocks"]):
        raise ValueError(f"Block count mismatch: {path}")
    zkeys = [key for key in header if re.fullmatch(r"[A-Za-z]+ Z", key)]
    if len(zkeys) != 1:
        raise ValueError(f"Missing element in {path}")
    zfloat = float(header[zkeys[0]])
    z = int(zfloat)
    electrons = {int(block[1]["NELE"]) for block in blocks}
    if z != zfloat or len(electrons) != 1:
        raise ValueError("Each EN file must contain exactly one ion of an integer-Z element")
    nele = electrons.pop()
    if not 0 <= nele <= z:
        raise ValueError("Invalid electron count")
    rows = [row.split() for _, _, lines in blocks for row in lines]
    if any(len(row) < 6 for row in rows):
        raise ValueError(f"Incomplete energy record: {path}")
    index = np.array([int(row[0]) for row in rows])
    energy = np.array([float(row[2]) for row in rows])
    weight = np.array([int(row[5]) + 1 for row in rows])
    if (
        len(set(index)) != len(index)
        or not len(index)
        or np.any(index < 0)
        or not np.all(np.isfinite(energy))
        or np.any(energy < 0)
        or np.any(weight < 1)
    ):
        raise ValueError(f"Invalid or duplicate energy levels: {path}")
    ref_index, ground = header["E0"].split(",")
    ground = float(ground)
    if not np.isfinite(ground) or int(ref_index) not in index:
        raise ValueError("Invalid energy reference")
    return {
        "element": zkeys[0].split()[0],
        "nuclear_charge": z,
        "charge": z - nele,
        "electrons": nele,
        "index": index,
        "energy_eV": energy,
        "weight": weight,
        "ground_eV": ground,
        "version": header["version"],
    }


def transition_blocks(path):
    seen = 0
    for header, block, records in _fac_blocks(path, 2):
        seen += 1
        if not records:
            continue
        counts = {len(row.split()) for row in records}
        if len(counts) != 1 or next(iter(counts)) not in (8, 10):
            raise ValueError(f"Unsupported detailed/UTA columns: {path}")
        array = np.loadtxt(records, ndmin=2)
        if not np.all(np.isfinite(array)):
            raise ValueError(f"Nonfinite transition record: {path}")
        if np.any(array[:, :4] != np.floor(array[:, :4])):
            raise ValueError("Level indices and weights must be integers")
        uta = array.shape[1] == 10
        zkeys = [key for key in header if re.fullmatch(r"[A-Za-z]+ Z", key)]
        if len(zkeys) != 1:
            raise ValueError(f"Missing element in {path}")
        gf_column = 6 if uta else 5
        multipole = int(block["MULTIP"])
        if (
            np.any(array[:, 4] <= 0)
            or np.any(array[:, gf_column : gf_column + 2] < 0)
            or (uta and (np.any(array[:, 5] < 0) or np.any(array[:, 9] < 0)))
        ):
            raise ValueError("Invalid transition energies, widths, or strengths")
        yield {
            "electrons": int(block["NELE"]),
            "multipole": multipole,
            "uta": uta,
            "element": zkeys[0].split()[0],
            "nuclear_charge": float(header[zkeys[0]]),
            "upper": array[:, 0].astype(int),
            "upper_weight": array[:, 1] + 1,
            "lower": array[:, 2].astype(int),
            "lower_weight": array[:, 3] + 1,
            "energy_eV": array[:, 4],
            "gf": array[:, gf_column],
            "rate_s": array[:, gf_column + 1],
            "sigma_uta_eV": array[:, 5] if uta else np.zeros(len(array)),
            "ci_factor": array[:, 9] if uta else np.ones(len(array)),
        }
    if seen != int(header["NBlocks"]):
        raise ValueError(f"Block count mismatch: {path}")


def populations(ions, temperature_eV, electron_density_cm3):
    if not np.isfinite(temperature_eV) or temperature_eV <= 0:
        raise ValueError("Electron temperature must be finite and positive")
    if not np.isfinite(electron_density_cm3) or electron_density_cm3 <= 0:
        raise ValueError("Electron density must be finite and positive")
    charges = np.array([ion["charge"] for ion in ions])
    if not len(ions) or np.any(np.diff(charges) != 1):
        raise ValueError("Supply unique adjacent charge states in increasing order")
    if len({(ion["element"], ion["nuclear_charge"]) for ion in ions}) != 1:
        raise ValueError("A single-element model is required")
    log_partition = np.array(
        [logsumexp(np.log(ion["weight"]) - ion["energy_eV"] / temperature_eV) for ion in ions]
    )
    ground = np.array([ion["ground_eV"] for ion in ions])
    if np.any(np.diff(ground) <= 0):
        raise ValueError("Adjacent ions must have positive ionization thresholds")
    log_prefactor = (
        np.log(2)
        + 1.5 * np.log(2 * np.pi * m_e * temperature_eV * e / h**2)
        - np.log(electron_density_cm3)
        - np.log(1e6)
    )
    log_fraction = (
        log_partition
        - (ground - ground[0]) / temperature_eV
        + (charges - charges[0]) * log_prefactor
    )
    fraction = np.exp(log_fraction - logsumexp(log_fraction))
    return fraction, log_partition


def gaussian_bins(edges, centers, sigma, areas):
    """Return integrated area per bin, resolving lines narrower than a bin."""
    edges = np.asarray(edges, dtype=float)
    if (
        edges.ndim != 1
        or len(edges) < 2
        or not np.all(np.isfinite(edges))
        or edges[0] < 0
        or np.any(np.diff(edges) <= 0)
    ):
        raise ValueError("Photon bin edges must be finite, nonnegative, and increasing")
    centers, sigma, areas = [np.asarray(x, dtype=float) for x in (centers, sigma, areas)]
    if (
        edges.ndim != 1
        or len(edges) < 2
        or not np.all(np.isfinite(edges))
        or np.any(np.diff(edges) <= 0)
        or centers.ndim != 1
        or centers.shape != sigma.shape
        or centers.shape != areas.shape
        or not all(np.all(np.isfinite(x)) for x in (centers, sigma, areas))
        or np.any(sigma <= 0)
        or np.any(areas < 0)
    ):
        raise ValueError("Invalid Gaussian spectrum grid or line parameters")
    result = np.zeros(len(edges) - 1)
    for center, width, area in zip(centers, sigma, areas, strict=True):
        if area == 0:
            continue
        lo = max(0, np.searchsorted(edges, center - 9 * width, side="right") - 1)
        hi = min(len(result), np.searchsorted(edges, center + 9 * width, side="left"))
        if hi > lo:
            x = (edges[lo : hi + 1] - center) / width
            # Survival-function subtraction avoids loss of precision on the right wing.
            cumulative = np.diff(ndtr(x))
            positive = x[:-1] >= 0
            cumulative[positive] = -np.diff(ndtr(-x))[positive]
            result[lo:hi] += area * cumulative
    return result


def synthesize(
    model_path,
    temperature_eV,
    electron_density_cm3,
    ion_temperature_eV,
    edges,
    instrument_sigma_eV=0.0,
    apply_uta_ci=True,
):
    edges = np.asarray(edges, dtype=float)
    if (
        edges.ndim != 1
        or len(edges) < 2
        or not np.all(np.isfinite(edges))
        or edges[0] < 0
        or np.any(np.diff(edges) <= 0)
    ):
        raise ValueError("Photon bin edges must be finite, nonnegative, and increasing")
    model_path = Path(model_path).resolve()
    model = json.loads(model_path.read_text())
    mass = float(model["atomic_mass_u"])
    if not np.isfinite(mass) or mass <= 0:
        raise ValueError("Atomic mass must be finite and positive")
    if (
        not np.isfinite(ion_temperature_eV)
        or ion_temperature_eV <= 0
        or not np.isfinite(instrument_sigma_eV)
        or instrument_sigma_eV < 0
    ):
        raise ValueError("Ion temperature must be positive; instrument sigma nonnegative")
    entries = model["ions"]
    ions = [read_levels(model_path.parent / item["levels"]) for item in entries]
    order = np.argsort([ion["charge"] for ion in ions])
    ions = [ions[i] for i in order]
    entries = [entries[i] for i in order]
    fractions, logz = populations(ions, temperature_eV, electron_density_cm3)
    zbar = float(fractions @ [ion["charge"] for ion in ions])
    if zbar <= 0:
        raise ValueError("A positive mean charge is required to infer density from ne")
    # pi*r_e*c is integrated absorption cross-section in m^2/s.
    # Multiplying h in eV*s and dividing mass gives m^2*eV/kg; x10 gives cm^2*eV/g.
    area_scale = np.pi * R_E_M * c * (h / e) / (mass * AMU_KG) * 10
    channels = {-1: np.zeros(len(edges) - 1), 1: np.zeros(len(edges) - 1)}
    expected_areas = {-1: 0.0, 1: 0.0}
    counts, identities = {}, {str(model_path): sha256(model_path)}
    for ion, entry, fraction, partition in zip(ions, entries, fractions, logz, strict=True):
        index = {int(k): i for i, k in enumerate(ion["index"])}
        counts[str(ion["charge"])] = {"levels": len(index), "e1": 0, "m1": 0}
        for key in ("levels", "transitions"):
            path = (model_path.parent / entry[key]).resolve()
            identities[str(path)] = sha256(path)
        transition_path = model_path.parent / entry["transitions"]
        for block in transition_blocks(transition_path):
            multipole = block["multipole"]
            if multipole not in channels:
                raise ValueError("Only explicit E1 (-1) and M1 (+1) blocks are supported")
            if any(block[key] != ion[key] for key in ("electrons", "element", "nuclear_charge")):
                raise ValueError("EN/TR element or electron counts differ")
            try:
                lower = np.array([index[int(k)] for k in block["lower"]])
                upper = np.array([index[int(k)] for k in block["upper"]])
            except KeyError as exc:
                raise ValueError("Transition references a missing level") from exc
            if not np.array_equal(
                ion["weight"][lower], block["lower_weight"]
            ) or not np.array_equal(ion["weight"][upper], block["upper_weight"]):
                raise ValueError("EN/TR statistical weights differ")
            energy = block["energy_eV"]
            strength = block["gf"] * (block["ci_factor"] if apply_uta_ci else 1.0)
            # Lower-level statistical weight cancels the g in the FAC gf value.
            area = (
                area_scale
                * fraction
                * np.exp(-ion["energy_eV"][lower] / temperature_eV - partition)
                * strength
                * -np.expm1(-energy / temperature_eV)
            )
            sigma = np.sqrt(
                block["sigma_uta_eV"] ** 2
                + instrument_sigma_eV**2
                + energy**2 * ion_temperature_eV * e / (mass * AMU_KG * c**2)
            )
            channels[multipole] += gaussian_bins(edges, energy, sigma, area)
            expected_areas[multipole] += float(np.sum(area))
            counts[str(ion["charge"])]["e1" if multipole == -1 else "m1"] += len(energy)
    widths = np.diff(edges)
    spectra = {
        "energy_edges_eV": edges,
        "e1_cm2_g": channels[-1] / widths,
        "m1_cm2_g": channels[1] / widths,
    }
    spectra["net_bound_bound_cm2_g"] = spectra["e1_cm2_g"] + spectra["m1_cm2_g"]
    summary = {
        "schema_version": "0.1.0",
        "scientific_status": "restricted_atomic_model",
        "model_description": model["description"],
        "element": ions[0]["element"],
        "atomic_mass_u": mass,
        "temperature_eV": temperature_eV,
        "ion_temperature_eV": ion_temperature_eV,
        "electron_density_cm3": electron_density_cm3,
        "mass_density_g_cm3": electron_density_cm3 / zbar * mass * AMU_KG * 1000,
        "charge_fractions": {
            str(i["charge"]): float(f) for i, f in zip(ions, fractions, strict=True)
        },
        "mean_charge": zbar,
        "boundary_charge_fraction": float(fractions[0] + fractions[-1])
        if len(fractions) > 1
        else 1.0,
        "counts": counts,
        "input_sha256": identities,
        "helper_sha256": sha256(__file__),
        "line_shape": "Gaussian UTA plus Doppler, with optional instrumental Gaussian",
        "instrument_sigma_eV": instrument_sigma_eV,
        "uta_ci_applied": apply_uta_ci,
        "omitted_physics": [
            "unlisted configurations and charge states",
            "bound-free",
            "free-free",
            "scattering",
            "continuum lowering",
            "natural and Stark line wings",
            "non-LTE populations",
        ],
        "line_area_cm2_eV_g": {str(k): v for k, v in expected_areas.items()},
        "captured_area_fraction": {
            str(k): float(channels[k].sum() / v) if v else None for k, v in expected_areas.items()
        },
        "checks": {
            "charge_fraction_normalized": bool(np.isclose(fractions.sum(), 1.0)),
            "spectrum_finite_nonnegative": bool(
                np.all(np.isfinite(spectra["net_bound_bound_cm2_g"]))
                and np.all(spectra["net_bound_bound_cm2_g"] >= 0)
            ),
        },
    }
    return summary, spectra


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Output prefix, without suffix")
    parser.add_argument("--temperature-ev", type=float, required=True)
    parser.add_argument("--electron-density-cm3", type=float, required=True)
    parser.add_argument("--ion-temperature-ev", type=float, required=True)
    parser.add_argument("--energy-min-ev", type=float, required=True)
    parser.add_argument("--energy-max-ev", type=float, required=True)
    parser.add_argument("--bins", type=int, required=True)
    parser.add_argument("--instrument-sigma-ev", type=float, default=0.0)
    parser.add_argument("--no-uta-ci", action="store_true")
    args = parser.parse_args()
    if (
        args.bins < 1
        or not np.isfinite(args.energy_min_ev + args.energy_max_ev)
        or not 0 <= args.energy_min_ev < args.energy_max_ev
    ):
        parser.error("Use a finite increasing nonnegative photon-energy range and positive bins")
    edges = np.linspace(args.energy_min_ev, args.energy_max_ev, args.bins + 1)
    summary, spectra = synthesize(
        args.model,
        args.temperature_ev,
        args.electron_density_cm3,
        args.ion_temperature_ev,
        edges,
        args.instrument_sigma_ev,
        not args.no_uta_ci,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(str(args.output) + ".npz", **spectra)
    summary["spectrum_sha256"] = sha256(str(args.output) + ".npz")
    Path(str(args.output) + ".json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({k: summary[k] for k in ("mean_charge", "mass_density_g_cm3", "checks")}))


if __name__ == "__main__":
    main()
