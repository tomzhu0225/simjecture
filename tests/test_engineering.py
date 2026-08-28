from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conjecture_solver.cli import build_parser
from conjecture_solver.engineering import (
    EngineeringCampaign,
    EngineeringCheck,
    EngineeringCheckStage,
    EngineeringCheckStatus,
    EngineeringContract,
    EngineeringError,
    EngineeringPatchStatus,
)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _target_repository(tmp_path: Path) -> Path:
    root = tmp_path / "target"
    root.mkdir()
    _git(root, "init", "--quiet")
    _git(root, "config", "user.name", "Simjecture test")
    _git(root, "config", "user.email", "simjecture-test@example.invalid")
    (root / "src").mkdir()
    (root / "src/value.py").write_text("VALUE = 1\n")
    (root / "tests").mkdir()
    (root / "tests/README.md").write_text("Protected acceptance tests.\n")
    _git(root, "add", "--all")
    _git(root, "commit", "--quiet", "-m", "initial")
    return root


def _contract(
    root: Path,
    *,
    check_stage: EngineeringCheckStage = EngineeringCheckStage.FULL,
) -> EngineeringContract:
    check = EngineeringCheck(
        name="value-contract",
        stage=check_stage,
        command=(
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "raise SystemExit(0 if Path('src/value.py').read_text() == 'VALUE = 2\\n' else 1)"
            ),
        ),
        timeout_seconds=10,
    )
    return EngineeringContract(
        campaign_id="engineering-test",
        goal="Make the value implementation return two.",
        repository=str(root),
        editable_paths=("src/**",),
        protected_paths=("tests/**",),
        checks=(check,),
    )


def test_engineering_campaign_commissions_and_validates_a_patch(tmp_path: Path) -> None:
    repository = _target_repository(tmp_path)
    campaign = EngineeringCampaign.create(_contract(repository), tmp_path / "campaign")

    commission = campaign.commission()
    assert commission[0].status is EngineeringCheckStatus.FAILED
    assert (campaign.output / "commission.json").is_file()
    with pytest.raises(EngineeringError, match="already recorded"):
        campaign.commission()

    patch = campaign.create_patch(
        "patch-001",
        diagnosis="The implementation returns the old constant.",
        prediction="Changing the constant to two will satisfy the contract.",
    )
    Path(patch.worktree, "src/value.py").write_text("VALUE = 2\n")

    validated = campaign.validate_patch("patch-001", commit_message="fix value contract")
    assert validated.status is EngineeringPatchStatus.VALIDATED
    assert validated.commit is not None
    assert validated.diff_sha256 is not None
    assert validated.checks[0].status is EngineeringCheckStatus.PASSED
    assert (campaign.output / "evidence/patch-001.json").is_file()
    assert _git(repository, "show", "-s", "--format=%s", validated.commit) == "fix value contract"

    snapshot = EngineeringCampaign.load(campaign.output).status()
    assert snapshot["base_commit"] == campaign.contract.base_commit
    assert snapshot["patches"][0]["status"] == "validated"


def test_failed_patch_is_a_counterexample_and_child_starts_from_its_commit(
    tmp_path: Path,
) -> None:
    repository = _target_repository(tmp_path)
    campaign = EngineeringCampaign.create(_contract(repository), tmp_path / "campaign")

    first = campaign.create_patch(
        "patch-001",
        diagnosis="Try a candidate constant.",
        prediction="The candidate should satisfy the value contract.",
    )
    Path(first.worktree, "src/value.py").write_text("VALUE = 3\n")
    failed = campaign.validate_patch("patch-001", commit_message="try value three")
    assert failed.status is EngineeringPatchStatus.COUNTEREXAMPLE
    assert failed.failure_reason == "check failed: value-contract (failed)"

    child = campaign.create_patch(
        "patch-002",
        diagnosis="The counterexample shows that three is not sufficient.",
        prediction="A child patch using two should pass the same contract.",
        parent_patch_id="patch-001",
    )
    assert child.parent_commit == failed.commit
    Path(child.worktree, "src/value.py").write_text("VALUE = 2\n")
    repaired = campaign.validate_patch("patch-002", commit_message="repair value contract")
    assert repaired.status is EngineeringPatchStatus.VALIDATED
    assert repaired.parent_patch_id == "patch-001"


def test_protected_path_change_is_rejected_without_a_commit(tmp_path: Path) -> None:
    repository = _target_repository(tmp_path)
    campaign = EngineeringCampaign.create(_contract(repository), tmp_path / "campaign")
    patch = campaign.create_patch(
        "protected-attempt",
        diagnosis="Try changing the acceptance test.",
        prediction="The test would pass after weakening it.",
    )
    Path(patch.worktree, "tests/README.md").write_text("Changed acceptance boundary.\n")

    rejected = campaign.validate_patch("protected-attempt", commit_message="must reject")
    assert rejected.status is EngineeringPatchStatus.REJECTED
    assert rejected.commit is None
    assert "protected paths changed: tests/README.md" in (rejected.failure_reason or "")
    assert _git(Path(patch.worktree), "rev-parse", "HEAD") == campaign.contract.base_commit


def test_contract_and_cli_keep_engineering_commands_structured(tmp_path: Path) -> None:
    repository = _target_repository(tmp_path)
    contract = _contract(repository)
    assert all("\x00" not in argument for argument in contract.checks[0].command)
    parsed = build_parser().parse_args(
        ["engineering", "patch-validate", "campaign", "patch-001", "--message", "fix"]
    )
    assert parsed.engineering_action == "patch-validate"
    assert parsed.assert_passed is False

    with pytest.raises(ValueError, match="editable and protected"):
        EngineeringContract(
            campaign_id="bad-contract",
            goal="overlap",
            repository=str(repository),
            editable_paths=("tests/**",),
            protected_paths=("tests/**",),
            checks=contract.checks,
        )


def test_check_timeout_is_recorded_as_a_counterexample(tmp_path: Path) -> None:
    repository = _target_repository(tmp_path)
    contract = _contract(repository).model_copy(
        update={
            "checks": (
                EngineeringCheck(
                    name="timeout",
                    command=(sys.executable, "-c", "import time; time.sleep(1)"),
                    timeout_seconds=0.05,
                ),
            )
        }
    )
    campaign = EngineeringCampaign.create(contract, tmp_path / "campaign")
    patch = campaign.create_patch(
        "timeout-patch",
        diagnosis="Exercise timeout handling.",
        prediction="The command should be recorded as a timed-out counterexample.",
    )
    Path(patch.worktree, "src/value.py").write_text("VALUE = 2\n")
    result = campaign.validate_patch("timeout-patch", commit_message="timeout probe")
    assert result.status is EngineeringPatchStatus.COUNTEREXAMPLE
    assert result.checks[0].status is EngineeringCheckStatus.TIMED_OUT


def test_campaign_cannot_be_started_inside_target_repository(tmp_path: Path) -> None:
    repository = _target_repository(tmp_path)
    with pytest.raises(EngineeringError, match="must not be inside"):
        EngineeringCampaign.create(_contract(repository), repository / ".simjecture")
