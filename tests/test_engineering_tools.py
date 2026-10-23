import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest

from conjecture_solver import elmer
from conjecture_solver.deployment import DeploymentManager, DeploymentProfile
from conjecture_solver.mvp_agent import BubblewrapSandbox, MVPAgentConfig
from conjecture_solver.mvp_skills import MVPCapabilityConfig, MVPSkillCatalog
from conjecture_solver.web.workspace import CATALOGUE

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "profile,capability",
    [("freecad", "freecad-1.1.3"), ("gmsh", "gmsh-4.15.2"), ("elmer", "elmer-0.1")],
)
def test_general_engineering_tools_are_discoverable_and_installable(
    tmp_path, monkeypatch, profile, capability
):
    catalog = MVPSkillCatalog.discover(ROOT / "skills")
    assert profile in catalog
    assert catalog.read(profile, "SKILL.md", max_chars=20000)
    config = MVPCapabilityConfig.model_validate_json(
        (ROOT / "capabilities" / (capability + ".json")).read_bytes()
    )
    assert config.manifest.skill == profile
    assert any(name == profile for name, *_ in CATALOGUE)
    for path in (f"capabilities/{capability}.json", f"skills/{profile}/scripts/bootstrap.sh"):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
    (tmp_path / "environments").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname="test"\n')
    manager = DeploymentManager(tmp_path)
    monkeypatch.setattr(manager, "_core_checks", lambda **_: [])
    monkeypatch.setattr(manager, "_already_ready", lambda *_: None)
    kwargs = {}
    if profile == "elmer":
        source = tmp_path / "supplied-install"
        source.mkdir()
        kwargs["source"] = source
    report = manager.install(DeploymentProfile(profile), dry_run=True, **kwargs)
    assert report.planned, report


def test_native_elmer_accepts_non_em_sif_and_passes_arguments_unchanged(tmp_path, monkeypatch):
    sif = tmp_path / "thermal.sif"
    sif.write_text('Solver 1\n Procedure = "HeatSolve" "HeatSolver"\nEnd\n')
    native = tmp_path / "native"
    native.write_text(
        "#!/usr/bin/env python3\nimport json,sys,os\n"
        'open("received.json","w").write(json.dumps([sys.argv[1:],os.getcwd()]))\n'
        'print("ELMER SOLVER FINISHED")\n'
    )
    native.chmod(0o755)
    monkeypatch.setattr(
        elmer, "runtime", lambda: (native, native, os.environ.copy(), {"build": "test"})
    )
    result = elmer.run_native("solver", tmp_path, ["thermal.sif", "-silent"], record="thermal-run")
    assert result["execution_pass"]
    assert json.loads((tmp_path / "received.json").read_text()) == [
        ["thermal.sif", "-silent"],
        str(tmp_path),
    ]
    assert result["input_hashes"]["thermal.sif"] == elmer.digest(sif)
    assert sif.read_text().startswith("Solver 1")
    assert not (tmp_path / "case.json").exists()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap unavailable")
def test_standard_python_can_read_sample_and_slice_vtu(tmp_path):
    sandbox = BubblewrapSandbox(
        tmp_path / "workspace",
        MVPAgentConfig(max_iterations=1, max_memory_bytes=3 * 1024**3, max_command_seconds=60),
    )
    result = sandbox.run_python(
        (
            "-c",
            """import json, numpy as np, pyvista as pv
mesh = pv.ImageData(dimensions=(5,5,5), spacing=(.25,.25,.25))
mesh['temperature'] = 300 + 10 * mesh.points[:,0]
mesh.save('field.vti')
restored = pv.read('field.vti')
probe = pv.PolyData([[.5,.5,.5]]).sample(restored)
assert probe['vtkValidPointMask'][0] == 1
assert abs(probe['temperature'][0] - 305) < 1e-8
plane = restored.slice(normal='z', origin=(.5,.5,.5))
assert plane.n_cells > 0
print(json.dumps({'temperature_K': float(probe['temperature'][0])}))
""",
        )
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["temperature_K"] == 305


def test_setup_declares_pyvista_and_installed_dependency_is_importable():
    import tomllib

    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert any(name.startswith("pyvista") for name in metadata["project"]["dependencies"])
    assert importlib.util.find_spec("pyvista") is not None


def test_elmer_option_echo_does_not_report_false_nonconvergence(tmp_path):
    import sys

    result = elmer.run_process(
        [
            sys.executable,
            "-c",
            'print("Unused keywords: linear system abort not converged");'
            'print("ELMER SOLVER FINISHED")',
        ],
        tmp_path,
        "run",
        timeout=10,
        memory_gib=1,
        env=os.environ.copy(),
    )
    assert result["execution_pass"]


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap unavailable")
def test_standard_python_renders_pyvista_offscreen_with_labels(tmp_path):
    import ctypes.util

    if not ctypes.util.find_library("EGL") or not Path("/etc/fonts/fonts.conf").exists():
        pytest.skip("Headless EGL and font configuration are host dependencies")
    workspace = tmp_path / "workspace"
    sandbox = BubblewrapSandbox(
        workspace,
        MVPAgentConfig(max_iterations=1, max_memory_bytes=4 * 1024**3, max_command_seconds=60),
    )
    result = sandbox.run_python(
        (
            "-c",
            """import pyvista as pv
mesh = pv.Sphere()
mesh['height'] = mesh.points[:, 2]
plotter = pv.Plotter(off_screen=True, window_size=(320,240))
plotter.add_mesh(mesh, scalars='height')
plotter.show(screenshot='field.png')
""",
        )
    )
    assert result.returncode == 0, result.stderr
    from PIL import Image

    with Image.open(workspace / "field.png") as image:
        assert image.size == (320, 240)
        assert any(low != high for low, high in image.getextrema())
