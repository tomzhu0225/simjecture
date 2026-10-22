"""Prescribed-current polyline Biot–Savart screening, in SI units.

This is a geometry/field smoke test, not an eddy-current or circuit solver.
No commercial CAD or simulation runtime is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

MU0_OVER_4PI = 1e-7


def polyline_field(points_m, vertices_m, current_a, *, exclusion_radius_m=0.0):
    """Exact finite-segment field; reject probes on/too near the filament.

    Segments carry current from vertex i to i+1. A path need not be closed,
    but callers must describe the rest of the physical return circuit.
    The exclusion radius is a probe validity guard, not a field regularizer.
    """
    points = np.asarray(points_m, dtype=float)
    vertices = np.asarray(vertices_m, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not len(points):
        raise ValueError("points_m must be a nonempty N by 3 array")
    if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 2:
        raise ValueError("vertices_m must be an N by 3 array with at least two vertices")
    if not np.isfinite(points).all() or not np.isfinite(vertices).all():
        raise ValueError("Coordinates must be finite")
    if not np.isfinite(current_a) or not np.isfinite(exclusion_radius_m):
        raise ValueError("Current and exclusion radius must be finite")
    if exclusion_radius_m < 0:
        raise ValueError("Exclusion radius must be nonnegative")
    delta = np.diff(vertices, axis=0)
    length = np.linalg.norm(delta, axis=1)
    if np.any(length <= 0):
        raise ValueError("Zero-length segments are not permitted")
    unit = delta / length[:, None]
    field = np.zeros_like(points)
    # Bound temporary memory independently of the number of probes/segments.
    for first in range(0, len(points), 64):
        probes = points[first : first + 64]
        for start in range(0, len(delta), 1024):
            u, ell = unit[start : start + 1024], length[start : start + 1024]
            r = probes[:, None, :] - vertices[None, start : start + len(u), :]
            s = np.einsum("pse,se->ps", r, u)
            perp = r - s[:, :, None] * u
            rho2 = np.einsum("pse,pse->ps", perp, perp)
            nearest = np.clip(s, 0, ell)
            distance2 = rho2 + (s - nearest) ** 2
            # Absolute 1 pm guard avoids 0/0 on the filament without hiding
            # probes along the segment's extension, where the field is zero.
            if np.any(distance2 <= max(exclusion_radius_m, 1e-12) ** 2):
                raise ValueError("Probe lies on or inside the filament exclusion radius")
            r1 = np.sqrt(rho2 + s**2)
            r2 = np.sqrt(rho2 + (s - ell) ** 2)
            weight = np.divide(
                s / r1 - (s - ell) / r2,
                rho2,
                out=np.zeros_like(rho2),
                where=rho2 > 1e-30,
            )
            field[first : first + len(probes)] += (
                MU0_OVER_4PI * current_a * np.sum(np.cross(u, perp) * weight[:, :, None], axis=1)
            )
    return field


def run_case(case):
    """Evaluate a versioned, explicit-SI prescribed-current input."""
    if case.get("schema_version") != "1.0" or case.get("units") != "SI":
        raise ValueError("Case requires schema_version=1.0 and units=SI")
    probes = case["probes"]
    names = [p["name"] for p in probes]
    if len(names) != len(set(names)):
        raise ValueError("Probe names must be unique")
    points = [p["position_m"] for p in probes]
    total = np.zeros((len(points), 3))
    components = {}
    for path in case["paths"]:
        name = path["name"]
        if name in components:
            raise ValueError("Path names must be unique")
        b = polyline_field(
            points,
            path["vertices_m"],
            path["current_a"],
            exclusion_radius_m=path.get("exclusion_radius_m", 0),
        )
        components[name] = b.tolist()
        total += b
    if not components:
        raise ValueError("At least one current path is required")
    return {
        "schema_version": "1.0",
        "model": "prescribed-current filament Biot-Savart",
        "qualification": "geometry screening only; no circuit or transient conductor solution",
        "probes": [
            {
                "name": name,
                "position_m": position,
                "B_T": b.tolist(),
                "Bnorm_T": float(np.linalg.norm(b)),
            }
            for name, position, b in zip(names, points, total, strict=True)
        ],
        "components_T": components,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.case.read_bytes()
    result = run_case(json.loads(raw))
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    result["driver_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
