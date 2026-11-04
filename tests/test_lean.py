"""The Lean integration must not mistake compilation or a failed proof for evidence."""

import json
import shutil
from pathlib import Path

import pytest

from conjecture_solver import lean_check
from conjecture_solver.deployment import DeploymentManager, DeploymentProfile
from conjecture_solver.mvp_agent import BubblewrapSandbox, MVPAgentConfig
from conjecture_solver.mvp_skills import MVPCapabilityRegistry, MVPSkillCatalog

ROOT = Path(__file__).resolve().parents[1]
INSTALLED = (ROOT / ".runtime/lean-4.24.0/share/build-record.json").is_file()


def test_lean_discovery_and_install_plan(tmp_path, monkeypatch):
    catalog = MVPSkillCatalog.discover(ROOT / "skills")
    assert "lean" in catalog
    for relative in ["capabilities/lean-4.24.0.json", "skills/lean/scripts/bootstrap.sh"]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    (tmp_path / "environments").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname="test"\n')
    manager = DeploymentManager(tmp_path)
    monkeypatch.setattr(manager, "_core_checks", lambda **_: [])
    monkeypatch.setattr(manager, "_already_ready", lambda *_: None)
    assert manager.install(DeploymentProfile.LEAN, dry_run=True).planned


def test_rejected_source_has_frozen_receipt(tmp_path):
    source = tmp_path / "Bad.lean"
    source.write_text("theorem invalid : False := by sorry\n")
    result = lean_check.check(source, ["invalid"], output=tmp_path / "receipt")
    assert result["status"] == "rejected_source"
    assert not result["checked"]
    assert result["source_sha256"] == lean_check.digest(source)
    assert (tmp_path / "receipt/Candidate.lean").read_bytes() == source.read_bytes()
    with pytest.raises(FileExistsError):
        lean_check.check(source, ["invalid"], output=tmp_path / "receipt")


@pytest.mark.skipif(not INSTALLED or not shutil.which("bwrap"), reason="installed Lean required")
def test_real_sandbox_checks_valid_false_placeholder_and_non_theorem(tmp_path):
    shutil.copy2(ROOT / "skills/lean/examples/health_check.py", tmp_path / "health.py")
    registry = MVPCapabilityRegistry.discover(ROOT / "capabilities", names=("lean-4.24.0",))
    sandbox = BubblewrapSandbox(
        tmp_path,
        MVPAgentConfig(
            max_iterations=1,
            max_memory_bytes=4 * 1024**3,
            max_command_seconds=120,
        ),
        registry,
    )
    result = sandbox.run_capability("lean-4.24.0", ("health.py",), timeout_seconds=120)
    assert result.returncode == 0, result.stdout + result.stderr
    checks = json.loads((tmp_path / "lean_health.json").read_text())["checks"]
    assert all(checks.values())
    false = json.loads((tmp_path / "false_claim_unproved/result.json").read_text())
    assert false["status"] == "undecided"
    valid = json.loads((tmp_path / "valid_proof/result.json").read_text())
    assert valid["status"] == "proved"
    assert set(valid["axioms"]["sample"]) <= lean_check.ALLOWED_AXIOMS
    native = json.loads((tmp_path / "native_axiom_rejected/result.json").read_text())
    assert native["compile_returncode"] == 0
    assert native["status"] == "undecided"
    assert set(native["axioms"]["sample"]) - lean_check.ALLOWED_AXIOMS


@pytest.mark.skipif(not INSTALLED, reason="installed Lean required")
def test_real_checker_missing_theorem_and_deadline(tmp_path):
    source = tmp_path / "Simple.lean"
    source.write_text("theorem actual : (1 : Nat) = 1 := rfl\n")
    missing = lean_check.check(source, ["missing"], output=tmp_path / "missing")
    assert not missing["checked"]
    timeout = lean_check.check(source, ["actual"], output=tmp_path / "timeout", timeout=0.00001)
    assert timeout["status"] == "timeout"
    assert not timeout["checked"]


@pytest.mark.skipif(not INSTALLED, reason="installed Lean required")
def test_real_checker_large_theorem_batch(tmp_path):
    names = [f"batch_{i}" for i in range(80)]
    source = tmp_path / "Batch.lean"
    source.write_text("\n".join(f"theorem {name} : True := True.intro" for name in names) + "\n")
    result = lean_check.check(source, names, output=tmp_path / "batch")
    assert result["checked"], (tmp_path / "batch/audit.log").read_text()
    assert set(result["axioms"]) == set(names)
    assert all(not dependencies for dependencies in result["axioms"].values())


@pytest.mark.skipif(not INSTALLED, reason="installed Lean required")
def test_checker_pins_sysroot_despite_caller_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAN_SYSROOT", str(tmp_path / "untrusted-sysroot"))
    monkeypatch.setenv("LEAN_PATH", str(tmp_path / "untrusted-modules"))
    source = tmp_path / "Ring.lean"
    source.write_text(
        "import Mathlib.Tactic.Ring\ntheorem sample (x : Rat) : x + 0 = x := by ring\n"
    )
    result = lean_check.check(source, ["sample"], output=tmp_path / "checked")
    assert result["checked"], result
    assert set(result["axioms"]["sample"]) <= lean_check.ALLOWED_AXIOMS
