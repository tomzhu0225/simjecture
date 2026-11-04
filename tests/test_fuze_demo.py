"""The public excerpt preserves arithmetic, rejection controls and failed candidates."""

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]
DEMO = Path("demos/fuze_mesh_solver_diagnostics")
spec = importlib.util.spec_from_file_location("fuze_verify", REPOSITORY / DEMO / "verify_record.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_retained_fuze_record():
    result = module.verify(REPOSITORY)
    assert result["flash_leaf_cells"] == 199800
    assert result["restart_maximum_relative_L2"] < 1e-10
    assert not result["axis_candidate_adopted"]


@pytest.fixture
def excerpt(tmp_path):
    shutil.copytree(REPOSITORY / DEMO, tmp_path / DEMO)
    assets = Path("docs/_static/demos/fuze")
    shutil.copytree(REPOSITORY / assets, tmp_path / assets)
    return tmp_path


def rewrite(excerpt, name, change):
    relative = DEMO / "record" / f"{name}.json"
    path = excerpt / relative
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))
    manifest_path = excerpt / DEMO / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))


def test_changed_figure_is_detected(excerpt):
    (excerpt / "docs/_static/demos/fuze/flash-paused.png").write_bytes(b"changed")
    with pytest.raises(ValueError, match="Changed retained artifact"):
        module.verify(excerpt)


@pytest.mark.parametrize(
    ("name", "change", "message"),
    [
        ("flash", lambda d: d["mesh"]["blocks_by_level"].update({"5": 329}), "Leaf block count"),
        (
            "restart",
            lambda d: d["matched_five_resumed_frames13field_L2"][0]["relative_L2"].pop("Pe"),
            "Incomplete 13-field",
        ),
        (
            "restart",
            lambda d: d["corruption_guard"].update(completed_physical_steps=1),
            "Corruption rejection",
        ),
        ("axis", lambda d: d.update(decision="adopt"), "Rejected axis candidate"),
        (
            "axis",
            lambda d: d["runs"][1]["frames"][0].update(time_us=15),
            "Unmatched physical times",
        ),
        ("axis", lambda d: d["runs"][1].update(actual_mass_kg=1), "Inconsistent values"),
    ],
)
def test_rehashed_inconsistent_audit_is_rejected(excerpt, name, change, message):
    rewrite(excerpt, name, change)
    with pytest.raises(ValueError, match=message):
        module.verify(excerpt)
