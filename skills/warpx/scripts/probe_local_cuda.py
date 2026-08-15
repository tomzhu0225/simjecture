#!/usr/bin/env python3
"""Report whether the loaded WarpX runtime is usable for local CUDA work."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np


def hdf5_roundtrip(workdir: Path | None) -> bool:
    """Write and read one scalar through the openPMD HDF5 backend."""
    import openpmd_api as io

    def exercise(root: Path) -> bool:
        path = root / "openpmd-probe.h5"
        series = io.Series(str(path), io.Access.create)
        component = series.iterations[0].meshes["probe"][
            io.Mesh_Record_Component.SCALAR
        ]
        component.reset_dataset(io.Dataset(np.dtype("float64"), [1]))
        component.store_chunk(np.array([1.25]))
        series.close()

        readback = io.Series(str(path), io.Access.read_only)
        loaded = readback.iterations[0].meshes["probe"][
            io.Mesh_Record_Component.SCALAR
        ].load_chunk()
        readback.flush()
        value = float(loaded[0])
        readback.close()
        return value == 1.25

    if workdir is not None:
        workdir.mkdir(parents=True, exist_ok=True)
        return exercise(workdir)
    with tempfile.TemporaryDirectory(prefix="warpx-openpmd-probe-") as path:
        return exercise(Path(path))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-openpmd",
        action="store_true",
        help="fail unless a temporary HDF5 openPMD series can be read back",
    )
    parser.add_argument("--workdir", type=Path)
    args = parser.parse_args()

    import amrex.space2d as amrex
    import openpmd_api as io

    smi = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,compute_cap,driver_version",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()[0]
    name, memory_mib, compute_capability, driver = (
        item.strip() for item in smi.split(",")
    )

    openpmd_hdf5 = bool(io.variants.get("hdf5", False))
    openpmd_roundtrip = openpmd_hdf5 and hdf5_roundtrip(args.workdir)
    result = {
        "amrex": {
            "gpu_backend": str(amrex.Config.gpu_backend),
            "have_gpu": bool(amrex.Config.have_gpu),
            "have_mpi": bool(amrex.Config.have_mpi),
            "have_omp": bool(amrex.Config.have_omp),
        },
        "gpu": {
            "name": name,
            "memory_mib": int(memory_mib),
            "compute_capability": compute_capability,
            "driver": driver,
        },
        "openpmd_api": {
            "version": io.__version__,
            "hdf5": openpmd_hdf5,
            "mpi": bool(io.variants.get("mpi", False)),
        },
    }
    usable = result["amrex"]["have_gpu"] and (
        str(result["amrex"]["gpu_backend"]).upper() == "CUDA"
    )
    result["checks"] = {
        "cuda_warpx": usable,
        "openpmd_hdf5_reader": openpmd_hdf5,
        "openpmd_hdf5_roundtrip": openpmd_roundtrip,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if not usable:
        return 1
    if args.require_openpmd and not openpmd_roundtrip:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
