"""Reproducible local illustration; error samples are separate from Lean proof."""

import argparse
import hashlib
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from solver import (
    Reconstruction,
    demonstration_density,
    euler_flux,
    exact_state,
    flow,
    inverse_flow,
    modeled_work,
    solve,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started_utc = datetime.now(UTC).isoformat()
    rng = np.random.default_rng(20261101)
    material = rng.random((100_000, 3))
    # Include all cube corners and points just inside coarse grid interfaces.
    material = np.concatenate(
        [material, np.array(np.meshgrid([0.0, 1.0], [0.0, 1.0], [0.0, 1.0])).reshape(3, -1).T]
    )
    rows = []
    for eps in [0.1, 0.05, 0.025, 0.0125]:
        elapsed = []
        for _ in range(3):
            started = time.perf_counter()
            solution = solve(demonstration_density, 2.0, eps)
            elapsed.append(time.perf_counter() - started)
        errors, eval_seconds = [], []
        for t in [0.0, 0.25, 0.75, 1.0]:
            x = flow(t, material)
            started = time.perf_counter()
            uh = solution.evaluate(t, x)
            eval_seconds.append(time.perf_counter() - started)
            u = exact_state(demonstration_density, t, x)
            errors.append(float(np.max(np.abs(uh - u))))
        assert max(errors) <= solution.exact_real_error_bound + 1e-12
        rows.append(
            dict(
                epsilon=eps,
                n=solution.n,
                oracle_queries=solution.query_count,
                formal_ram_work=modeled_work(solution.n),
                density_array_bytes=solution.data.nbytes,
                exact_real_uniform_bound=solution.exact_real_error_bound,
                sampled_full_state_max_error_by_time=errors,
                build_seconds=elapsed,
                median_build_seconds=float(np.median(elapsed)),
                evaluate_100008_points_seconds=eval_seconds,
            )
        )
    x = flow(0.4, material[:512])
    dt = 1e-5
    residual = (
        exact_state(demonstration_density, 0.4 + dt, x)
        - exact_state(demonstration_density, 0.4 - dt, x)
    ) / (2 * dt)
    for d in range(3):
        shift = np.zeros(3)
        shift[d] = dt
        residual += (
            euler_flux(exact_state(demonstration_density, 0.4, x + shift), d)
            - euler_flux(exact_state(demonstration_density, 0.4, x - shift), d)
        ) / (2 * dt)
    # Explicit C1 quartic bump illustrating the indistinguishability mechanism.
    n = 8
    eps = 2 / (48 * n)
    ijk = np.indices((n, n, n)).reshape(3, -1).T
    hole = np.array([3, 4, 2])
    queries = (ijk[np.any(ijk != hole, axis=1)] + 0.5) / n
    center = (hole + 0.5) / n

    def bump(a):
        s = n * a - hole
        return np.prod(np.where((s > 0) & (s < 1), 16 * s * s * (1 - s) * (1 - s), 0), axis=-1)

    plus = 1.5 + 2 * eps * bump(queries)
    minus = 1.5 - 2 * eps * bump(queries)
    assert np.array_equal(plus, minus)
    assert np.all(plus == 1.5)
    hard = dict(
        n=n,
        queries=len(queries),
        available_cells=n**3,
        epsilon=eps,
        lipschitz_upper_bound=48 * eps * n,
        all_query_answers_equal=True,
        unqueried_center=center.tolist(),
        plus_at_center=float(1.5 + 2 * eps * bump(center)),
        minus_at_center=float(1.5 - 2 * eps * bump(center)),
        separation_at_center=4 * eps,
        note=(
            "Numerical illustration uses a quartic bump; the formal proof uses "
            "Mathlib's smooth bump and an existential fixed Lipschitz constant."
        ),
    )

    def steep_density(a):
        return 1.5 + 0.49 * np.tanh((2 / 0.49) * (a[..., 0] - 0.45))

    good = solve(steep_density, 2.0, 0.05)
    nbad = 10
    bad_centers = (np.arange(nbad) + 0.5) / nbad
    bad_points = np.stack(
        np.meshgrid(bad_centers, bad_centers, bad_centers, indexing="ij"), axis=-1
    )
    bad = Reconstruction(steep_density(bad_points), 2.0, 0.05, nbad**3)
    witness = flow(0.75, np.array([[0.5 - 1e-10, 1.0, 1.0]]))
    truth = exact_state(steep_density, 0.75, witness)
    good_error = float(np.max(np.abs(good.evaluate(0.75, witness) - truth)))
    bad_error = float(np.max(np.abs(bad.evaluate(0.75, witness) - truth)))
    assert good_error <= 0.05 < bad_error
    resolution_control = dict(
        epsilon=0.05,
        lipschitz=2.0,
        correct_n=good.n,
        altered_n=nbad,
        witness_material=[0.5 - 1e-10, 1.0, 1.0],
        correct_error=good_error,
        altered_error=bad_error,
        density="1.5 + 0.49*tanh((2/0.49)*(X-0.45)); global range [1.01,1.99], Lipschitz <= 2",
    )
    here = Path(__file__).resolve().parent
    sources = {
        name: hashlib.sha256((here / name).read_bytes()).hexdigest()
        for name in ["solver.py", "run_experiment.py", "CONTRACT.json"]
    }
    result = dict(
        started_utc=started_utc,
        sources=sources,
        resolution_negative_control=resolution_control,
        schema_version="0.1.0",
        scope=(
            "Floating-point illustration, not executable verification or a general Euler benchmark"
        ),
        platform=platform.platform(),
        python=platform.python_version(),
        numpy=np.__version__,
        seed=20261101,
        lipschitz=2.0,
        times=[0.0, 0.25, 0.75, 1.0],
        test_points_per_time=len(material),
        flow_inverse_sample_max_error=float(
            np.max(np.abs(inverse_flow(0.75, flow(0.75, material)) - material))
        ),
        finite_difference_euler_residual_max=float(np.max(np.abs(residual))),
        finite_difference_step=dt,
        rows=rows,
        hard_pair=hard,
        limitations=[
            (
                "The global smoothness/Lipschitz class is an analytic input "
                "contract, not inferred from samples."
            ),
            (
                "Lean checks exact-real mathematics and the stated RAM model, not"
                " NumPy or IEEE rounding."
            ),
            (
                "Wall times are descriptive; no speed comparison to a "
                "general-purpose Euler solver is made."
            ),
        ],
    )
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    np.savez_compressed(
        args.output / "visual_data.npz",
        material=material[:12000],
        eulerian=flow(0.75, material[:12000]),
        density=demonstration_density(material[:12000]),
    )
    print(
        json.dumps(
            {"results": str(args.output / "results.json"), "rows": rows, "hard_pair": hard},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
