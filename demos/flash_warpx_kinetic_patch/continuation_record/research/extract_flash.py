"""Export a uniform 2D FLASH state and a fitted flux potential for kinetic follow-up.

This is a one-way data-transfer helper, not a two-way MHD/PIC coupler. It preserves
code units; the kinetic launcher must supply an explicit dimensional mapping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
from scipy.fft import dctn, idctn


def potential(bx, bz, dx, dz):
    """Least-squares Ay from edge-averaged Bz=dAy/dx and Bx=-dAy/dz.

    The graph-gradient normal equation uses natural boundaries and a fixed zero
    mean. A DCT diagonalizes its Neumann Laplacian on the uniform cell-center grid.
    """
    nz, nx = bx.shape
    gx = 0.5 * (bz[:, 1:] + bz[:, :-1])
    gz = -0.5 * (bx[1:, :] + bx[:-1, :])
    rhs = np.zeros_like(bx)
    rhs[:, :-1] -= gx / dx
    rhs[:, 1:] += gx / dx
    rhs[:-1, :] -= gz / dz
    rhs[1:, :] += gz / dz
    eigen = (4 * np.sin(np.pi * np.arange(nx) / (2 * nx)) ** 2 / dx**2)[None, :]
    eigen = eigen + (4 * np.sin(np.pi * np.arange(nz) / (2 * nz)) ** 2 / dz**2)[:, None]
    eigen[0, 0] = 1.0
    modes = dctn(rhs, type=2, norm="ortho") / eigen
    modes[0, 0] = 0.0
    ay = idctn(modes, type=2, norm="ortho")
    residual = np.sqrt(
        np.mean((np.diff(ay, axis=1) / dx - gx) ** 2)
        + np.mean((np.diff(ay, axis=0) / dz - gz) ** 2)
    )
    scale = np.sqrt(np.mean(gx**2) + np.mean(gz**2))
    return ay, float(residual / max(scale, np.finfo(float).tiny))


def named(dataset):
    return {row["name"].decode().strip(): row["value"].item() for row in dataset[()]}


def export(source: Path, output: Path):
    with h5py.File(source) as f:
        bounds = f["bounding box"][:].astype(float)
        strings = {
            row["name"].decode().strip().lower(): row["value"].decode().strip().lower()
            for row in f["string runtime parameters"]
        }
        if strings.get("unitsystem") != "none" or strings.get("geometry") != "cartesian":
            raise ValueError("This handoff requires the normalized Cartesian FLASH application")
        if f["dens"].shape[1] != 1:
            raise ValueError("This handoff requires a 2D FLASH state")
        # Fail explicitly on AMR/multiple blocks. A production extension needs a
        # checked covering-grid reconstruction, not a silent choice of block 0.
        assert bounds.shape[0] == 1, "Only a uniform, single-output-block FLASH file is supported"
        state = {
            name: f[key][0, 0].astype(float)
            for name, key in {
                "rho": "dens",
                "pressure": "pres",
                "ux": "velx",
                "uz": "vely",
                "bx": "magx",
                "bz": "magy",
            }.items()
        }
        nz, nx = state["rho"].shape
        xmin, xmax = bounds[0, 0]
        zmin, zmax = bounds[0, 1]
        dx, dz = (xmax - xmin) / nx, (zmax - zmin) / nz
        x = xmin + (np.arange(nx) + 0.5) * dx
        z = zmin + (np.arange(nz) + 0.5) * dz
        time_code = float(named(f["real scalars"])["time"])
        params = named(f["real runtime parameters"])
    assert all(np.isfinite(v).all() for v in state.values())
    assert state["rho"].min() > 0 and state["pressure"].min() > 0
    ay, residual = potential(state["bx"], state["bz"], dx, dz)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.with_suffix(".json").exists():
        raise FileExistsError("Use a new handoff output path")
    np.savez_compressed(output, x=x, z=z, ay=ay, **state)
    manifest = {
        "schema_version": 1,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_name": source.name,
        "source_time_code": time_code,
        "flash_shape_zx": [nz, nx],
        "cell_size_code": [dx, dz],
        "bounds_xz_code": [[xmin, xmax], [zmin, zmax]],
        "rotation": (
            "Right-handed (X,Y,Z)=(x,-z,y); FLASH Bz=uz=0 in this application. "
            "Thus B_W=(Bx,0,By), J_W,y=-J_FLASH,z."
        ),
        "units": (
            "FLASH normalized UnitSystem=none; mu0=1; pressure is total scalar fluid pressure. "
            "No SI mapping is inferred by this helper."
        ),
        "eta_code": float(params.get("resistivity", 0.0)),
        "potential_relative_edge_residual": residual,
        "potential_definition": (
            "Bx=-dAy/dZ, Bz=dAy/dX; least-squares reconstruction, zero mean; "
            "original B arrays are also retained."
        ),
        "handoff_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "scope": (
            "Transfer/initialization material only; not kinetic qualification or claim evidence."
        ),
    }
    output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flash-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.flash_file, args.output), indent=2))
