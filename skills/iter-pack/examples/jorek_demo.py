"""Numerical readiness for a registered model600 build, not an instability claim."""

import json
import os
import subprocess
from pathlib import Path

import h5py
import numpy as np

root = Path(os.environ["JOREK_ROOT"])
Path("input").write_bytes((root / "share/demo-input").read_bytes())
with open("input") as data, open("jorek.log", "w") as log:
    result = subprocess.run(
        ["mpirun", "-np", "2", str(root / "bin/jorek_model600")],
        stdin=data,
        stdout=log,
        stderr=subprocess.STDOUT,
        timeout=100,
    )
text = Path("jorek.log").read_text(errors="replace")
metrics = {}
if result.returncode == 0 and Path("jorek000003.h5").is_file():
    with h5py.File("jorek000003.h5") as data:
        for name in ("t_now", "n_elements", "n_tor", "n_period", "area_t", "volume_t"):
            metrics[name] = np.asarray(data[name]).tolist()
        metrics["finite_solution"] = bool(np.isfinite(data["values"][...]).all())
checks = {
    "completed": result.returncode == 0 and "After step 000003" in text,
    "finite_solution": metrics.get("finite_solution", False),
    "three_steps": bool(np.allclose(metrics.get("t_now", -1), 3.0)),
    "circular_area": bool(np.allclose(metrics.get("area_t", -1), np.pi, rtol=0.002)),
}
Path("jorek_demo.json").write_text(
    json.dumps(
        {
            "checks": checks,
            "metrics": metrics,
            "returncode": result.returncode,
            "scope": "Three-step reduced-MHD readiness, n=0/6; not a converged tearing-mode study",
            "metadata_warnings": text.count("HDF5-DIAG"),
        },
        indent=2,
    )
    + "\n"
)
if not all(checks.values()):
    raise SystemExit(1)
