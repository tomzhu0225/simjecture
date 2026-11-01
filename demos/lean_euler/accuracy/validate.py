"""Independent quadrature, work instrumentation, and admission negative controls."""

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("accuracy_study", "study.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def main():
    nodes, weights = np.polynomial.legendre.leggauss(8)
    quad_errors = []
    center_errors = []
    for n, cell, t in [(4, (1, 2, 0), 0.017), (8, (2, 1, 3), 0.05), (16, (5, 7, 11), 0.031)]:
        axes = [(i + 0.5 + 0.5 * nodes) / n for i in cell]
        phase = axes[0][:, None, None] + axes[1][None, :, None] + axes[2][None, None, :] - 0.6 * t
        density = 1 + 0.1 * np.sin(2 * np.pi * phase)
        tensor = weights[:, None, None] * weights[None, :, None] * weights[None, None, :] / 8
        integral = float(np.sum(tensor * density))
        analytic = float(study.exact_state(n, t)[cell][0])
        quad_errors.append(abs(integral - analytic))
        center = 1 + 0.1 * np.sin(2 * np.pi * (sum((i + 0.5) / n for i in cell) - 0.6 * t))
        center_errors.append(abs(center - analytic))
    assert max(quad_errors) < 1e-13
    assert max(center_errors) > 1e-4
    counts = []
    solutions = {}
    for method in ["reference", "cached", "fused", "muscl_rk2"]:
        original = study.reference.pressure
        observed = 0

        def counted(u, gamma=2, original=original):
            nonlocal observed
            observed += int(np.prod(u.shape[:-1]))
            return original(u, gamma)

        study.reference.pressure = counted
        try:
            u, row = study.solve(8, method, 0.05, 0.3)
        finally:
            study.reference.pressure = original
        assert observed == row["eos_cell_evaluations"]
        study.assess(u, row, 0.05)
        solutions[method] = u
        counts.append(
            dict(
                method=method,
                observed_eos_cells=observed,
                reported_eos_cells=row["eos_cell_evaluations"],
                density_l1=row["density_l1"],
            )
        )
    assert np.array_equal(solutions["reference"], solutions["cached"])
    assert np.array_equal(solutions["reference"], solutions["fused"])
    coarse = next(r for r in counts if r["method"] == "reference")
    assert coarse["density_l1"] > 0.02
    assert counts[-1]["density_l1"] < coarse["density_l1"]
    wrong = dict(n=8, final_time=0.0)
    try:
        study.assess(study.exact_state(8, 0), wrong, 0.05)
    except ValueError:
        wrong_time_rejected = True
    else:
        raise AssertionError("A zero-duration solve was admitted")
    report = dict(
        quadrature_max_error=max(quad_errors),
        point_sample_vs_cell_average_max=max(center_errors),
        counts=counts,
        coarse_first_order_rejected_for_epsilon_002=True,
        wrong_final_time_rejected=wrong_time_rejected,
        scope="Independent numerical checks; quadrature is not a formal integration proof",
        source_sha256={
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in ["study.py", "validate.py", "euler.py", "experiment.py"]
        },
    )
    Path("validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
