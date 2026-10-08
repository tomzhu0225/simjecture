"""Prepare a SI, divergence-free Yee-grid patch from an exported FLASH state.

The dimensional scale and collisionless realization are operator/model choices,
not information that can be inferred from a normalized MHD snapshot alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.constants import c, e, epsilon_0, m_e, mu_0
from scipy.interpolate import RectBivariateSpline


def prepare(a):
    metadata = json.loads(a.state.with_suffix(".json").read_text())
    if hashlib.sha256(a.state.read_bytes()).hexdigest() != metadata["handoff_sha256"]:
        raise ValueError("FLASH export hash does not match its handoff manifest")
    with np.load(a.state, allow_pickle=False) as f:
        data = {k: f[k].copy() for k in f.files}
    if a.output.exists() or a.output.with_suffix(".json").exists():
        raise FileExistsError("Use a new prepared-patch output path")
    x, z = data["x"], data["z"]
    bounds = np.array(
        [
            [a.center_x - a.half_width, a.center_x + a.half_width],
            [a.center_z - a.half_width, a.center_z + a.half_width],
        ]
    )
    if not (
        x[2] < bounds[0, 0] < bounds[0, 1] < x[-3] and z[2] < bounds[1, 0] < bounds[1, 1] < z[-3]
    ):
        raise ValueError("Patch needs at least two source-grid cells of interpolation clearance")
    if (
        min(a.nx, a.nz) < 8
        or min(a.mass_ratio, a.density, a.skin_depth_code, a.temperature_ratio) <= 0
    ):
        raise ValueError("Require positive physical scales and at least eight cells per axis")
    if not 0 < a.va_over_c < 0.1:
        raise ValueError("Use an explicit nonrelativistic Alfven-speed scale")
    mi, me = a.mass_ratio * m_e, m_e
    n0, v0 = a.density, a.va_over_c * c
    rho0 = n0 * (mi + me)
    b0 = v0 * np.sqrt(mu_0 * rho0)
    di = np.sqrt(mi / (mu_0 * n0 * e**2))
    l0 = di / a.skin_depth_code
    xn = np.linspace(*bounds[0], a.nx + 1)
    zn = np.linspace(*bounds[1], a.nz + 1)
    xc, zc = (xn[:-1] + xn[1:]) / 2, (zn[:-1] + zn[1:]) / 2
    dx, dz = (xn[1] - xn[0]) * l0, (zn[1] - zn[0]) * l0
    splines = {k: RectBivariateSpline(z, x, v, kx=3, ky=3) for k, v in data.items() if v.ndim == 2}
    ay = splines["ay"](zn, xn) * b0 * l0
    bx = -np.diff(ay, axis=0) / dz
    bz = np.diff(ay, axis=1) / dx
    div = np.diff(bx, axis=1) / dx + np.diff(bz, axis=0) / dz

    def sample(name):
        return splines[name](zc, xc)

    density = sample("rho") * n0
    pressure = sample("pressure") * rho0 * v0 * v0
    if density.min() <= 0 or pressure.min() <= 0:
        raise ValueError("Cubic transfer produced nonpositive density/pressure")
    jy = -(splines["ay"](zc, xc, dx=2) + splines["ay"](zc, xc, dy=2)) * b0 / (mu_0 * l0)
    bulk = np.stack([sample("ux") * v0, np.zeros_like(density), sample("uz") * v0], axis=-1)
    relative_drift = np.stack([np.zeros_like(jy), jy / (e * density), np.zeros_like(jy)], axis=-1)
    ui = bulk + me / (mi + me) * relative_drift
    ue = bulk - mi / (mi + me) * relative_drift
    te = pressure / (density * (1 + a.temperature_ratio))
    ti = a.temperature_ratio * te
    bx_node = -splines["ay"](zn, xn, dx=1) * b0
    bz_node = splines["ay"](zn, xn, dy=1) * b0
    ey = v0 * (splines["ux"](zn, xn) * bz_node - splines["uz"](zn, xn) * bx_node)
    if a.electric == "resistive":
        jcode = -(splines["ay"](zn, xn, dx=2) + splines["ay"](zn, xn, dy=2))
        ey += metadata["eta_code"] * jcode * b0 * v0
    a.output.parent.mkdir(parents=True, exist_ok=True)
    # All arrays here are (z,x[,component]); the WarpX launcher transposes them.
    np.savez_compressed(
        a.output,
        bx=bx,
        bz=bz,
        ey=ey,
        n=density,
        p=pressure,
        ui=ui,
        ue=ue,
        ti=ti,
        te=te,
        jy=jy,
        x=xc * l0,
        z=zc * l0,
    )
    bcenter = np.sqrt(((bx[:, :-1] + bx[:, 1:]) / 2) ** 2 + ((bz[:-1] + bz[1:]) / 2) ** 2)
    meta = {
        "schema_version": 1,
        "source_state_sha256": hashlib.sha256(a.state.read_bytes()).hexdigest(),
        "source_flash_sha256": metadata["source_sha256"],
        "source_time_code": metadata["source_time_code"],
        "patch_sha256": hashlib.sha256(a.output.read_bytes()).hexdigest(),
        "shape_zx": [a.nz, a.nx],
        "bounds_xz_m": (bounds * l0).tolist(),
        "cell_size_m": [dx, dz],
        "scales": {
            "length_m": l0,
            "velocity_m_s": v0,
            "magnetic_T": b0,
            "density_m3": n0,
            "mass_density_kg_m3": rho0,
            "ion_mass_kg": mi,
            "electron_mass_kg": me,
            "ion_skin_depth_m": di,
            "ion_skin_depth_code": a.skin_depth_code,
            "omega_ci_reference_s1": e * b0 / mi,
            "omega_pe_reference_s1": np.sqrt(n0 * e**2 / (epsilon_0 * me)),
        },
        "temperature_ratio_i_e": a.temperature_ratio,
        "electric_policy": a.electric,
        "physics": (
            "Collisionless, fully kinetic electron-ion continuation; "
            "no scalar MHD resistivity is evolved in PIC."
        ),
        "mapping": (
            "Right-handed FLASH (x,y,z) to WarpX (X,Y,Z)=(x,-z,y); "
            "n=rho_code*n0; p=p_code*rho0*v0^2; total mass rho=n*(mi+me)."
        ),
        "initial_discrete_divb_scaled": float(
            np.max(np.abs(div)) * min(dx, dz) / max(bcenter.max(), 1e-300)
        ),
        "maximum_drift_over_c": float(
            max(np.linalg.norm(ui, axis=-1).max(), np.linalg.norm(ue, axis=-1).max()) / c
        ),
        "maximum_electron_thermal_speed_over_c": float(np.sqrt(te.max() / me) / c),
        "source_potential_residual": metadata["potential_relative_edge_residual"],
        "scope": (
            "Prepared local initial-value problem only. Patch boundaries, relaxation, "
            "collisionless closure and physical scale need scientific review."
        ),
    }
    a.output.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--nx", type=int, default=64)
    p.add_argument("--nz", type=int, default=64)
    p.add_argument("--center-x", type=float, default=0.0)
    p.add_argument("--center-z", type=float, default=0.0)
    p.add_argument("--half-width", type=float, default=0.12)
    p.add_argument("--skin-depth-code", type=float, default=0.02)
    p.add_argument("--density", type=float, default=1e24)
    p.add_argument("--mass-ratio", type=float, default=25)
    p.add_argument("--va-over-c", type=float, default=0.01)
    p.add_argument("--temperature-ratio", type=float, default=1.0)
    p.add_argument("--electric", choices=["ideal", "resistive"], default="ideal")
    print(json.dumps(prepare(p.parse_args()), indent=2))
