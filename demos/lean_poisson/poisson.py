"""Two-sweep 1D Dirichlet solve, exact checks, and bounded local measurements."""

import json
import math
import platform
import random
import statistics
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.linalg import solve_banded


def solve(rhs, *, counted=False):
    """Solve 2*u[i]-u[i-1]-u[i+1]=rhs[i], with zero Dirichlet boundaries.

    Fraction inputs use exact arithmetic; floats exercise a separate empirical
    implementation. The counters mirror the Lean ghost-trace model, not CPU work.
    """
    n = 0
    weighted = 0
    counts = dict(control=1, read=0, increment=0, cast=0, mul=0, add=0, sub=0, div=0, emit=0)
    for value in reversed(rhs):
        n += 1
        weighted += n * value
        if counted:
            for key in ["control", "read", "increment", "cast", "mul", "add"]:
                counts[key] += 1
    delta = weighted / (n + 1)
    if counted:
        for key in ["increment", "cast", "div"]:
            counts[key] += 1
    left = 0
    solution = []
    for value in rhs:
        current = left + delta
        delta -= value
        solution.append(current)
        left = current
        if counted:
            for key in ["control", "read", "add", "sub", "emit"]:
                counts[key] += 1
    boundary = left + delta
    if counted:
        counts["control"] += 1
        counts["add"] += 1
        return solution, boundary, counts
    return solution


def residual(rhs, u):
    extended = [0, *u, 0]
    return [
        2 * extended[i + 1] - extended[i] - extended[i + 2] - value for i, value in enumerate(rhs)
    ]


def thomas_exact(rhs):
    """Independent elimination/back-substitution reference over rational inputs."""
    if not rhs:
        return []
    upper = []
    reduced = []
    for i, value in enumerate(rhs):
        pivot = Fraction(2) if i == 0 else Fraction(2) + upper[-1]
        upper.append(-1 / pivot)
        reduced.append((value if i == 0 else value + reduced[-1]) / pivot)
    result = [Fraction(0)] * len(rhs)
    result[-1] = reduced[-1]
    for i in range(len(rhs) - 2, -1, -1):
        result[i] = reduced[i] - upper[i] * result[i + 1]
    return result


def exact_checks():
    rng = random.Random(20261101)
    cases = [[], [Fraction(0)], [Fraction(1)], [Fraction(-3, 7)]]
    for n in [2, 3, 4, 7, 16, 31, 64]:
        cases += [
            [Fraction(rng.randint(-20, 20), rng.randint(1, 11)) for _ in range(n)] for _ in range(4)
        ]
        cases += [[Fraction(int(i == n // 2)) for i in range(n)]]
    records = []
    for rhs in cases:
        u, boundary, counts = solve(rhs, counted=True)
        assert boundary == 0 and all(r == 0 for r in residual(rhs, u))
        assert u == thomas_exact(rhs)
        assert sum(counts.values()) == 11 * len(rhs) + 6
        assert counts["emit"] == len(rhs)
        records.append(
            dict(
                n=len(rhs),
                rhs=[str(x) for x in rhs],
                solution=[str(x) for x in u],
                right_boundary=str(boundary),
                counts=counts,
            )
        )
    # A wrong normalization passes many interior equations but violates the boundary problem.
    rhs = [Fraction(1)]
    wrong = [Fraction(1)]  # w/N, instead of w/(N+1), for N=1.
    failure = residual(rhs, wrong)
    assert failure == [Fraction(1)]
    return dict(
        cases=records,
        all_exact=True,
        independent_reference="rational Thomas elimination",
        negative_control=dict(
            rhs=["1"], wrong_solution=["1"], residual=["1"], cause="normalize by N instead of N+1"
        ),
    )


def measure(n):
    h = 1 / (n + 1)
    x = np.arange(1, n + 1) * h
    # Analytic Poisson solution sin(pi*x); exact discrete sine solution differs
    # by the known finite-difference eigenvalue, without a subtraction-based RHS.
    rhs = h * h * math.pi**2 * np.sin(math.pi * x)
    exact_discrete = rhs / (4 * math.sin(math.pi * h / 2) ** 2)
    values = rhs.tolist()
    band = np.zeros((3, n))
    band[0, 1:] = -1
    band[1, :] = 2
    band[2, :-1] = -1
    reference = solve_banded((1, 1), band, rhs)
    solve(values)  # warm-up; excluded from measurements
    trials = []
    u = None
    for _ in range(7):
        started = time.perf_counter()
        u = solve(values)
        trials.append(time.perf_counter() - started)
    arr = np.asarray(u)
    r = np.asarray(residual(values, u))
    norm = 4 * np.max(abs(arr)) + np.max(abs(rhs))
    backward_error = float(np.max(abs(r)) / norm)
    error = float(np.max(abs(arr - exact_discrete)))
    assert np.all(np.isfinite(arr))
    # Numerical acceptance for these smooth cases only; no universal stability theorem.
    assert error < 1e-7
    return dict(
        n=n,
        work_units=11 * n + 6,
        lower_bound=n,
        trials_seconds=trials,
        median_seconds=statistics.median(trials),
        seconds_per_unknown=statistics.median(trials) / n,
        max_residual=float(np.max(abs(r))),
        normalized_backward_error=backward_error,
        backward_error_target=5e-15,
        meets_backward_error_target=bool(backward_error < 5e-15),
        max_error_vs_exact_discrete=error,
        max_difference_vs_scipy=float(np.max(abs(arr - reference))),
        max_error_vs_continuum=float(np.max(abs(arr - np.sin(math.pi * x)))),
    )


def main():
    results = dict(
        contract="Exact 1D discrete Dirichlet solve in a unit-cost scalar trace model",
        exact=exact_checks(),
        timings=[measure(n) for n in [64, 256, 1024, 4096, 16384, 65536]],
        environment=dict(
            python=platform.python_version(),
            numpy=np.__version__,
            platform=platform.platform(),
            precision="binary64 for timing; Fraction for exact checks",
        ),
        limitations=[
            "Rational bit complexity is not unit cost",
            "Floating-point correspondence is empirical",
            "No fastest-constant, GPU, multidimensional Poisson, or Euler optimality claim",
        ],
    )
    Path("measurements.json").write_text(json.dumps(results, indent=2) + "\n")
    print(
        json.dumps(
            {"exact_cases": len(results["exact"]["cases"]), "timings": results["timings"]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
