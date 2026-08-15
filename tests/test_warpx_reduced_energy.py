from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/warpx/scripts/reduced_energy_budget.py"
)


def write_tables(directory: Path) -> tuple[Path, Path]:
    field = directory / "field_energy.txt"
    particle = directory / "particle_energy.txt"
    field.write_text(
        "#[0]step() [1]time(s) [2]total_lev0(J) [3]E_lev0(J) [4]B_lev0(J)\n"
        "0 0.0 10.0 2.0 8.0\n"
        "1 1.0 8.0 3.0 5.0\n"
    )
    particle.write_text(
        "#[0]step() [1]time(s) [2]total(J) [3]electrons(J) [4]ions(J) "
        "[5]total_mean(J)\n"
        "0 0.0 5.0 2.0 3.0 0.1\n"
        "1 1.0 8.0 3.0 5.0 0.2\n"
    )
    return field, particle


def test_reduced_energy_reader_selects_only_exact_totals(tmp_path: Path) -> None:
    field, particle = write_tables(tmp_path)
    output = tmp_path / "budget.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(field),
            str(particle),
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result == json.loads(output.read_text())
    assert result["selected_columns"]["field"] == {
        "index": 2,
        "label": "total_lev0(J)",
    }
    assert result["selected_columns"]["particle"] == {
        "index": 2,
        "label": "total(J)",
    }
    assert result["initial"]["combined_J"] == 15.0
    assert result["final"]["combined_J"] == 16.0
    assert result["relative_change"]["combined"] == 1.0 / 15.0
    assert result["checks"]["non_overlapping_totals_selected"] is True


def test_reduced_energy_reader_rejects_unknown_field_schema(tmp_path: Path) -> None:
    field, particle = write_tables(tmp_path)
    field.write_text(
        "#[0]step() [1]time(s) [2]E_lev0(J) [3]B_lev0(J)\n"
        "0 0.0 2.0 8.0\n"
        "1 1.0 3.0 5.0\n"
    )
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(field), str(particle)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "Do not guess or sum total and component columns" in completed.stderr


def test_reduced_energy_reader_rejects_misaligned_rows(tmp_path: Path) -> None:
    field, particle = write_tables(tmp_path)
    particle.write_text(particle.read_text().replace("1 1.0 8.0", "2 1.0 8.0"))
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(field), str(particle)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "step/time coordinates differ" in completed.stderr
