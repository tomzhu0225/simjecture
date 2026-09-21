"""Independent finite-difference evaluator for recorded driven-sheet HDF5 fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np


def named(dataset):
    result = {}
    for row in dataset[:]:
        value = row[1].item()
        if isinstance(value, bytes):
            value = value.decode().strip()
        result[row[0].decode().strip().casefold()] = value
    return result


def fields(path):
    with h5py.File(path) as f:
        boxes = f["bounding box"][:]
        order = np.argsort(boxes[:, 0, 0])
        ordered = boxes[order]
        if not np.allclose(ordered[:, 1, :], [-1, 1]):
            raise ValueError("Expected the declared x-only block decomposition")
        if not np.allclose(ordered[:-1, 0, 1], ordered[1:, 0, 0]):
            raise ValueError("Blocks have gaps or overlap")
        if not np.allclose([ordered[0, 0, 0], ordered[-1, 0, 1]], [-1, 1]):
            raise ValueError("Unexpected domain")
        data = {
            k: np.concatenate([np.asarray(f[k][b, 0], dtype=float) for b in order], axis=1)
            for k in ["magx", "magy", "dens", "pres", "divb"]
        }
        t = float(named(f["real scalars"])["time"])
        params = named(f["real runtime parameters"])
        params.update(named(f["integer runtime parameters"]))
        params.update(named(f["string runtime parameters"]))
        params.update(named(f["logical runtime parameters"]))
    shape = data["magx"].shape
    if shape[0] != shape[1] or any(x.shape != shape for x in data.values()):
        raise ValueError("Expected a uniform square grid")
    return t, data, params


def core_q(bx, by, eta):
    ny, nx = bx.shape
    dx = 2 / nx
    dy = 2 / ny
    x = -1 + (np.arange(nx) + 0.5) * dx
    y = -1 + (np.arange(ny) + 0.5) * dy
    current = np.gradient(by, dx, axis=1, edge_order=2) - np.gradient(bx, dy, axis=0, edge_order=2)
    mask = (np.abs(y[:, None]) < 0.5) & (np.abs(x[None, :]) < 0.5)
    return float(eta * np.sum(current[mask] ** 2) * dx * dy)


def analyze(directory):
    directory = Path(directory)
    rows = []
    parameters = None
    initial = None
    initial_time = float("inf")
    for path in sorted(directory.glob("sheet_*hdf5_plt_cnt_*")):
        t, u, parameters = fields(path)
        ny, nx = u["magx"].shape
        x = -1 + (np.arange(nx) + 0.5) * 2 / nx
        if t < initial_time:
            initial_time = t
            initial = dict(
                max_By_profile_error=float(np.max(np.abs(u["magy"] - np.tanh(x[None, :] / 0.05)))),
                mode_amplitude=float(2 * np.mean(u["magy"] * np.sin(np.pi * x)[None, :])),
            )
        field_hash = hashlib.sha256(b"".join(u[k].tobytes() for k in sorted(u))).hexdigest()
        rows.append(
            dict(
                time=t,
                field_sha256=field_hash,
                Q=core_q(u["magx"], u["magy"], parameters["resistivity"]),
                mode_amplitude=float(2 * np.mean(u["magy"] * np.sin(np.pi * x)[None, :])),
                min_density=float(u["dens"].min()),
                min_pressure=float(u["pres"].min()),
                max_abs_divb=float(np.max(np.abs(u["divb"]))),
                finite=all(np.isfinite(x).all().item() for x in u.values()),
            )
        )
    rows.sort(key=lambda x: x["time"])
    source_snapshot_count = len(rows)
    unique = []
    for row in rows:
        if unique and row["time"] == unique[-1]["time"]:
            if row["field_sha256"] != unique[-1]["field_sha256"]:
                raise ValueError("Different fields share a simulation time")
            continue
        unique.append(row)
    rows = unique
    if (
        not rows
        or abs(rows[0]["time"]) > 1e-12
        or any(b["time"] <= a["time"] for a, b in zip(rows, rows[1:], strict=False))
    ):
        raise ValueError("Missing initial state or duplicate/nonmonotone times")
    times = np.array([x["time"] for x in rows])
    q = np.array([x["Q"] for x in rows])
    integral = float(np.sum(0.5 * (q[1:] + q[:-1]) * np.diff(times)))
    result = dict(
        n=nx,
        eta=parameters["resistivity"],
        A=parameters.get("sim_amplitude"),
        mode=parameters.get("sim_mode"),
        cfl=parameters.get("cfl"),
        interval=parameters.get("plotfileintervaltime"),
        nu=parameters.get("diff_visc_nu"),
        phase=parameters.get("sim_phase"),
        wavelength=parameters.get("sim_wavelength"),
        gamma=parameters.get("gamma"),
        seed=parameters.get("sim_seed"),
        physical_switches={
            k: bool(parameters.get(k))
            for k in ["usehydro", "usemagneticresistivity", "useviscosity", "useexplicitviscosity"]
        },
        boundaries={
            k: parameters.get(k)
            for k in [
                "xl_boundary_type",
                "xr_boundary_type",
                "yl_boundary_type",
                "yr_boundary_type",
            ]
        },
        D=integral,
        final_time=rows[-1]["time"],
        snapshot_count=len(rows),
        source_snapshot_count=source_snapshot_count,
        min_density=min(x["min_density"] for x in rows),
        min_pressure=min(x["min_pressure"] for x in rows),
        max_abs_divb=max(x["max_abs_divb"] for x in rows),
        finite=all(x["finite"] for x in rows),
        initial=initial,
        rows=rows,
    )
    if abs(rows[0]["mode_amplitude"]) > 1e-10:
        result["amplitude_ratio"] = rows[-1]["mode_amplitude"] / rows[0]["mode_amplitude"]
        result["analytic_diffusion_ratio"] = float(
            np.exp(-parameters["resistivity"] * np.pi**2 * times[-1])
        )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    results = []
    for entry in json.loads((a.root / "runs.json").read_text()):
        try:
            result = (
                analyze(entry["path"]) if entry["returncode"] == 0 else {"error": "solver failure"}
            )
        except Exception as error:
            result = {"error": str(error)}
        results.append(dict(**entry, analysis=result))
    a.output.write_text(json.dumps(results, indent=2) + "\n")
    for r in results:
        print(r["index"], {k: v for k, v in r["analysis"].items() if k != "rows"})


if __name__ == "__main__":
    main()
