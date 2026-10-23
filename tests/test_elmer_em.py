import importlib.util
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

from conjecture_solver import elmer as general
from conjecture_solver import elmer_em as em
from conjecture_solver.deployment import DeploymentManager, DeploymentProfile
from conjecture_solver.mvp_skills import MVPCapabilityConfig, MVPSkillCatalog


def sample_config():
    return {
        "schema_version": "0.1",
        "units": "SI",
        "dt_s": 1e-6,
        "steps": 4,
        "linear_tolerance": 1e-10,
        "materials": [{"tag": 100, "conductivity_S_m": 5.8e7}, {"tag": 101, "conductivity_S_m": 0}],
        "boundaries": {"input": [300], "ground": [301], "outer": [200]},
        "driver": {
            "kind": "rlc",
            "R_ohm": 10,
            "L_H": 0.001,
            "C_F": 1e-6,
            "V0_V": 1000,
            "provenance": "Synthetic control",
        },
        "probes": [{"name": "side", "position_m": [0.002, 0, 0]}],
        "current_regions": [
            {"name": "wire", "tags": [100], "length_m": 0.02, "direction": [0, 0, -1]}
        ],
        "current_balances": [["wire"]],
        "limits": {"current_relative": 1e-4, "energy_relative": 1e-3, "circuit_relative": 1e-6},
    }


def test_finite_capacitor_discharge_energy_and_corruption():
    driver = sample_config()["driver"]
    current, drop = [], []
    previous = np.zeros(2)
    h, load_r = 2e-6, 3.0
    for _ in range(40):
        # Separate BE recurrence, with a passive resistor as the load.
        previous = np.linalg.solve(
            [[1 + h * 13 / 0.001, h / 0.001], [-h / 1e-6, 1]], previous + [h * 1000 / 0.001, 0]
        )
        current.append(previous[0])
        drop.append(previous[1])
    current, drop = np.array(current), np.array(drop)
    t = h * np.arange(1, 41)
    report = em.circuit_audit(driver, t, current, load_r * current, drop)
    assert max(report[k] for k in ("kvl_relative", "charge_relative", "energy_relative")) < 1e-12
    assert report["backward_Euler_dissipation_J"] > 0
    assert report["initial_energy_J"] == 0.5
    corrupt = em.circuit_audit(driver, t, current, load_r * current + 100, drop)
    assert corrupt["kvl_relative"] > 0.09
    assert corrupt["energy_relative"] > 0.01


@pytest.mark.parametrize("marker", general.FAILURES)
def test_exit_zero_with_solver_breakdown_is_rejected(tmp_path, marker):
    result = em.run_process(
        [sys.executable, "-c", f'print({marker!r});print("ELMER SOLVER FINISHED")'],
        tmp_path,
        "run",
        timeout=10,
        memory_gib=1,
        env=os.environ.copy(),
    )
    assert result["returncode"] == 0
    assert result["execution_pass"] is False
    assert result["failure_markers"]


def test_runner_timeout_and_fresh_trial_requirement(tmp_path):
    result = em.run_process(
        [sys.executable, "-c", "import time;time.sleep(20)"],
        tmp_path,
        "run",
        timeout=0.1,
        memory_gib=1,
        env=os.environ.copy(),
    )
    assert result["timed_out"] and not result["execution_pass"]
    with pytest.raises(ValueError, match="fresh case"):
        em.run_process(
            [sys.executable, "-c", "pass"],
            tmp_path,
            "run",
            timeout=1,
            memory_gib=1,
            env=os.environ.copy(),
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c.update(units="mm"),
        lambda c: c.update(dt_s=float("nan")),
        lambda c: c["driver"].update(C_F=0),
        lambda c: c["driver"].update(provenance=""),
        lambda c: c["boundaries"].update(input=[200]),
        lambda c: c["current_regions"][0].update(direction=[0, 0, 2]),
        lambda c: c["current_regions"][0].update(tags=[101]),
        lambda c: c.update(current_balances=[["wire", "wire"]]),
    ],
)
def test_invalid_model_inputs_fail(change):
    config = sample_config()
    change(config)
    with pytest.raises(ValueError):
        em.validate(config)


def test_declared_model_reaches_sif_and_circuit(tmp_path):
    config = em.validate(sample_config())
    em.generate_case(tmp_path, config)
    sif = (tmp_path / "case.sif").read_text()
    circuit = (tmp_path / "circuit.definitions").read_text()
    assert "Timestep Sizes = 1e-06" in sif
    assert "Linear System Convergence Tolerance = 1e-10" in sif
    assert "SaveScalars" in sif and "Export Lagrange Multiplier" in sif
    assert "C.1.A(0,0) = 0.001" in circuit
    assert "C.1.A(2,2) = 1e-06" in circuit
    assert "Vbank0 = Real 1000" in sif
    assert em.read(tmp_path / "body-map.json") == {"100": 1, "101": 2}


def test_skill_discovery_and_install_contract(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    catalog = MVPSkillCatalog.discover(root / "skills")
    assert "elmer" in catalog
    assert catalog.read("elmer", "references/case-interface.md", max_chars=20000)
    config = MVPCapabilityConfig.model_validate_json(
        (root / "capabilities/elmer-0.1.json").read_bytes()
    )
    assert "elmer/lib/elmersolver/libelmersolver.so" in config.identity_files
    assert config.manifest.preflight_checks
    project = tmp_path / "project"
    for relative in ("capabilities/elmer-0.1.json", "skills/elmer/scripts/bootstrap.sh"):
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)
    (project / "environments").mkdir()
    (project / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    manager = DeploymentManager(project_root=project)
    monkeypatch.setattr(manager, "_core_checks", lambda **_: [])
    monkeypatch.setattr(manager, "_already_ready", lambda *_: None)
    report = manager.install(DeploymentProfile.ELMER, dry_run=True)
    assert not report.ready
    assert any(c.name.endswith(".source") for c in report.checks)
    source = tmp_path / "elmer-install"
    source.mkdir()
    report = manager.install(DeploymentProfile.ELMER, source=source, dry_run=True)
    assert report.planned and "--source" in report.command


def test_plot_rejects_failed_audit(tmp_path):
    em.save(tmp_path / "audit.json", {"numerical_checks_pass": False})
    with pytest.raises(ValueError, match="Rejected case"):
        em.plot(tmp_path)


def test_installer_rejects_unmanaged_runtime(tmp_path, monkeypatch):
    source = tmp_path / "source"
    for name in (
        "bin/ElmerGrid",
        "bin/ElmerSolver",
        "lib/elmersolver/libelmersolver.so",
        "share/elmersolver/lib/elements.def",
    ):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test")
    target = tmp_path / "runtime"
    target.mkdir()
    sentinel = target / "keep"
    sentinel.write_text("original")
    script = Path(__file__).resolve().parents[1] / "skills/elmer/scripts/bootstrap.py"
    spec = importlib.util.spec_from_file_location("bootstrap_elmer", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        sys,
        "argv",
        ["bootstrap", "--prefix", str(target), "--project-root", ".", "--source", str(source)],
    )
    with pytest.raises(SystemExit):
        module.main()
    assert sentinel.read_text() == "original"


def test_runtime_module_changes_invalidate_build_record(tmp_path, monkeypatch):
    home = tmp_path / "elmer"
    for name in ("bin/ElmerSolver", "bin/ElmerGrid", "share/elmersolver/lib/MagnetoDynamics.so"):
        p = home / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("original")
    monkeypatch.setenv("SIMJECTURE_ELMER_HOME", str(home))
    identity = em.runtime()[3]
    (tmp_path / "share").mkdir()
    em.save(tmp_path / "share/build-record.json", {"elmer_identity": identity})
    assert em.runtime()[3] == identity
    (home / "share/elmersolver/lib/MagnetoDynamics.so").write_text("changed")
    with pytest.raises(ValueError, match="Elmer files changed"):
        em.runtime()
