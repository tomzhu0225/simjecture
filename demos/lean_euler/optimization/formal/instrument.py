"""Count actual NumPy thermodynamic calls; check mapping and stale-cache failure."""

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("cache_experiment", "experiment.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def counts(kernel, u, dt, dx):
    calls = dict(pressure_calls=0, pressure_cells=0, sqrt_calls=0, sqrt_cells=0)
    pressure = module.reference.pressure
    sqrt = np.sqrt

    def counted_pressure(values, gamma=2):
        calls["pressure_calls"] += 1
        calls["pressure_cells"] += int(np.prod(values.shape[:-1]))
        return pressure(values, gamma)

    def counted_sqrt(values, *args, **kwargs):
        calls["sqrt_calls"] += 1
        calls["sqrt_cells"] += int(np.size(values))
        return sqrt(values, *args, **kwargs)

    module.reference.pressure = counted_pressure
    np.sqrt = counted_sqrt
    try:
        result = kernel(u, dt, dx)
    finally:
        module.reference.pressure = pressure
        np.sqrt = sqrt
    return result, calls


def scalar_face(left, right, axis):
    """Literal five-component transcription of EulerCache.face, in binary64."""

    def physical(u):
        p = u[4] - (u[1] ** 2 + u[2] ** 2 + u[3] ** 2) / (2 * u[0])
        velocity = u[axis + 1] / u[0]
        result = np.array(
            [
                u[k] * velocity + (p if k == axis + 1 else 0) + (p * velocity if k == 4 else 0)
                for k in range(5)
            ]
        )
        return result, abs(velocity) + np.sqrt(2 * p / u[0])

    fl, sl = physical(left)
    fr, sr = physical(right)
    return (fl + fr - max(sl, sr) * (right - left)) / 2


def scalar_step(u, dt, dx):
    out = u.copy()
    shape = u.shape[:-1]
    for cell in np.ndindex(shape):
        for axis in range(3):
            nxt = list(cell)
            prev = list(cell)
            nxt[axis] = (nxt[axis] + 1) % shape[axis]
            prev[axis] = (prev[axis] - 1) % shape[axis]
            out[cell] -= (
                dt
                / dx
                * (
                    scalar_face(u[cell], u[tuple(nxt)], axis)
                    - scalar_face(u[tuple(prev)], u[cell], axis)
                )
            )
    return out


def validate_schedule(commands, n):
    ready = set()
    used = set()
    evals = 0
    uses = 0
    drops = 0
    for action, cell, axis in commands:
        if not 0 <= cell < n:
            return dict(legal=False, reason="out-of-range cell")
        if action == "eval":
            ready.add(cell)
            evals += 1
        elif action == "drop":
            ready.discard(cell)
            drops += 1
        elif action == "use":
            if cell not in ready or axis not in range(3):
                return dict(legal=False, reason="use without ready thermodynamics")
            used.add((axis, cell))
            uses += 1
        else:
            raise ValueError(action)
    return dict(legal=True, complete=len(used) == 3 * n, evaluations=evals, uses=uses, drops=drops)


def main():
    rows = []
    for n in [3, 8, 16]:
        u = module.state(n, 77 + n, "random")
        dt = module.timestep(u, 1 / n)
        baseline, bcounts = counts(module.reference.step, u, dt, 1 / n)
        cached, ccounts = counts(module.cached_step, u, dt, 1 / n)
        assert np.array_equal(baseline, cached)
        assert bcounts["pressure_cells"] == bcounts["sqrt_cells"] == 3 * n**3
        assert ccounts["pressure_cells"] == ccounts["sqrt_cells"] == n**3
        rows.append(dict(n=n, cells=n**3, reference=bcounts, cached=ccounts, bitwise_equal=True))
    u = module.state(3, 910, "random")
    vector = module.cached_step(u, 0.001, 1 / 3)
    scalar = scalar_step(u, 0.001, 1 / 3)
    gap = float(np.max(abs(vector - scalar)))
    assert gap < 1e-13
    old_pressure = module.reference.pressure(u)
    changed = u.copy()
    changed[0, 0, 0, 4] += 0.5
    true_result = module.reference.step(changed, 0.001, 1 / 3)
    original = module.reference.pressure
    module.reference.pressure = lambda _: old_pressure
    try:
        stale_result = module.cached_step(changed, 0.001, 1 / 3)
    finally:
        module.reference.pressure = original
    stale_gap = float(np.max(abs(true_result - stale_result)))
    assert stale_gap > 1e-6
    n = 7
    # Axis-major ordering matches NumPy; Lean's canonical witness is cell-major.
    # Both satisfy the same legal/complete contract and the same exact counts.
    baseline_schedule = [
        (action, i, a) for a in range(3) for i in range(n) for action in ["eval", "use"]
    ]
    cached_schedule = [("eval", i, None) for i in range(n)] + [
        ("use", i, a) for a in range(3) for i in range(n)
    ]
    b = validate_schedule(baseline_schedule, n)
    c = validate_schedule(cached_schedule, n)
    illegal = validate_schedule(cached_schedule[1:], n)
    assert b["legal"] and b["complete"] and b["evaluations"] == 3 * n
    assert c["legal"] and c["complete"] and c["evaluations"] == n
    assert not illegal["legal"]
    report = dict(
        actual_call_counts=rows,
        scalar_model_transcription_max_difference=gap,
        stale_pressure_negative_control_max_difference=stale_gap,
        schedules=dict(reference=b, cached=c, missing_eval_negative_control=illegal),
        source_sha256={
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in ["euler.py", "experiment.py", "instrument.py"]
        },
        scope=(
            "Empirical correspondence checks; not verified compilation or floating-point refinement"
        ),
    )
    Path("instrumentation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
