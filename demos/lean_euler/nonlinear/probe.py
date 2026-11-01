"""Commission coupled Euler dynamics; no exact positive-time solution is supplied."""

import argparse
import hashlib
import importlib.util
import json
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / "euler.py"
spec = importlib.util.spec_from_file_location("nonlinear_reference", REFERENCE)
euler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(euler)


def initial(n, amplitude, delta):
    c = (np.arange(n) + 0.5) * (2 * np.pi / n)
    x, y, z = np.meshgrid(c, c, c, indexing="ij")
    rho = 1 + delta * np.sin(x) * np.sin(y) * np.sin(z)
    velocity = np.stack(
        [
            amplitude * np.sin(x) * np.cos(y) * np.cos(z),
            -amplitude * np.cos(x) * np.sin(y) * np.cos(z),
            np.zeros_like(x),
        ],
        axis=-1,
    )
    pressure = 1 + (amplitude**2 / 16) * (np.cos(2 * x) + np.cos(2 * y)) * (np.cos(2 * z) + 2)
    state = np.empty((n, n, n, 5))
    state[..., 0] = rho
    state[..., 1:4] = rho[..., None] * velocity
    state[..., 4] = pressure + 0.5 * rho * np.sum(velocity**2, axis=-1)
    return state


def run(n, amplitude, delta, final_time=0.25):
    started = time.perf_counter()
    u = initial(n, amplitude, delta)
    original = u.copy()
    p0 = euler.pressure(original)
    t, steps = 0.0, 0
    dx = 2 * np.pi / n
    while t < final_time:
        speed = sum(float(euler.flux(u, d)[1].max()) for d in range(3))
        dt = min(final_time - t, 0.25 * dx / speed)
        u = euler.step(u, dt, dx)
        t += dt
        steps += 1
        if not np.all(np.isfinite(u)) or u[..., 0].min() <= 0 or euler.pressure(u).min() <= 0:
            raise AssertionError("Non-admissible baseline state")
    p = euler.pressure(u)
    drift = np.max(np.abs(u.mean(axis=(0, 1, 2)) - original.mean(axis=(0, 1, 2))))
    result = dict(
        n=n,
        A=amplitude,
        delta=delta,
        final_time=t,
        steps=steps,
        cell_updates=steps * n**3,
        max_abs_vertical_velocity=float(np.max(np.abs(u[..., 3] / u[..., 0]))),
        max_abs_pressure_change=float(np.max(np.abs(p - p0))),
        max_abs_density_change=float(np.max(np.abs(u[..., 0] - original[..., 0]))),
        min_density=float(u[..., 0].min()),
        min_pressure=float(p.min()),
        mean_conserved_drift=float(drift),
        solver_seconds=time.perf_counter() - started,
    )
    assert result["max_abs_vertical_velocity"] > 1e-4
    assert result["max_abs_pressure_change"] > 1e-4
    assert drift < 1e-11
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rows = [run(n, a, d) for a, d in [(0.5, -0.05), (0.75, 0.0), (1.0, 0.05)] for n in [16, 32]]
    result = dict(
        scope=(
            "Initial nonlinear dynamics commissioning only; "
            "no continuum accuracy or optimality claim"
        ),
        initialization="Cell-center conservative states; not exact cell averages",
        method="Existing first-order gamma=2 Rusanov finite-volume baseline",
        rows=rows,
        analytic_witness="At (0,0,pi/4), initial vertical acceleration is A^2/4 >= 1/16",
        sources={
            str(p.relative_to(HERE.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__).resolve(), REFERENCE, HERE / "contract.json"]
        },
    )
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
