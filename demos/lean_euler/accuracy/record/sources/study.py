"""Total work/time at matched solution error for a specified smooth 3D Euler family."""

import argparse
import hashlib
import importlib.util
import json
import random
import time
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("cache_experiment", "experiment.py")
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)
reference = cache.reference
VELOCITY = np.array([0.5, 0.2, -0.1])


def exact_state(n, t):
    x = (np.arange(n) + 0.5) / n
    phase = x[:, None, None] + x[None, :, None] + x[None, None, :]
    rho = 1 + 0.1 * np.sinc(1 / n) ** 3 * np.sin(2 * np.pi * (phase - VELOCITY.sum() * t))
    u = np.empty((n, n, n, 5))
    u[..., 0] = rho
    u[..., 1:4] = rho[..., None] * VELOCITY
    u[..., 4] = 1 + 0.5 * rho * np.sum(VELOCITY**2)
    return u


def primitives(u):
    p = reference.pressure(u)
    if np.min(u[..., 0]) <= 0 or np.min(p) <= 0:
        raise ValueError("non-admissible state")
    sound = np.sqrt(2 * p / u[..., 0])
    velocity = tuple(u[..., a + 1] / u[..., 0] for a in range(3))
    return p, sound, velocity


def prepared_step(u, dt, dx, prim):
    p, sound, velocities = prim
    new = u.copy()
    for a, v in enumerate(velocities):
        f = u * v[..., None]
        f[..., a + 1] += p
        f[..., 4] += p * v
        speed = abs(v) + sound
        alpha = np.maximum(speed, np.roll(speed, -1, axis=a))
        face = (f + np.roll(f, -1, axis=a) - alpha[..., None] * (np.roll(u, -1, axis=a) - u)) / 2
        new -= dt / dx * (face - np.roll(face, 1, axis=a))
    return new


def minmod3(a, b, c):
    same = (np.sign(a) == np.sign(b)) & (np.sign(b) == np.sign(c))
    return np.where(same, np.sign(a) * np.minimum(np.minimum(abs(a), abs(b)), abs(c)), 0.0)


def muscl_rhs(u, dx):
    rhs = np.zeros_like(u)
    for axis in range(3):
        minus = u - np.roll(u, 1, axis=axis)
        plus = np.roll(u, -1, axis=axis) - u
        slope = minmod3(2 * minus, 0.5 * (minus + plus), 2 * plus)
        left = u + 0.5 * slope
        right = np.roll(u - 0.5 * slope, -1, axis=axis)
        # Reject invalid reconstructed faces; this demo has no general positivity limiter.
        if min(reference.pressure(left).min(), reference.pressure(right).min()) <= 0:
            raise ValueError("nonpositive reconstructed pressure")
        if min(left[..., 0].min(), right[..., 0].min()) <= 0:
            raise ValueError("nonpositive reconstructed density")
        fl, sl = reference.flux(left, axis)
        fr, sr = reference.flux(right, axis)
        face = (fl + fr - np.maximum(sl, sr)[..., None] * (right - left)) / 2
        rhs -= (face - np.roll(face, 1, axis=axis)) / dx
    return rhs


def solve(n, method, final_time, cfl):
    begin = time.perf_counter()
    u = exact_state(n, 0)
    t = 0.0
    steps = 0
    stages = 0
    eos = 0
    min_density = float(u[..., 0].min())
    min_pressure = float(reference.pressure(u).min())
    eos += n**3
    dt_history = []
    while t < final_time:
        if method in ["reference", "cached"]:
            speed = sum(reference.flux(u, a)[1].max() for a in range(3))
            eos += 3 * n**3
            dt = min(final_time - t, cfl / (n * speed))
            kernel = reference.step if method == "reference" else cache.cached_step
            u = kernel(u, dt, 1 / n)
            eos += (3 if method == "reference" else 1) * n**3
            stages += 1
        else:
            prim = primitives(u)
            eos += n**3
            speed = sum((abs(v) + prim[1]).max() for v in prim[2])
            dt = min(final_time - t, cfl / (n * speed))
            if method == "fused":
                u = prepared_step(u, dt, 1 / n, prim)
                stages += 1
            elif method == "muscl_rk2":
                first = u + dt * muscl_rhs(u, 1 / n)
                # 6 reconstructed-face pressure validations + 6 flux EOS calls/stage.
                eos += 12 * n**3
                if min(first[..., 0].min(), reference.pressure(first).min()) <= 0:
                    raise ValueError("non-admissible RK stage")
                eos += n**3
                u = 0.5 * u + 0.5 * (first + dt * muscl_rhs(first, 1 / n))
                eos += 12 * n**3
                stages += 2
            else:
                raise ValueError(method)
        steps += 1
        t += dt
        dt_history.append(dt)
        p = reference.pressure(u)
        eos += n**3
        min_density = min(min_density, float(u[..., 0].min()))
        min_pressure = min(min_pressure, float(p.min()))
        if not np.all(np.isfinite(u)) or min_density <= 0 or min_pressure <= 0:
            raise ValueError("non-admissible step")
    seconds = time.perf_counter() - begin
    return u, dict(
        n=n,
        method=method,
        steps=steps,
        stages=stages,
        cell_stage_updates=stages * n**3,
        eos_cell_evaluations=eos,
        solver_seconds=seconds,
        final_time=t,
        timestep_sha256=hashlib.sha256(
            np.asarray(dt_history, dtype=np.float64).tobytes()
        ).hexdigest(),
        min_density=min_density,
        min_pressure=min_pressure,
    )


def assess(u, row, target_time):
    begin = time.perf_counter()
    n = row["n"]
    if abs(row["final_time"] - target_time) > 1e-12:
        raise ValueError("Solver did not reach the required physical time")
    exact = exact_state(n, target_time)
    err = abs(u - exact)
    row.update(
        component_l1=err.mean(axis=(0, 1, 2)).tolist(),
        component_linf=err.max(axis=(0, 1, 2)).tolist(),
        density_l1=float(err[..., 0].mean()),
        pressure_linf=float(np.max(abs(reference.pressure(u) - 1))),
        velocity_linf=float(np.max(abs(u[..., 1:4] / u[..., 0, None] - VELOCITY))),
        conserved_total_drift=(
            u.mean(axis=(0, 1, 2)) - exact_state(n, 0).mean(axis=(0, 1, 2))
        ).tolist(),
    )
    row["analysis_seconds"] = time.perf_counter() - begin
    row["solution_sha256"] = hashlib.sha256(u.tobytes()).hexdigest()
    return row


def select(rows, targets, methods):
    choices = []
    for eps in targets:
        for method in methods:
            eligible = [r for r in rows if r["method"] == method and r["density_l1"] <= eps]
            selected = min(eligible, key=lambda r: r["cell_stage_updates"]) if eligible else None
            choices.append(
                dict(
                    epsilon=eps,
                    method=method,
                    minimum_sampled_work=selected,
                    fastest_sampled_wall=min(eligible, key=lambda r: r["median_solver_seconds"])
                    if eligible
                    else None,
                    status="attained_on_sampled_grid" if selected else "unattained",
                )
            )
    return choices


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default="contract.json")
    parser.add_argument("--output", default="accuracy.json")
    args = parser.parse_args()
    contract = json.loads(Path(args.contract).read_text())
    rows = []
    rng = random.Random(20261101)
    for n in contract["grids"]:
        # All methods are evaluated at the same grid and physical time, even if one misses a target.
        for trial in range(contract["trials"]):
            methods = list(contract["methods"])
            rng.shuffle(methods)
            for method in methods:
                u, row = solve(n, method, contract["final_time"], contract["cfl"])
                row = assess(u, row, contract["final_time"])
                row["trial"] = trial
                rows.append(row)
                print(
                    json.dumps(
                        {
                            k: row[k]
                            for k in [
                                "n",
                                "method",
                                "trial",
                                "steps",
                                "density_l1",
                                "solver_seconds",
                            ]
                        }
                    ),
                    flush=True,
                )
    summary = []
    for n in contract["grids"]:
        for method in contract["methods"]:
            selected = [r for r in rows if r["n"] == n and r["method"] == method]
            first = selected[0]
            assert len({r["solution_sha256"] for r in selected}) == 1
            summary.append(
                {
                    k: v
                    for k, v in first.items()
                    if k not in ["trial", "solver_seconds", "analysis_seconds"]
                }
                | dict(
                    median_solver_seconds=float(np.median([r["solver_seconds"] for r in selected])),
                    median_analysis_seconds=float(
                        np.median([r["analysis_seconds"] for r in selected])
                    ),
                )
            )
        hashes = [
            r["solution_sha256"]
            for r in summary
            if r["n"] == n and r["method"] in ["reference", "cached", "fused"]
        ]
        assert len(set(hashes)) == 1, "First-order variants changed the solution"
    result = dict(
        contract=contract,
        rows=rows,
        summary=summary,
        choices=select(summary, contract["accuracy_targets"], contract["methods"]),
        scope=(
            "Measured work to an analytic Euler solution error on a finite test catalogue; "
            "no global optimality claim"
        ),
        sources={
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in ["euler.py", "experiment.py", "study.py", args.contract]
        },
    )
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
