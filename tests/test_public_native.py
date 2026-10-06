"""Native examples reject executable input and invalid diagnostic schemas."""

from pathlib import Path

import pytest

from conjecture_solver.public.native import digest, materialize, reduced_table, validate


def entry(tmp_path):
    binary, template = tmp_path / "installed", tmp_path / "template"
    binary.write_bytes(b"operator executable identity")
    template.write_text("amr.n_cell = {{cells}}\n")
    return {
        "id": "commissioned-example",
        "name": "Example",
        "family": "warpx",
        "binary": str(binary),
        "binary_sha256": digest(binary),
        "template": str(template),
        "template_sha256": digest(template),
        "parameters": {"cells": {"default": 32, "choices": [32, 64], "integer": True}},
        "scope": "A commissioned model",
        "qualification": "Actual operator qualification",
    }


@pytest.mark.parametrize(
    "parameters",
    [
        {"cells": "32; touch /tmp/unauthorized"},
        {"cells": True},
        {"cells": 32.0},
        {"cells": float("nan")},
        {"cells": 128},
        {"binary": "/bin/sh"},
        {"cells": 32, "input": "../../../private"},
    ],
)
def test_native_parameters_cannot_become_code_or_paths(tmp_path, parameters):
    with pytest.raises(ValueError):
        validate(entry(tmp_path), parameters)


@pytest.mark.parametrize("changed", ["binary", "template"])
def test_runtime_or_template_change_requires_requalification(tmp_path, changed):
    value = entry(tmp_path)
    Path(value[changed]).write_text("unqualified replacement")
    with pytest.raises(ValueError, match="requalification"):
        materialize(value, {}, tmp_path / "experiment")
    assert not (tmp_path / "experiment").exists()


def test_reduced_energy_uses_named_total_without_double_counting(tmp_path):
    path = tmp_path / "energy.txt"
    path.write_text(
        "# [0]step() [1]time(s) [2]total(J) [3]electron(J) [4]ion(J)\n0 0 11 10 1\n1 0.1 22 20 2\n"
    )
    _, _, total, header = reduced_table(path, "total(J)")
    assert total.tolist() == [11, 22] and "electron(J)" in header
    with pytest.raises(ValueError, match="Unknown"):
        reduced_table(path, "total_lev0(J)")


@pytest.mark.parametrize("rows", ["0 0 1\n1 0.1 nan\n", "0 0 1 2\n"])
def test_invalid_reduced_diagnostics_never_form_evidence(tmp_path, rows):
    path = tmp_path / "energy.txt"
    path.write_text("# [0]step() [1]time(s) [2]total(J)\n" + rows)
    with pytest.raises(ValueError, match="Incomplete|non-finite"):
        reduced_table(path, "total(J)")


def test_flash_diagnostics_use_snapshot_time_and_application_output_prefix(tmp_path, monkeypatch):
    import h5py
    import numpy as np

    from conjecture_solver.public.native import analyze_flash

    monkeypatch.chdir(tmp_path)
    for name, time in (
        ("island_hdf5_plt_cnt_0000", 0.0),
        ("island_forced_hdf5_plt_cnt_0000", 0.05),
    ):
        with h5py.File(name, "w") as data:
            scalars = np.array([(b"time", time)], dtype=[("name", "S80"), ("value", "f8")])
            data["real scalars"] = scalars
            data["dens"] = np.ones((1, 1, 8, 8))
            data["bounding box"] = np.array([[[-0.5, 0.5], [-0.5, 0.5]]])
    case = {"name": "Magnetic island", "parameters": {"end_time": 0.05}, "geometry": "2d"}
    result = analyze_flash(case)
    assert result["final_time_code_units"] == 0.05
    assert (tmp_path / "evolution.png").is_file()
    case["parameters"]["end_time"] = 0.04
    with pytest.raises(ValueError, match="requested physical time"):
        analyze_flash(case)
    import zipfile

    from conjecture_solver.public.native import preserve_raw_output

    preserve_raw_output()
    with zipfile.ZipFile("raw-output.zip") as archive:
        assert "island_hdf5_plt_cnt_0000" in archive.namelist()
        assert "island_forced_hdf5_plt_cnt_0000" in archive.namelist()
