"""Analytic controls for the demonstration's MHD-to-kinetic mapping.

These are model-free transfer tests; they do not qualify a reconnection patch.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.constants import e

pytest.importorskip("h5py")
ROOT = Path(__file__).parents[1] / "demos/flash_warpx_kinetic_patch/guided"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXTRACT = load("extract_flash")
PREPARE = load("prepare_patch")


def analytic_state(tmp_path):
    n = 64
    x = -0.5 + (np.arange(n) + 0.5) / n
    xx, zz = np.meshgrid(x, x)
    ay = xx**2 + 2 * zz**2 + 0.3 * xx * zz
    path = tmp_path / "state.npz"
    np.savez_compressed(
        path,
        x=x,
        z=x,
        ay=ay,
        bx=-4 * zz - 0.3 * xx,
        bz=2 * xx + 0.3 * zz,
        rho=np.ones_like(xx) * 1.2,
        pressure=np.ones_like(xx) * 3,
        ux=np.ones_like(xx) * 0.2,
        uz=np.ones_like(xx) * -0.1,
    )
    path.with_suffix(".json").write_text(
        json.dumps(
            {
                "handoff_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "source_sha256": "analytic-fixture",
                "source_time_code": 0.25,
                "eta_code": 0.001,
                "potential_relative_edge_residual": 0.0,
            }
        )
    )
    return path


def arguments(state, output):
    return argparse.Namespace(
        state=state,
        output=output,
        center_x=0.0,
        center_z=0.0,
        half_width=0.2,
        nx=32,
        nz=48,
        mass_ratio=25,
        density=1e24,
        skin_depth_code=0.02,
        va_over_c=0.01,
        temperature_ratio=1.0,
        electric="ideal",
    )


def test_potential_recovers_asymmetric_quadratic_with_current():
    nx, nz = 32, 48
    x = np.linspace(-0.7, 0.9, nx)
    z = np.linspace(-0.4, 0.6, nz)
    xx, zz = np.meshgrid(x, z)
    expected = xx**2 + 2 * zz**2 + 0.3 * xx * zz
    ay, residual = EXTRACT.potential(
        -4 * zz - 0.3 * xx, 2 * xx + 0.3 * zz, x[1] - x[0], z[1] - z[0]
    )
    np.testing.assert_allclose(ay, expected - expected.mean(), rtol=0, atol=3e-13)
    assert residual < 1e-12


def test_mapping_preserves_pressure_mass_flow_current_sign_and_divergence(tmp_path):
    args = arguments(analytic_state(tmp_path), tmp_path / "patch.npz")
    meta = PREPARE.prepare(args)
    with np.load(args.output) as d:
        scales = meta["scales"]
        mi = scales["ion_mass_kg"]
        me = scales["electron_mass_kg"]
        np.testing.assert_allclose(d["n"] * (d["ti"] + d["te"]), d["p"], rtol=1e-13)
        bulk = (mi * d["ui"] + me * d["ue"]) / (mi + me)
        np.testing.assert_allclose(bulk[:, :, 0], 0.2 * scales["velocity_m_s"], rtol=1e-13)
        np.testing.assert_allclose(bulk[:, :, 2], -0.1 * scales["velocity_m_s"], rtol=1e-13)
        np.testing.assert_allclose(bulk[:, :, 1], 0.0, atol=1e-10)
        np.testing.assert_allclose(
            e * d["n"] * (d["ui"][:, :, 1] - d["ue"][:, :, 1]), d["jy"], rtol=1e-13
        )
        assert np.max(d["jy"]) < 0, "Right-handed mapping requires Jy=-Jz_FLASH"
        dx, dz = meta["cell_size_m"]
        div = np.diff(d["bx"], axis=1) / dx + np.diff(d["bz"], axis=0) / dz
        assert np.max(np.abs(div)) * min(dx, dz) / scales["magnetic_T"] < 1e-13
    assert meta["initial_discrete_divb_scaled"] < 1e-13


def test_changed_handoff_is_rejected_before_producing_patch(tmp_path):
    state = analytic_state(tmp_path)
    with state.open("ab") as f:
        f.write(b"changed")
    args = arguments(state, tmp_path / "patch.npz")
    with pytest.raises(ValueError, match="hash"):
        PREPARE.prepare(args)
    assert not args.output.exists()
