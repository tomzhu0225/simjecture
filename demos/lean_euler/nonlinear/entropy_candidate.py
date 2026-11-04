"""Gamma=2 entropy-conservative flux + LF dissipation with checked trial steps.

The float implementation tests admissibility and a finite-step entropy target.
These tests are not certified rounding-error bounds or continuum-error bounds.
The base flux is the existing Chandrashekar logarithmic-mean construction.
"""

from dataclasses import dataclass

import finite_volume as fv
import numpy as np


def logarithmic_mean(left, right):
    a, b = np.broadcast_arrays(np.asarray(left, dtype=float), np.asarray(right, dtype=float))
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)) or np.min(a) <= 0 or np.min(b) <= 0:
        raise ValueError("Logarithmic means require positive finite arguments")
    mean = a + 0.5 * (b - a)
    z = (0.5 * (b - a)) / mean
    q = z * z
    small, far = q < 1e-6, np.abs(z) >= 0.9
    regular = ~(small | far)
    series = 1 + q * (1 / 3 + q * (1 / 5 + q * (1 / 7 + q / 9)))
    denominator = np.arctanh(np.where(regular, z, 0.0))
    factor = np.divide(z, denominator, out=np.ones_like(z), where=regular)
    result = np.where(small, mean / series, mean * factor)
    np.divide(b - a, np.log(b) - np.log(a), out=result, where=far)
    if not np.all(np.isfinite(result)) or np.min(result) <= 0:
        raise ArithmeticError("Logarithmic mean lost finite positivity")
    return result


def state_fields(u):
    rho, p = u[..., 0], fv.pressure(u)
    if not np.all(np.isfinite(u)) or np.min(rho) <= 0 or np.min(p) <= 0:
        raise ValueError("State is not admissible")
    velocity = u[..., 1:4] / rho[..., None]
    beta = rho / (2 * p)
    return rho, p, velocity, beta


def entropy(u):
    rho, p, _, _ = state_fields(u)
    return -rho * (np.log(p) - 2 * np.log(rho))


def entropy_variables(u):
    rho, p, velocity, beta = state_fields(u)
    result = np.empty_like(u)
    result[..., 0] = 2 - (np.log(p) - 2 * np.log(rho)) - beta * np.sum(velocity**2, axis=-1)
    result[..., 1:4] = 2 * beta[..., None] * velocity
    result[..., 4] = -2 * beta
    return result


def _parameter_flux(rho_left, rho_right, beta_left, beta_right, velocity_left, velocity_right, d):
    velocity = 0.5 * (velocity_left + velocity_right)
    density_mean = logarithmic_mean(rho_left, rho_right)
    beta_mean = logarithmic_mean(beta_left, beta_right)
    pressure_mean = (rho_left + rho_right) / (2 * (beta_left + beta_right))
    mass = density_mean * velocity[..., d]
    momentum = mass[..., None] * velocity
    momentum[..., d] += pressure_mean
    speed_square_mean = 0.5 * np.sum(velocity_left**2 + velocity_right**2, axis=-1)
    result = np.empty((*mass.shape, 5))
    result[..., 0], result[..., 1:4] = mass, momentum
    result[..., 4] = mass * (1 / (2 * beta_mean) - 0.5 * speed_square_mean) + np.sum(
        velocity * momentum, axis=-1
    )
    return result


def entropy_conservative_flux(left, right, d):
    if d not in (0, 1, 2):
        raise ValueError("Use a spatial direction 0, 1, or 2")
    rl, _, vl, bl = state_fields(left)
    rr, _, vr, br = state_fields(right)
    return _parameter_flux(rl, rr, bl, br, vl, vr, d)


@dataclass
class _Prepared:
    increment: np.ndarray
    speeds: np.ndarray
    dissipation: float
    entropy_before: float


def _prepare(u):
    rho, p, velocity, beta = state_fields(u)
    speeds = np.max(np.abs(velocity) + np.sqrt(2 * p / rho)[..., None], axis=(0, 1, 2))
    gradient = entropy_variables(u)
    increment, dissipation = np.zeros_like(u), 0.0
    for d in range(3):
        jump = np.roll(u, -1, axis=d) - u
        face = (
            _parameter_flux(
                rho,
                np.roll(rho, -1, axis=d),
                beta,
                np.roll(beta, -1, axis=d),
                velocity,
                np.roll(velocity, -1, axis=d),
                d,
            )
            - 0.5 * speeds[d] * jump
        )
        increment -= face - np.roll(face, 1, axis=d)
        gradient_jump = np.roll(gradient, -1, axis=d) - gradient
        dissipation += 0.5 * speeds[d] * float(np.mean(np.sum(gradient_jump * jump, axis=-1)))
    if dissipation < 0 or not np.isfinite(dissipation):
        raise ArithmeticError("Computed dissipation is not finite and nonnegative")
    return _Prepared(increment, speeds, dissipation, float(entropy(u).mean()))


@dataclass
class StepResult:
    field: np.ndarray
    dt: float
    rejected: int
    entropy_before: float
    entropy_after: float
    entropy_margin: float
    predicted_drop: float
    min_density: float
    min_pressure: float


def _step_prepared(u, dx, proposal, prepared, max_halvings=60):
    """Internal only: prepared data must be fresh from this same immutable u."""
    if dx <= 0 or proposal <= 0 or not np.isfinite(dx + proposal):
        raise ValueError("Require positive finite spacing and timestep")
    dt = proposal
    for rejected in range(max_halvings + 1):
        ratio = dt / dx
        updated = u + ratio * prepared.increment
        try:
            rho, p, _, _ = state_fields(updated)
            after = float(entropy(updated).mean())
            predicted = 0.5 * ratio * prepared.dissipation
            target = prepared.entropy_before - predicted
            if after <= target:
                return StepResult(
                    updated,
                    dt,
                    rejected,
                    prepared.entropy_before,
                    after,
                    target - after,
                    predicted,
                    float(rho.min()),
                    float(p.min()),
                )
        except ValueError:
            pass
        dt *= 0.5
        if dt == 0:
            raise ArithmeticError("Timestep underflow during trial checks")
    raise ArithmeticError("Admissibility/entropy backtracking exhausted its limit")


def step(u, dx, proposal, max_halvings=60):
    return _step_prepared(u, dx, proposal, _prepare(u), max_halvings)


@dataclass
class Result:
    field: np.ndarray
    time: float
    steps: int
    rejected_steps: int
    trial_cell_updates: int
    face_evaluations: int
    history: list


def solve(n, amplitude, delta, final_time=0.25, cfl=0.3):
    if not 0 < cfl <= 1 or final_time <= 0:
        raise ValueError("Require 0 < CFL <= 1 and positive final time")
    u = fv.cell_averages(n, amplitude, delta)
    dx, time, history = 2 * np.pi / n, 0.0, []
    rejected_steps = 0
    while time < final_time:
        prepared = _prepare(u)
        proposal = min(final_time - time, cfl * dx / prepared.speeds.sum())
        result = _step_prepared(u, dx, proposal, prepared)
        if time + result.dt == time:
            raise ArithmeticError("Accepted timestep cannot advance floating-point time")
        u, time = result.field, time + result.dt
        rejected_steps += result.rejected
        history.append(
            dict(
                time=time,
                proposal=proposal,
                dt=result.dt,
                rejected=result.rejected,
                entropy=result.entropy_after,
                entropy_margin=result.entropy_margin,
                predicted_drop=result.predicted_drop,
                min_density=result.min_density,
                min_pressure=result.min_pressure,
            )
        )
    steps = len(history)
    return Result(
        u, time, steps, rejected_steps, (steps + rejected_steps) * n**3, 3 * steps * n**3, history
    )
