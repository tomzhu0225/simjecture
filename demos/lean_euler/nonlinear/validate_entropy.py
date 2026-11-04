"""Measure actual-step entropy loss; observations are not a continuum certificate."""

import argparse
import hashlib
import json
from pathlib import Path

import finite_volume as fv
import numpy as np


def entropy(u):
    rho, p = u[..., 0], fv.pressure(u)
    if np.min(rho) <= 0 or np.min(p) <= 0:
        raise ValueError("Entropy diagnostic requires an admissible state")
    return -rho * (np.log(p) - 2 * np.log(rho))


def relative_entropy(u):
    return float(entropy(u).mean() - entropy(u.mean(axis=(0, 1, 2))))


def trajectory(n, amplitude, delta):
    u = fv.cell_averages(n, amplitude, delta)
    initial = u.copy()
    dx, time, count = 2 * np.pi / n, 0.0, 0
    entropy_initial = float(entropy(u).mean())
    initial_relative = relative_entropy(u)
    drops, scaled_drops, edge_ratios = [], [], []
    min_rho, max_rho, min_p, max_p, max_v = float("inf"), 0.0, float("inf"), 0.0, 0.0

    def measure_bounds(state):
        nonlocal min_rho, max_rho, min_p, max_p, max_v
        p, v, speeds = fv.primitives(state)
        min_rho, max_rho = (
            min(min_rho, float(state[..., 0].min())),
            max(max_rho, float(state[..., 0].max())),
        )
        min_p, max_p = min(min_p, float(p.min())), max(max_p, float(p.max()))
        max_v = max(max_v, float(np.max(np.abs(v))))
        return speeds

    while time < 0.25:
        speeds = measure_bounds(u)
        dt = min(0.25 - time, 0.3 * dx / speeds.sum())
        before = float(entropy(u).mean())
        relative_before = relative_entropy(u)
        edge_squared = sum(
            float(np.mean(np.sum((np.roll(u, -1, axis=d) - u) ** 2, axis=-1))) for d in range(3)
        )
        updated = fv.step(u, dt / dx)
        after = float(entropy(updated).mean())
        drop = before - after
        drops.append(drop)
        scaled_drops.append(drop / (dt * dx * relative_before))
        edge_ratios.append(drop / ((dt / dx) * edge_squared))
        u, time, count = updated, time + dt, count + 1
    measure_bounds(u)
    replay_error = None
    if n == 16:
        replay = fv.solve(n, amplitude, delta)
        replay_error = float(np.max(np.abs(replay.field - u)))
        assert replay_error == 0 and replay.steps == count
    loss = entropy_initial - float(entropy(u).mean())
    return dict(
        n=n,
        A=amplitude,
        delta=delta,
        final_time=time,
        cfl=0.3,
        steps=count,
        entropy_initial=entropy_initial,
        entropy_final=float(entropy(u).mean()),
        entropy_loss=loss,
        entropy_loss_over_dx=loss / dx,
        relative_entropy_initial=initial_relative,
        relative_entropy_final=relative_entropy(u),
        minimum_step_entropy_drop=min(drops),
        minimum_drop_over_dt_dx_relative=min(scaled_drops),
        minimum_drop_over_ratio_edge_squared=min(edge_ratios),
        min_density=min_rho,
        max_density=max_rho,
        min_pressure=min_p,
        max_pressure=max_p,
        max_abs_velocity=max_v,
        conservation_error=float(np.max(np.abs(u.mean((0, 1, 2)) - initial.mean((0, 1, 2))))),
        direct_solver_replay_max_error=replay_error,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for amplitude, delta in [(0.5, -0.05), (0.75, 0), (1.0, 0.05)]:
        for n in [16, 32, 64]:
            row = trajectory(n, amplitude, delta)
            rows.append(row)
            print(json.dumps(row), flush=True)
    rng = np.random.default_rng(20261103)
    random_rows = []
    for trial in range(12):
        rho, p = 10 ** rng.uniform(-2, 1, (2, 4, 4, 4))
        v = rng.uniform(-3, 3, (4, 4, 4, 3))
        u = np.empty((4, 4, 4, 5))
        u[..., 0], u[..., 1:4] = rho, rho[..., None] * v
        u[..., 4] = p + rho * np.sum(v * v, axis=-1) / 2
        speeds = fv.primitives(u)[2]
        for cfl in [0.3, 1.0]:
            updated = fv.step(u, cfl / speeds.sum())
            random_rows.append(
                dict(
                    trial=trial,
                    cfl=cfl,
                    mean_entropy_change=float(entropy(updated).mean() - entropy(u).mean()),
                )
            )
    here = Path(__file__).resolve().parent
    result = dict(
        scope=(
            "Observed entropy loss of actual finite-volume updates, including discrete "
            "initial states. No certified continuum error, uniform trajectory bound, "
            "entropy-dissipation theorem, speedup or work-optimality result. Diagnostic "
            "work and replay checks are additional to the candidate solve."
        ),
        rows=rows,
        random_states=random_rows,
        sources={
            name: hashlib.sha256((here / name).read_bytes()).hexdigest()
            for name in ["validate_entropy.py", "finite_volume.py", "contract.json"]
        },
    )
    (args.output / "entropy-validation.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
