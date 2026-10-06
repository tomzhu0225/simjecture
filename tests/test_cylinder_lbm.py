import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from conjecture_solver.cylinder_lbm import force_statistics
from conjecture_solver.cylinder_lbm_benchmark import task
from conjecture_solver.deployment import DeploymentProfile
from conjecture_solver.public.native import materialize


def test_complete_period_statistics_preserve_the_force_definitions():
    samples = np.arange(5000)
    lift = 2 + 0.4 * np.sin(2 * np.pi * samples / 100)
    drag = 1.3 + 0.01 * np.sin(4 * np.pi * samples / 100)
    stats = force_statistics(drag, lift, nd=32, speed=0.06)
    assert stats["n_cycles"] == 10
    assert stats["periodic_statistics_qualified"]
    assert stats["St"] == pytest.approx(32 / (0.06 * 100), rel=1e-8)
    assert stats["Cd_mean"] == pytest.approx(1.3, abs=1e-5)
    assert stats["Cl_rms"] == pytest.approx(0.4 / np.sqrt(2), rel=0.001)
    assert stats["Cl_rms_about_zero"] > 2
    assert stats["Cl_mean"] == pytest.approx(2, abs=0.001)


def test_steady_or_short_runs_do_not_claim_periodic_statistics():
    for lift in (np.zeros(500), np.sin(np.arange(50) / 20)):
        stats = force_statistics(np.ones(len(lift)), lift, 32, 0.06)
        assert stats["St"] is None
        assert not stats["periodic_statistics_qualified"]
    with pytest.raises(ValueError, match="finite"):
        force_statistics(np.ones(2), np.array([np.nan, 1]), 32, 0.06)


def test_contribution_is_preserved_and_credited():
    from conjecture_solver import cylinder_lbm

    root = Path(cylinder_lbm.__file__).parent / "vendor/cylinder_lbm"
    record = json.loads((root / "provenance.json").read_text())
    assert (
        hashlib.sha256((root / "cylinder_warp_lbm_solver.py").read_bytes()).hexdigest()
        == record["solver_sha256"]
    )
    assert record["author"] == "Zifei Meng" and record["license"] == "Apache-2.0"
    assert (root / "LICENSE").read_text().lstrip().startswith("Apache License")
    assert (root / "docs/grid_convergence.md").is_file()
    assert DeploymentProfile("warp-lbm") == DeploymentProfile.WARP_LBM
    benchmark = task()
    assert not benchmark["ranked_results_available"]
    assert benchmark["capability"] == "warp-lbm-cylinder-1.0"


def test_native_source_identity_is_checked_before_execution(tmp_path):
    binary, template, source = (tmp_path / name for name in ("python", "input", "solver"))
    for path in (binary, template, source):
        path.write_text("original")

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    entry = {
        "id": "lbm",
        "name": "Cylinder",
        "family": "lbm",
        "parameters": {},
        "binary": str(binary),
        "binary_sha256": digest(binary),
        "template": str(template),
        "template_sha256": digest(template),
        "identity_files": {str(source): digest(source)},
        "scope": "Fixture",
        "qualification": "Fixture",
    }
    case = materialize(entry, {}, tmp_path / "first")
    assert case["identity_files"] == entry["identity_files"]
    source.write_text("changed")
    with pytest.raises(ValueError, match="source or driver changed"):
        materialize(entry, {}, tmp_path / "second")
