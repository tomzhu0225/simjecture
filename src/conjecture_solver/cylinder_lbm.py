"""Recorded execution adapter for Zifei Meng's contributed Warp cylinder solver.

This file is also installed as a standalone driver in the optional runtime.
Dependencies are imported only when a simulation or analysis is requested.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from pathlib import Path


def load_solver(path):
    path = Path(path).resolve(strict=True)
    spec = importlib.util.spec_from_file_location("cylinder_warp_lbm_solver", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, path


def force_statistics(cd, cl, nd, speed, cycles=10):
    """Use the final complete lift periods, with dimensionless time tU/D."""
    import numpy as np

    if len(cd) != len(cl) or len(cd) < 2 or not np.isfinite([cd, cl]).all():
        raise ValueError("Force histories must have equal finite samples")
    tail = cl[len(cl) // 2 :]
    fluctuation = tail - tail.mean()
    baseline = {
        "n_cycles": 0,
        "St": None,
        "Cd_mean": float(cd[len(cd) // 2 :].mean()),
        "Cl_mean": float(tail.mean()),
        "Cl_rms": float(np.sqrt(np.mean(fluctuation**2))),
        "window_tU_over_D": [(len(cl) // 2 + 1) * speed / nd, len(cl) * speed / nd],
        "periodic_statistics_qualified": False,
    }
    if np.ptp(tail) < 1e-8:
        return baseline
    offset = cl - tail.mean()
    indices = np.flatnonzero((offset[:-1] < 0) & (offset[1:] >= 0))
    crossings = indices + (-offset[indices]) / (offset[indices + 1] - offset[indices])
    crossings = crossings[crossings > 0.4 * len(cl)]
    if len(crossings) < 3:
        return baseline
    count = min(cycles, len(crossings) - 1)
    crossings = crossings[-count - 1 :]
    periods = np.diff(crossings)
    first, last = int(math.ceil(crossings[0])), int(math.floor(crossings[-1]))
    selected = cl[first:last]
    amplitudes = []
    for a, b in zip(crossings[:-1], crossings[1:], strict=True):
        segment = cl[int(math.ceil(a)) : int(math.floor(b))]
        if not len(segment):
            return baseline
        amplitudes.append(float(np.ptp(segment) / 2))
    baseline.update(
        n_cycles=int(count),
        St=float(nd / (speed * periods.mean())),
        Cd_mean=float(cd[first:last].mean()),
        Cl_mean=float(selected.mean()),
        Cl_rms=float(selected.std()),
        Cl_rms_about_zero=float(np.sqrt(np.mean(selected**2))),
        period_relative_std=float(periods.std() / periods.mean()),
        lift_amplitude_drift=float(amplitudes[-1] / amplitudes[0] - 1),
        window_tU_over_D=[(first + 1) * speed / nd, last * speed / nd],
        periodic_statistics_qualified=bool(count == cycles),
    )
    return baseline


def simulate(args):
    import numpy as np
    import warp as wp

    solver, source = load_solver(args.solver_source)
    overrides = {
        "nd": args.nd,
        "u": args.speed,
        "H": args.height,
        "L": args.length,
        "xc": args.inlet,
        "tconv": args.time,
        "cs": 0.0,
    }
    cfg = solver.make_config(args.re, override=overrides)
    if args.steps is not None:
        if args.steps < 1:
            raise ValueError("steps must be positive")
        cfg["steps"] = args.steps
    cells = cfg["nx"] * cfg["ny"]
    if cells > args.max_cells:
        raise ValueError(f"Requested {cells} cells exceeds this launch's {args.max_cells} limit")
    wp.init()
    device = args.device
    if device == "auto":
        device = "cuda:0" if wp.is_cuda_available() else "cpu"
    sim = solver.CylinderLBM(
        cfg,
        device=device,
        fp64=args.fp64,
        wall=args.wall,
        delta=args.interface_width,
        psm=args.psm,
        side_sponge_len=args.side_sponge,
        out_eq_sponge_len=args.outlet_sponge,
    )
    # Reuse the contributor's parameter validation and normalization convention.
    solver.apply_body_args(
        sim,
        cfg,
        argparse.Namespace(
            shape_a=args.shape_a,
            shape_b=args.shape_b,
            omega=args.rotation,
            aoa=args.angle,
            jet_c=None,
            jet_s=None,
        ),
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    state, forces = sim.run(cfg["steps"])
    elapsed = time.perf_counter() - started
    fields, solid = sim.macro(state), sim.solid_map()
    cd, cl = forces[:, 0] * sim.qinv, forces[:, 1] * sim.qinv
    stats = force_statistics(cd, cl, cfg["nd"], cfg["u"])
    tstar = (np.arange(len(forces)) + 1) * cfg["u"] / cfg["nd"]
    np.savez_compressed(out / "forces.npz", t_star=tstar, Cd=cd, Cl=cl)
    np.savetxt(
        out / "forces.csv",
        np.column_stack((tstar, cd, cl)),
        delimiter=",",
        header="t_star,Cd,Cl",
        comments="",
    )
    # Retain an explicitly labelled wake crop, rather than silently downsampling
    # a full domain. The full force history and full-domain health checks remain.
    nd = cfg["nd"]
    x0, x1 = max(0, int(cfg["cx"] - 4 * nd)), min(cfg["nx"], int(cfg["cx"] + 16 * nd))
    y0, y1 = max(0, int(cfg["cy"] - 4 * nd)), min(cfg["ny"], int(cfg["cy"] + 4 * nd))
    window = (slice(x0, x1), slice(y0, y1))
    omega = (np.gradient(fields[2], axis=0) - np.gradient(fields[1], axis=1)) * nd / cfg["u"]
    x = (np.arange(x0, x1) - cfg["cx"]) / nd
    y = (np.arange(y0, y1) - cfg["cy"]) / nd
    np.savez_compressed(
        out / "fields.npz",
        x_over_D=x,
        y_over_D=y,
        rho=fields[0][window].astype(np.float32),
        ux_over_U=(fields[1][window] / cfg["u"]).astype(np.float32),
        uy_over_U=(fields[2][window] / cfg["u"]).astype(np.float32),
        omega_D_over_U=omega[window].astype(np.float32),
        solid=solid[window].astype(np.float32),
    )
    checks = {
        "completed": True,
        "finite_forces": bool(np.isfinite(forces).all()),
        "finite_fields": bool(np.isfinite(fields).all()),
        "positive_density": bool((fields[0] > 0).all()),
    }
    summary = {
        "schema_version": "0.1.0",
        "solver": "Cylinder Warp-LBM",
        "author": "Zifei Meng",
        "author_url": "https://github.com/ZifeiMengSPH",
        "method": "D2Q9 MRT-LBM / smooth PSM",
        "configuration": cfg,
        "parameters": sim.get_params().tolist(),
        "boundary": {
            "wall": args.wall,
            "psm": args.psm,
            "interface_width_lattice": args.interface_width,
            "side_sponge_D": args.side_sponge,
            "outlet_equilibrium_sponge_D": args.outlet_sponge,
            "outlet_viscosity_sponge_D": 3.0,
            "outlet_viscosity_sponge_max": 0.7,
        },
        "device": str(sim.dev),
        "precision": "float64" if args.fp64 else "float32",
        "completed_steps": len(forces),
        "final_tU_over_D": float(tstar[-1]),
        "solver_wall_seconds": elapsed,
        "million_cell_updates_per_second": cells * len(forces) / elapsed / 1e6,
        "minimum_density": float(fields[0].min()),
        "maximum_density": float(fields[0].max()),
        "statistics": stats,
        "checks": checks,
        "field_output": {
            "scope": "Final wake crop",
            "full_domain": False,
            "lattice_bounds": [x0, x1, y0, y1],
            "time_tU_over_D": float(tstar[-1]),
        },
        "units": {
            "time": "tU/D",
            "coordinates": "D from cylinder centre",
            "velocity": "U",
            "vorticity": "U/D",
            "density": "initial density",
            "forces": "0.5*rho0*U^2*D per unit span",
        },
        "provenance": {
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "warp_version": wp.__version__,
            "numpy_version": np.__version__,
        },
        "scope": (
            "2D isothermal weakly compressible hydrodynamics. "
            "Runtime health and periodic statistics do not certify "
            "grid/domain convergence or a research claim."
        ),
    }
    if not all(checks.values()):
        raise ValueError("Numerical health checks failed")
    if not args.no_plot:
        plot(out, summary)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "completed": True,
                "output": str(out),
                "statistics": stats,
                "solver_wall_seconds": elapsed,
            },
            allow_nan=False,
        ),
        flush=True,
    )
    return summary


def plot(out, summary):
    import matplotlib
    import numpy as np

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    with np.load(out / "fields.npz", allow_pickle=False) as data:
        x, y = data["x_over_D"], data["y_over_D"]
        field = np.ma.masked_where(data["solid"] > 0.5, data["omega_D_over_U"])
    with np.load(out / "forces.npz", allow_pickle=False) as data:
        t, cd, cl = data["t_star"], data["Cd"], data["Cl"]
    fig, axes = plt.subplots(3, 1, figsize=(11, 8), layout="constrained")
    image = axes[0].pcolormesh(x, y, field.T, cmap="RdBu_r", vmin=-4, vmax=4, shading="auto")
    axes[0].contour(x, y, np.asarray(field.mask).T.astype(float), levels=[0.5], colors="black")
    axes[0].set(
        xlabel="x/D from cylinder centre",
        ylabel="y/D",
        title=f"Cylinder wake · Re={summary['configuration']['re']:g} · tU/D={t[-1]:.2f}",
    )
    axes[0].set_aspect("equal")
    fig.colorbar(image, ax=axes[0], label="Vorticity ωD/U")
    skip = max(1, len(t) // 10000)
    for ax, values, label in [(axes[1], cd, "Drag Cd"), (axes[2], cl, "Lift Cl")]:
        ax.plot(t[::skip], values[::skip], lw=0.8)
        if summary["statistics"]["n_cycles"]:
            ax.axvspan(*summary["statistics"]["window_tU_over_D"], alpha=0.15, color="green")
        ax.set(xlabel="Time tU/D", ylabel=label)
        ax.grid(alpha=0.2)
    fig.savefig(out / "evolution.png", dpi=150)
    plt.close(fig)


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    default_source = os.environ.get(
        "SIMJECTURE_LBM_SOURCE", str(Path(__file__).parent / "source/cylinder_warp_lbm_solver.py")
    )
    p.add_argument("--solver-source", default=default_source)
    p.add_argument("--out", default="outputs")
    p.add_argument("--device", default="auto")
    p.add_argument("--re", type=float, default=100)
    p.add_argument("--nd", type=int, default=24)
    p.add_argument("--speed", type=float, default=0.06)
    p.add_argument("--height", type=float, default=24)
    p.add_argument("--length", type=float, default=48)
    p.add_argument("--inlet", type=float, default=16)
    p.add_argument("--time", type=float, default=180)
    p.add_argument("--steps", type=int)
    p.add_argument("--max-cells", type=int, default=50_000_000)
    p.add_argument("--wall", choices=["far", "slip", "noslip", "periodic"], default="far")
    p.add_argument("--psm", choices=["nt", "linear"], default="nt")
    p.add_argument("--interface-width", type=float, default=0.5)
    p.add_argument("--side-sponge", type=float, default=0)
    p.add_argument("--outlet-sponge", type=float, default=0)
    p.add_argument("--rotation", type=float, default=0)
    p.add_argument("--angle", type=float, default=0)
    p.add_argument("--shape-a")
    p.add_argument("--shape-b")
    p.add_argument("--fp64", action="store_true")
    p.add_argument("--no-plot", action="store_true")
    return p


if __name__ == "__main__":
    simulate(parser().parse_args())
