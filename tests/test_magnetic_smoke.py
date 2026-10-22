import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from conjecture_solver import magnetic_smoke
from conjecture_solver.deployment import DeploymentManager, DeploymentProfile
from conjecture_solver.magnetic_smoke import polyline_field, run_case
from conjecture_solver.mvp_skills import MVPCapabilityConfig, MVPCapabilityInstallation


def test_finite_wire_and_collinear_extension():
    r, half_length, current = 0.02, 0.1, 700.0
    result = polyline_field(
        [[r, 0, 0], [0, 0, 0.2]], [[0, 0, -half_length], [0, 0, half_length]], current
    )
    expected = 2e-7 * current * half_length / (r * np.hypot(r, half_length))
    assert result[0] == pytest.approx([0, expected, 0], rel=1e-12)
    assert result[1] == pytest.approx([0, 0, 0], abs=1e-14)


def test_loop_axial_field_and_geometry_resolution():
    errors = []
    radius, current, z = 0.008, 1200.0, 0.003
    analytic = 2 * np.pi * 1e-7 * current * radius**2 / (radius**2 + z**2) ** 1.5
    for n in (60, 120, 240):
        t = np.linspace(0, 2 * np.pi, n + 1)
        loop = np.column_stack([radius * np.cos(t), radius * np.sin(t), t * 0])
        field = polyline_field([[0, 0, z]], loop, current)[0]
        errors.append(abs(field[2] / analytic - 1))
        assert field[:2] == pytest.approx([0, 0], abs=1e-14)
        assert polyline_field([[0, 0, z]], loop[::-1], current)[0] == pytest.approx(-field)
    assert errors[1] < errors[0] / 3.9
    assert errors[2] < errors[1] / 3.9
    assert errors[2] < 1e-4


def test_rigid_rotation_translation_and_batched_probes():
    points = np.tile([[0.01, 0, 0], [0.02, 0, 0.03]], (40, 1))
    vertices = np.column_stack([np.zeros(2051), np.zeros(2051), np.linspace(-0.1, 0.1, 2051)])
    transform = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]])
    offset = np.array([0.2, -0.3, 0.1])
    base = polyline_field(points, vertices, 900)
    moved = polyline_field(points @ transform.T + offset, vertices @ transform.T + offset, 900)
    assert moved == pytest.approx(base @ transform.T, rel=1e-10, abs=1e-14)
    assert polyline_field(points, [vertices[0], vertices[-1]], 900) == pytest.approx(base)


@pytest.mark.parametrize(
    "points,vertices,radius",
    [
        ([[0, 0, 0]], [[0, 0, -1], [0, 0, 1]], 0),
        ([[0.001, 0, 0]], [[0, 0, -1], [0, 0, 1]], 0.002),
        ([[np.nan, 0, 0]], [[0, 0, -1], [0, 0, 1]], 0),
        ([[1, 0, 0]], [[0, 0, 0], [0, 0, 0]], 0),
    ],
)
def test_invalid_or_interior_probes_fail(points, vertices, radius):
    with pytest.raises(ValueError):
        polyline_field(points, vertices, 1, exclusion_radius_m=radius)


def test_cli_explicit_si_and_vector_output(tmp_path):
    case = {
        "schema_version": "1.0",
        "units": "SI",
        "probes": [{"name": "side", "position_m": [0.02, 0, 0]}],
        "paths": [{"name": "wire", "current_a": 1000, "vertices_m": [[0, 0, -0.1], [0, 0, 0.1]]}],
    }
    source = tmp_path / "case.json"
    target = tmp_path / "result.json"
    source.write_text(json.dumps(case))
    subprocess.run(
        [
            sys.executable,
            str(Path(magnetic_smoke.__file__)),
            "--case",
            str(source),
            "--output",
            str(target),
        ],
        check=True,
    )
    result = json.loads(target.read_text())
    assert result["probes"][0]["B_T"][1] > 0
    assert result["input_sha256"] and result["driver_sha256"]
    assert "no circuit" in result["qualification"]
    with pytest.raises(ValueError, match="units=SI"):
        run_case({**case, "units": "mm"})


def test_deployment_and_driver_identity_binding(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    config = MVPCapabilityConfig.model_validate_json(
        (root / "capabilities/magnetic-smoke-1.0.json").read_bytes()
    )
    assert config.manifest.preflight_checks
    runtime = tmp_path / "runtime"
    (runtime / "bin").mkdir(parents=True)
    executable = runtime / "bin/python"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    for relative in config.identity_files:
        target = runtime / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("original")
    descriptor = tmp_path / "capability.json"
    descriptor.write_text(config.model_copy(update={"runtime_root": "runtime"}).model_dump_json())
    installed = MVPCapabilityInstallation.read(descriptor)
    installed.assert_runtime_identity()
    (runtime / "share/magnetic_smoke.py").write_text("changed")
    with pytest.raises(RuntimeError, match="changed after"):
        installed.assert_runtime_identity()
    project = tmp_path / "project"
    for relative in (
        "capabilities/magnetic-smoke-1.0.json",
        "skills/magnetic-smoke/scripts/bootstrap.sh",
        "pyproject.toml",
    ):
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)
    (project / "environments").mkdir()
    manager = DeploymentManager(project)
    monkeypatch.setattr(DeploymentManager, "_core_checks", lambda *a, **kw: [])
    report = manager.install(DeploymentProfile.MAGNETIC_SMOKE, dry_run=True)
    assert "bootstrap.sh" in str(report.model_dump())
