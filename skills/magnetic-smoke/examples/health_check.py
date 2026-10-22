"""Cheap analytic checks; no experimental qualification is implied."""

import importlib.util
import json
import os
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location(
    "magnetic_driver", os.environ["SIMJECTURE_MAGNETIC_DRIVER"]
)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
angle = np.linspace(0, 2 * np.pi, 721)
radius, current = 0.01, 1000.0
loop = np.column_stack([radius * np.cos(angle), radius * np.sin(angle), np.zeros_like(angle)])
field = driver.polyline_field([[0, 0, 0]], loop, current)[0]
expected_loop = 2 * np.pi * 1e-7 * current / radius
wire = driver.polyline_field([[0.01, 0, 0]], [[0, 0, -0.1], [0, 0, 0.1]], current)[0]
expected_wire = 2e-7 * current / 0.01 * 0.1 / np.hypot(0.01, 0.1)
Path("magnetic_health.json").write_text(
    json.dumps(
        {
            "checks": {
                "finite": bool(np.isfinite(field).all() and np.isfinite(wire).all()),
                "circular_loop": bool(
                    np.allclose(field, [0, 0, expected_loop], rtol=1e-4, atol=1e-12)
                ),
                "finite_wire": bool(
                    np.allclose(wire, [0, expected_wire, 0], rtol=1e-12, atol=1e-12)
                ),
            },
            "scope": "Analytic filament checks only; not a conductor/circuit qualification.",
        },
        indent=2,
    )
    + "\n"
)
