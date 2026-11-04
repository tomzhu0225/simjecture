"""Exact solver properties and provenance of the checked optimality record."""

import hashlib
import importlib.util
import json
import shutil
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos/lean_poisson"
spec = importlib.util.spec_from_file_location("poisson_demo", DEMO / "poisson.py")
poisson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poisson)


def test_exact_solve_against_independent_elimination_and_counterexample():
    result = poisson.exact_checks()
    assert len(result["cases"]) == 39
    assert result["negative_control"]["residual"] == ["1"]
    assert poisson.solve([Fraction(1)]) == [Fraction(1, 2)]


def test_record_matches_proofs_and_executed_sources():
    proof = json.loads((DEMO / "record/proof.json").read_text())
    assert proof["checked"]
    assert (
        hashlib.sha256((DEMO / "Optimality.lean").read_bytes()).hexdigest()
        == proof["source_sha256"]
    )
    for name in ["Audit.lean", "audit.log", "compile.log"]:
        assert (
            hashlib.sha256((DEMO / "record" / name).read_bytes()).hexdigest()
            == proof["artifact_sha256"][name]
        )
    for name, expected in json.loads((DEMO / "record/source-hashes.json").read_text()).items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == expected
    measurements = json.loads((DEMO / "record/measurements.json").read_text())
    for case in measurements["exact"]["cases"]:
        rhs = list(map(Fraction, case["rhs"]))
        assert list(map(str, poisson.solve(rhs))) == case["solution"]
        assert sum(case["counts"].values()) == 11 * case["n"] + 6
    assert measurements["timings"][-1]["meets_backward_error_target"] is False


@pytest.mark.skipif(
    not (ROOT / ".runtime/lean-4.24.0/share/build-record.json").is_file()
    or not shutil.which("bwrap"),
    reason="installed Lean and sandbox required",
)
def test_poisson_optimality_checks_in_real_capability(tmp_path):
    from conjecture_solver.mvp_agent import BubblewrapSandbox, MVPAgentConfig
    from conjecture_solver.mvp_skills import MVPCapabilityRegistry

    for name in ["check_proof.py", "Optimality.lean"]:
        shutil.copy2(DEMO / name, tmp_path / name)
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
    result = sandbox.run_capability("lean-4.24.0", ("check_proof.py",), timeout_seconds=120)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / "proof.json").read_text())
    assert report["checked"]
    assert "Poisson.work_optimal" in report["axioms"]
