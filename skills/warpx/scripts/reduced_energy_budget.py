#!/usr/bin/env python3
"""Read a pinned single-level WarpX field-plus-particle energy budget safely."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

HEADER_TOKEN = re.compile(r"\[(\d+)\]([^\s]+)")
FIELD_TOTAL_LABEL = "total_lev0(J)"
PARTICLE_TOTAL_LABEL = "total(J)"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_table(path: Path) -> tuple[list[str], list[list[float]]]:
    lines = path.read_text().splitlines()
    if not lines or not lines[0].startswith("#"):
        raise ValueError(f"missing WarpX reduced-diagnostic header: {path}")
    indexed = {int(index): label for index, label in HEADER_TOKEN.findall(lines[0])}
    if not indexed or sorted(indexed) != list(range(max(indexed) + 1)):
        raise ValueError(f"non-contiguous reduced-diagnostic header: {path}")
    labels = [indexed[index] for index in range(len(indexed))]
    rows: list[list[float]] = []
    for line_number, line in enumerate(lines[1:], start=2):
        if not line.strip() or line.startswith("#"):
            continue
        try:
            row = [float(value) for value in line.split()]
        except ValueError as exc:
            raise ValueError(f"non-numeric row {line_number}: {path}") from exc
        if len(row) != len(labels):
            raise ValueError(
                f"row {line_number} has {len(row)} columns; header has "
                f"{len(labels)}: {path}"
            )
        if not all(math.isfinite(value) for value in row):
            raise ValueError(f"non-finite value in row {line_number}: {path}")
        rows.append(row)
    if not rows:
        raise ValueError(f"empty reduced diagnostic: {path}")
    return labels, rows


def exact_column(labels: list[str], required: str, *, path: Path) -> int:
    matches = [index for index, label in enumerate(labels) if label == required]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one {required!r} column in {path}; found {len(matches)}. "
            "Do not guess or sum total and component columns."
        )
    return matches[0]


def relative_change(initial: float, final: float, *, name: str) -> float:
    if initial == 0.0:
        raise ValueError(f"cannot normalize {name}: initial value is zero")
    return (final - initial) / abs(initial)


def energy_budget(
    field_path: Path,
    particle_path: Path,
    *,
    time_atol: float,
) -> dict[str, Any]:
    field_labels, field_rows = read_table(field_path)
    particle_labels, particle_rows = read_table(particle_path)
    field_total_column = exact_column(
        field_labels, FIELD_TOTAL_LABEL, path=field_path
    )
    particle_total_column = exact_column(
        particle_labels, PARTICLE_TOTAL_LABEL, path=particle_path
    )
    if len(field_rows) != len(particle_rows):
        raise ValueError("field and particle diagnostics have different row counts")
    for index, (field_row, particle_row) in enumerate(
        zip(field_rows, particle_rows, strict=True)
    ):
        if field_row[0] != particle_row[0] or not math.isclose(
            field_row[1],
            particle_row[1],
            rel_tol=0.0,
            abs_tol=time_atol,
        ):
            raise ValueError(
                f"field and particle step/time coordinates differ at row {index}"
            )

    field = [row[field_total_column] for row in field_rows]
    particle = [row[particle_total_column] for row in particle_rows]
    combined = [
        field_value + particle_value
        for field_value, particle_value in zip(field, particle, strict=True)
    ]
    return {
        "schema_version": "0.1.0",
        "kind": "warpx_reduced_energy_budget",
        "selection_policy": (
            "Select exact non-overlapping total columns from realized headers; "
            "never add a total column to its component or per-species columns."
        ),
        "inputs": {
            "field_path": str(field_path),
            "field_sha256": sha256(field_path),
            "particle_path": str(particle_path),
            "particle_sha256": sha256(particle_path),
        },
        "selected_columns": {
            "field": {
                "index": field_total_column,
                "label": field_labels[field_total_column],
            },
            "particle": {
                "index": particle_total_column,
                "label": particle_labels[particle_total_column],
            },
        },
        "ignored_columns": {
            "field": field_labels[field_total_column + 1 :],
            "particle": particle_labels[particle_total_column + 1 :],
        },
        "checks": {
            "rows_aligned": True,
            "all_values_finite": True,
            "exact_field_total_label": True,
            "exact_particle_total_label": True,
            "non_overlapping_totals_selected": True,
        },
        "points": len(combined),
        "initial": {
            "field_J": field[0],
            "particle_J": particle[0],
            "combined_J": combined[0],
        },
        "final": {
            "field_J": field[-1],
            "particle_J": particle[-1],
            "combined_J": combined[-1],
        },
        "relative_change": {
            "field": relative_change(field[0], field[-1], name="field energy"),
            "particle": relative_change(
                particle[0], particle[-1], name="particle energy"
            ),
            "combined": relative_change(
                combined[0], combined[-1], name="combined energy"
            ),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compute a single-level WarpX field-plus-particle energy budget by "
            "exact header identity."
        )
    )
    parser.add_argument("field_energy", type=Path)
    parser.add_argument("particle_energy", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--time-atol", type=float, default=1.0e-30)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.time_atol < 0.0:
        parser.error("--time-atol must be non-negative")
    try:
        result = energy_budget(
            args.field_energy,
            args.particle_energy,
            time_atol=args.time_atol,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(encoded)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
