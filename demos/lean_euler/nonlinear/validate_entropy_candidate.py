"""Independent flux diagnostics and nonlinear runs for the alternative candidate."""

import argparse
import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path

import entropy_candidate as ec
import finite_volume as fv
import numpy as np


def conserved(rho, p, velocity):
    u = np.empty((*rho.shape, 5))
    u[..., 0], u[..., 1:4] = rho, rho[..., None] * velocity
    u[..., 4] = p + rho * np.sum(velocity**2, axis=-1) / 2
    return u


def complex_step_gradient(u):
    """Independent differentiation of the actual entropy expression."""
    result = np.empty_like(u)
    for j in range(5):
        z = u.astype(complex)
        z[..., j] += 1e-30j
        rho = z[..., 0]
        p = z[..., 4] - np.sum(z[..., 1:4] ** 2, axis=-1) / (2 * rho)
        value = -rho * (np.log(p) - 2 * np.log(rho))
        result[..., j] = value.imag / 1e-30
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    mean_error = 0.0
    for left, right in [(1.0, 1.0), (1.0, 1.0 + 1e-12), (1e-8, 1e8), (1e-300, 1e300)]:
        with localcontext() as ctx:
            ctx.prec = 70
            a, b = Decimal.from_float(left), Decimal.from_float(right)
            reference = float(a if a == b else (b - a) / (b.ln() - a.ln()))
        observed = float(ec.logarithmic_mean(left, right))
        mean_error = max(mean_error, abs(observed / reference - 1))
    assert mean_error < 2e-14

    rng = np.random.default_rng(20261104)
    rho = 10 ** rng.uniform(-2, 1, (2, 1024))
    pressure = 10 ** rng.uniform(-2, 1, (2, 1024))
    velocity = rng.uniform(-3, 3, (2, 1024, 3))
    left, right = conserved(rho, pressure, velocity)
    gl, gr = complex_step_gradient(left), complex_step_gradient(right)
    gradient_error = max(
        float(np.max(np.abs(ec.entropy_variables(state) - reference) / (1 + np.abs(reference))))
        for state, reference in [(left, gl), (right, gr)]
    )
    jump_error, consistency_error, symmetry_error = 0.0, 0.0, 0.0
    for d in range(3):
        flux = ec.entropy_conservative_flux(left, right, d)
        terms = (gr - gl) * flux
        jump = right[..., d + 1] - left[..., d + 1]
        residual = np.sum(terms, axis=-1) - jump
        scale = 1 + np.sum(np.abs(terms), axis=-1) + np.abs(jump)
        jump_error = max(jump_error, float(np.max(np.abs(residual) / scale)))
        symmetric = ec.entropy_conservative_flux(right, left, d)
        symmetry_error = max(
            symmetry_error, float(np.max(np.abs(flux - symmetric) / (1 + np.abs(flux))))
        )
        p = fv.pressure(left)
        v = left[..., 1:4] / left[..., 0, None]
        physical = fv.physical_flux(left, p, v, d)
        diagonal = ec.entropy_conservative_flux(left, left, d)
        consistency_error = max(
            consistency_error, float(np.max(np.abs(diagonal - physical) / (1 + np.abs(physical))))
        )
    assert gradient_error < 1e-10
    assert jump_error < 1e-10
    assert consistency_error < 2e-12
    assert symmetry_error < 2e-12

    initial = fv.cell_averages(8, 1.0, 0.05)
    dx = 2 * np.pi / 8
    prepared = ec._prepare(initial)
    identity_error = abs(
        float(np.mean(np.sum(complex_step_gradient(initial) * prepared.increment, axis=-1)))
        + prepared.dissipation
    )
    assert identity_error < 1e-11
    proposal = 10 * dx / prepared.speeds.sum()
    backtrack = ec.step(initial, dx, proposal)
    assert backtrack.rejected > 0 and backtrack.entropy_margin >= 0
    assert backtrack.min_density > 0 and backtrack.min_pressure > 0

    constant = np.broadcast_to(np.array([1.0, 0.2, -0.3, 0.4, 1.5]), (4, 4, 4, 5)).copy()
    constant_prepared = ec._prepare(constant)
    constant_step = ec.step(constant, dx, 100.0)
    assert constant_prepared.dissipation == 0
    assert np.array_equal(constant_step.field, constant)
    assert constant_step.rejected == 0

    rows = []
    for amplitude, delta in [(0.5, -0.05), (0.75, 0), (1.0, 0.05)]:
        for n in [16, 32, 64]:
            initial = fv.cell_averages(n, amplitude, delta)
            result = ec.solve(n, amplitude, delta)
            drift = float(np.max(np.abs(result.field.mean((0, 1, 2)) - initial.mean((0, 1, 2)))))
            assert drift < 1e-11
            row = dict(
                n=n,
                A=amplitude,
                delta=delta,
                final_time=result.time,
                steps=result.steps,
                rejected_steps=result.rejected_steps,
                trial_cell_updates=result.trial_cell_updates,
                face_evaluations=result.face_evaluations,
                max_halvings=max(x["rejected"] for x in result.history),
                minimum_entropy_margin=min(x["entropy_margin"] for x in result.history),
                min_density=min(x["min_density"] for x in result.history),
                min_pressure=min(x["min_pressure"] for x in result.history),
                entropy_initial=float(ec.entropy(initial).mean()),
                entropy_final=float(ec.entropy(result.field).mean()),
                conservation_error=drift,
                vertical_velocity_max=float(
                    np.max(np.abs(result.field[..., 3] / result.field[..., 0]))
                ),
            )
            rows.append(row)
            print(json.dumps(row), flush=True)
    here = Path(__file__).resolve().parent
    report = dict(
        scope=(
            "Existing entropy-conservative flux plus LF dissipation, with floating-point "
            "admissibility/entropy trial checks. Flux identities and successful trajectories "
            "do not establish continuum accuracy, certified rounding error or work optimality. "
            "Counts are coarse execution diagnostics, not a proved complete scalar work trace."
        ),
        logmean_high_precision_max_relative_error=mean_error,
        entropy_gradient_complex_step_max_scaled_error=gradient_error,
        tadmor_identity_max_scaled_error=jump_error,
        diagonal_flux_max_scaled_error=consistency_error,
        symmetric_flux_max_scaled_error=symmetry_error,
        periodic_entropy_pairing_error=identity_error,
        constant_state_control=dict(
            dissipation=constant_prepared.dissipation,
            state_max_error=float(np.max(np.abs(constant_step.field - constant))),
            rejected=constant_step.rejected,
        ),
        excessive_proposal_control=dict(
            proposal=float(proposal),
            accepted_dt=backtrack.dt,
            rejected=backtrack.rejected,
            entropy_margin=backtrack.entropy_margin,
            min_density=backtrack.min_density,
            min_pressure=backtrack.min_pressure,
        ),
        rows=rows,
        sources={
            name: hashlib.sha256((here / name).read_bytes()).hexdigest()
            for name in [
                "entropy_candidate.py",
                "validate_entropy_candidate.py",
                "finite_volume.py",
                "contract.json",
            ]
        },
    )
    (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
