"""Verifier-owned diagnostic definitions; never import submitted code here."""

import csv
import math
from pathlib import Path

ENERGIES = ("kinetic_erg", "magnetic_erg", "internal_erg")


def number(row, name):
    value = float(row[name])
    if not math.isfinite(value):
        raise ValueError(f"Nonfinite {name}")
    return value


def csv_result(directory):
    directory = Path(directory)
    with (directory / "radiation_boundary.csv").open() as stream:
        radiation = list(csv.DictReader(stream))
    if not radiation:
        raise ValueError("Missing radiation records")
    increments = {}
    for row in radiation:
        clock = number(row, "time_s")
        if clock <= 0:
            raise ValueError("Radiation clock must be positive")
        increments[clock] = increments.get(clock, 0) + number(row, "escaped_energy_erg") * 1e-7
    with (directory / "operator_budget.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    before = [row for row in rows if row["tag"] == "radiation_before"]
    after = [row for row in rows if row["tag"] == "radiation_after"]
    if not before or len(before) != len(after):
        raise ValueError("Unpaired radiation stages")
    loss = 0.0
    for start, end in zip(before, after, strict=True):
        if number(start, "time_s") != number(end, "time_s"):
            raise ValueError("Radiation stage clocks differ")
        loss += sum(number(start, key) - number(end, key) for key in ENERGIES) * 1e-7
    total = sum(increments.values())
    time = [0.0, *sorted(increments)]
    cumulative = [0.0]
    for clock in time[1:]:
        cumulative.append(cumulative[-1] + increments[clock])
    return {
        "E_rad_total_J": total,
        "radiation_operator_loss_J": loss,
        "radiation_relative_difference": abs(total - loss) / max(abs(total), 1e-12),
    }, {"radiation_time_s": time, "cumulative_radiation_J": cumulative}


def tracer_radius(radii, masses):
    """Half-mass radius in cm, independent of ordering at equal radii."""
    import numpy as np

    radii, masses = np.asarray(radii, dtype=float), np.asarray(masses, dtype=float)
    if (
        radii.ndim != 1
        or radii.shape != masses.shape
        or not len(radii)
        or not np.all(np.isfinite(radii))
        or not np.all(np.isfinite(masses))
        or np.any(radii < 0)
        or np.any(masses < 0)
    ):
        raise ValueError("Invalid tracer radii or masses")
    centres, inverse = np.unique(radii, return_inverse=True)
    grouped = np.bincount(inverse, weights=masses)
    positive = grouped > 0
    centres, grouped = centres[positive], grouped[positive]
    if not len(centres):
        raise ValueError("Missing positive leaf tracer mass")
    cumulative = np.cumsum(grouped)
    return float(np.interp(0.5 * cumulative[-1], cumulative, centres))


def rz_result(directory):
    import h5py
    import numpy as np

    directory = Path(directory)
    records = []
    for path in sorted(directory.glob("stagnation_hdf5_plt_cnt_*")):
        with h5py.File(path) as file:
            scalar = {k.decode().strip(): float(v) for k, v in file["real scalars"][:]}
            total = np.zeros(5)
            radii, masses = [], []
            for block in np.flatnonzero(file["node type"][:] == 1):
                rho = np.asarray(file["dens"][block], dtype=np.float64)
                if not np.all(np.isfinite(rho)) or np.any(rho <= 0):
                    raise ValueError("Invalid density")
                dummy, nz, nr = rho.shape
                if dummy != 1:
                    raise ValueError("Expected 2D RZ field layout")
                bounds = np.asarray(file["bounding box"][block], dtype=np.float64)
                dr = (bounds[0, 1] - bounds[0, 0]) / nr
                dz = (bounds[1, 1] - bounds[1, 0]) / nz
                if dr <= 0 or dz <= 0 or bounds[0, 0] < 0:
                    raise ValueError("Invalid RZ geometry")
                radius = np.broadcast_to(bounds[0, 0] + (np.arange(nr) + 0.5) * dr, rho.shape)
                volume = 2 * np.pi * radius * dr * dz
                vr, vy, vz = (
                    np.asarray(file[key][block], dtype=np.float64)
                    for key in ("velx", "vely", "velz")
                )
                magnetic = sum(
                    np.asarray(file[key][block], dtype=np.float64) ** 2
                    for key in ("magx", "magy", "magz")
                )
                values = [
                    rho,
                    0.5 * rho * np.maximum(-vr, 0) ** 2,
                    0.5 * rho * (vr**2 + vy**2 + vz**2),
                    0.5 * magnetic,
                    rho * np.asarray(file["eint"][block], dtype=np.float64),
                ]
                total += [np.sum(value * volume) for value in values]
                radii.extend(radius.ravel())
                tracer = np.asarray(file["line"][block], dtype=np.float64)
                masses.extend((rho * tracer * volume).ravel())
            r50 = tracer_radius(radii, masses) * 10
            records.append([scalar["time"], total[0], *(total[1:] * 1e-7), r50])
    a = np.array(records)
    if len(records) < 2 or not np.all(np.isfinite(a)) or np.any(np.diff(a[:, 0]) <= 0):
        raise ValueError("Missing, nonfinite or unordered HDF5 records")
    peak = float(a[:, 2].max())
    if peak <= 0:
        raise ValueError("No inward kinetic reference")
    ref = float(a[a[:, 2].argmax(), 0])
    mask = a[:, 6] <= 1.3 * a[:, 6].min()
    lo, hi = float(a[mask, 0][0]), float(a[mask, 0][-1])
    result, curves = csv_result(directory)
    rt, er = curves["radiation_time_s"], curves["cumulative_radiation_J"]
    if rt[-1] < a[-1, 0]:
        raise ValueError("Radiation clock does not cover HDF5 span")
    compressed = float(np.interp(hi, rt, er) - np.interp(lo, rt, er))
    stored = a[:, 3] + a[:, 4] + a[:, 5]
    result.update(
        t_ref_ns=ref * 1e9,
        compression_bounds_ns=[lo * 1e9, hi * 1e9],
        K_in_peak_J=peak,
        E_rad_after_ref_J=float(er[-1] - np.interp(ref, rt, er)),
        E_rad_compression_J=compressed,
        delta_stored_J=float(stored[-1] - stored[0]),
        mass_relative_drift=float((a[-1, 1] - a[0, 1]) / a[0, 1]),
        broadband_ratio=result["E_rad_total_J"] / peak,
        compression_ratio=compressed / peak,
        compression_exceeds_peak=bool(compressed > peak),
        whole_domain_closure_established=False,
        mechanism_proven=False,
    )
    curves.update(
        time_s=a[:, 0].tolist(),
        inward_kinetic_J=a[:, 2].tolist(),
        stored_energy_J=stored.tolist(),
        tracer_r50_mm=a[:, 6].tolist(),
    )
    return result, curves


def reduce_case(directory, task="rz-diagnostics"):
    return (csv_result if task == "csv-energy" else rz_result)(directory)[0]


def comparisons(actual, target, prefix=""):
    import numpy as np

    checks = []
    for key, expected in target.items():
        value = actual.get(key) if isinstance(actual, dict) else None
        if isinstance(expected, bool):
            passed = value is expected
        else:
            try:
                passed = (
                    np.shape(value) == np.shape(expected)
                    and np.all(np.isfinite(np.asarray(value, dtype=float)))
                    and np.allclose(
                        value, expected, rtol=1e-7, atol=1e-18 if key.endswith("time_s") else 1e-8
                    )
                )
            except (TypeError, ValueError):
                passed = False
        checks.append({"metric": prefix + key, "passed": bool(passed)})
    return checks
