from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from conjecture_solver.cli import build_parser
from conjecture_solver.engineering import (
    EngineeringAdjudicationStatus,
    EngineeringCampaign,
    EngineeringCheck,
    EngineeringCheckStage,
    EngineeringCheckStatus,
    EngineeringContract,
    EngineeringError,
    EngineeringHoldoutContract,
    EngineeringPatchStatus,
)
from conjecture_solver.engineering_agent import (
    EngineeringAgentConfig,
    EngineeringAgentRunner,
    EngineeringFileEdit,
    EngineeringPatchProposal,
)
from conjecture_solver.llm import CompletionResult, ModelRoute


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
    adjudicate = build_parser().parse_args(
        [
            "engineering",
            "adjudicate",
            "campaign",
            "patch-001",
            "--holdout",
            "holdout.json",
            "--assert-accepted",
        ]
    )
    assert adjudicate.engineering_action == "adjudicate"
    assert adjudicate.assert_accepted is True

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


def _holdout(
    campaign: EngineeringCampaign,
    *,
    expected: str = "VALUE = 2\n",
) -> EngineeringHoldoutContract:
    return EngineeringHoldoutContract(
        holdout_id="hidden-value-case",
        campaign_id=campaign.contract.campaign_id,
        repository=campaign.contract.repository,
        base_commit=campaign.contract.base_commit or "",
        checks=(
            EngineeringCheck(
                name="hidden-value-contract",
                stage=EngineeringCheckStage.HOLDOUT,
                command=(
                    sys.executable,
                    "-c",
                    (
                        "from pathlib import Path; "
                        "raise SystemExit(0 if Path('src/value.py').read_text() "
                        f"== {expected!r} else 1)"
                    ),
                ),
                timeout_seconds=10,
            ),
        ),
    )


def test_external_holdout_and_diff_judge_accept_only_the_exact_candidate(
    tmp_path: Path,
) -> None:
    repository = _target_repository(tmp_path)
    campaign = EngineeringCampaign.create(_contract(repository), tmp_path / "campaign")
    patch = campaign.create_patch(
        "patch-001",
        diagnosis="The implementation returns the old constant.",
        prediction="Changing the constant to two satisfies the visible contract.",
    )
    Path(patch.worktree, "src/value.py").write_text("VALUE = 2\n")
    visible = campaign.validate_patch("patch-001", commit_message="fix value contract")
    assert visible.status is EngineeringPatchStatus.VALIDATED

    adjudication = campaign.adjudicate_patch("patch-001", _holdout(campaign))
    assert adjudication.status is EngineeringAdjudicationStatus.ACCEPTED
    assert adjudication.diff_review.status.value == "accepted"
    assert adjudication.checks[0].status is EngineeringCheckStatus.PASSED
    assert campaign.status()["patches"][0]["status"] == "accepted"
    assert campaign.status()["adjudications"][0]["status"] == "accepted"

    with pytest.raises(EngineeringError, match="already has an adjudication"):
        campaign.adjudicate_patch("patch-001", _holdout(campaign))


def test_holdout_failure_becomes_a_counterexample(tmp_path: Path) -> None:
    repository = _target_repository(tmp_path)
    campaign = EngineeringCampaign.create(_contract(repository), tmp_path / "campaign")
    patch = campaign.create_patch(
        "patch-001",
        diagnosis="Try the visible-contract candidate.",
        prediction="The visible pass generalizes to the withheld case.",
    )
    Path(patch.worktree, "src/value.py").write_text("VALUE = 2\n")
    assert campaign.validate_patch("patch-001", commit_message="visible candidate").status == (
        EngineeringPatchStatus.VALIDATED
    )

    adjudication = campaign.adjudicate_patch(
        "patch-001",
        _holdout(campaign, expected="VALUE = 99\n"),
    )
    assert adjudication.status is EngineeringAdjudicationStatus.COUNTEREXAMPLE
    assert adjudication.failure_reason == "holdout check failed: hidden-value-contract (failed)"
    assert campaign.status()["patches"][0]["status"] == "counterexample"


def test_diff_judge_rejects_mutation_after_visible_validation(tmp_path: Path) -> None:
    repository = _target_repository(tmp_path)
    campaign = EngineeringCampaign.create(_contract(repository), tmp_path / "campaign")
    patch = campaign.create_patch(
        "patch-001",
        diagnosis="Apply the candidate implementation.",
        prediction="The candidate remains unchanged while it is reviewed.",
    )
    Path(patch.worktree, "src/value.py").write_text("VALUE = 2\n")
    assert campaign.validate_patch("patch-001", commit_message="candidate").status == (
        EngineeringPatchStatus.VALIDATED
    )
    # Simulate a compromised or stale worker changing the worktree after CI.
    Path(patch.worktree, "src/value.py").write_text("VALUE = 3\n")

    adjudication = campaign.adjudicate_patch("patch-001", _holdout(campaign))
    assert adjudication.status is EngineeringAdjudicationStatus.REJECTED
    assert not adjudication.checks
    assert "worktree is not clean" in (adjudication.failure_reason or "")


def test_holdout_contract_is_external_and_stage_restricted(tmp_path: Path) -> None:
    repository = _target_repository(tmp_path)
    contract = _contract(repository)
    with pytest.raises(ValueError, match="holdout checks must be supplied"):
        EngineeringContract(
            campaign_id=contract.campaign_id,
            goal=contract.goal,
            repository=contract.repository,
            editable_paths=contract.editable_paths,
            protected_paths=contract.protected_paths,
            checks=(
                EngineeringCheck(
                    name="visible-but-hidden",
                    stage=EngineeringCheckStage.HOLDOUT,
                    command=("true",),
                ),
            ),
        )
    with pytest.raises(ValueError, match="every external holdout"):
        EngineeringHoldoutContract(
            holdout_id="bad-holdout",
            campaign_id="engineering-test",
            repository=str(repository),
            base_commit=_git(repository, "rev-parse", "HEAD"),
            checks=(contract.checks[0],),
        )


def test_validation_rejects_a_check_that_moves_worktree_head(tmp_path: Path) -> None:
    repository = _target_repository(tmp_path)
    contract = _contract(repository).model_copy(
        update={
            "checks": (
                EngineeringCheck(
                    name="sneaky-commit",
                    command=(
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('src/value.py').write_text('VALUE = 4\\n')",
                    ),
                ),
                EngineeringCheck(
                    name="sneaky-commit-2",
                    command=(
                        "git",
                        "add",
                        "src/value.py",
                    ),
                ),
                EngineeringCheck(
                    name="sneaky-commit-3",
                    command=(
                        "git",
                        "-c",
                        "user.name=check",
                        "-c",
                        "user.email=check@example.invalid",
                        "commit",
                        "-m",
                        "sneaky",
                    ),
                ),
            )
        }
    )
    campaign = EngineeringCampaign.create(contract, tmp_path / "campaign")
    patch = campaign.create_patch(
        "patch-001",
        diagnosis="Exercise commit-integrity protection.",
        prediction="A validation command must not replace the candidate commit.",
    )
    Path(patch.worktree, "src/value.py").write_text("VALUE = 2\n")
    result = campaign.validate_patch("patch-001", commit_message="candidate")
    assert result.status is EngineeringPatchStatus.REJECTED
    assert "changed the worktree HEAD" in (result.failure_reason or "")


class _ProposalClient:
    def __init__(self, proposals: list[EngineeringPatchProposal]) -> None:
        self.proposals = proposals
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]], **_kwargs: object) -> CompletionResult:
        self.calls.append(messages)
        proposal = self.proposals.pop(0)
        return CompletionResult(
            request_id=f"fixture-{len(self.calls)}",
            model="fixture-model",
            content=proposal.model_dump_json(),
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 10},
            route=ModelRoute.DEFAULT,
            route_reason="fixture",
        )


def _write_proposal(snapshot: str, value: int) -> EngineeringPatchProposal:
    return EngineeringPatchProposal(
        diagnosis=f"The current implementation contains the wrong value before attempt {value}.",
        prediction=f"Replacing the value with {value} will satisfy the visible contract.",
        commit_message=f"set value to {value}",
        edits=(
            EngineeringFileEdit(
                path="src/value.py",
                content=f"VALUE = {value}\n",
                expected_sha256=hashlib.sha256(snapshot.encode()).hexdigest(),
            ),
        ),
    )


def test_engineering_agent_runs_structured_edit_loop_to_acceptance(tmp_path: Path) -> None:
    repository = _target_repository(tmp_path)
    campaign = EngineeringCampaign.create(_contract(repository), tmp_path / "campaign")
    client = _ProposalClient([_write_proposal("VALUE = 1\n", 2)])

    report = EngineeringAgentRunner(
        campaign,
        client,
        config=EngineeringAgentConfig(max_attempts=2, max_wall_seconds=30),
    ).run(holdout=_holdout(campaign))

    assert report.status.value == "accepted"
    assert report.selected_patch_id == "patch-001"
    assert report.attempts[0].status.value == "accepted"
    assert campaign.status()["agent"]["status"] == "accepted"
    prompt = json.loads(client.calls[0][1]["content"])
    assert prompt["source_snapshot"]["src/value.py"] == "VALUE = 1\n"
    assert prompt["source_snapshot_sha256"]["src/value.py"] == hashlib.sha256(
        b"VALUE = 1\n"
    ).hexdigest()
    assert "hidden-value-case" not in client.calls[0][1]["content"]
    assert (campaign.output / "agent.json").is_file()
    with pytest.raises(EngineeringError, match="different holdout"):
        EngineeringAgentRunner(campaign, client).run(
            holdout=_holdout(campaign, expected="VALUE = 99\n")
        )


def test_engineering_agent_uses_a_visible_counterexample_to_make_a_child(
    tmp_path: Path,
) -> None:
    repository = _target_repository(tmp_path)
    campaign = EngineeringCampaign.create(_contract(repository), tmp_path / "campaign")
    client = _ProposalClient(
        [
            _write_proposal("VALUE = 1\n", 3),
            _write_proposal("VALUE = 3\n", 2),
        ]
    )

    report = EngineeringAgentRunner(
        campaign,
        client,
        config=EngineeringAgentConfig(max_attempts=3, max_wall_seconds=30),
    ).run(holdout=_holdout(campaign))

    assert report.status.value == "accepted"
    assert [item.patch_id for item in report.attempts] == ["patch-001", "patch-002"]
    assert [item.status.value for item in report.attempts] == [
        "counterexample",
        "accepted",
    ]
    child = campaign.status()["patches"][1]
    assert child["parent_patch_id"] == "patch-001"
    second_prompt = json.loads(client.calls[1][1]["content"])
    assert second_prompt["source_snapshot"]["src/value.py"] == "VALUE = 3\n"


def test_engineering_agent_rejects_unsafe_edit_paths() -> None:
    with pytest.raises(ValueError, match="safe POSIX-relative"):
        EngineeringFileEdit(path="../secret.py", content="SECRET = 1\n")


def test_engineering_agent_cli_parser_accepts_agent_run() -> None:
    parsed = build_parser().parse_args(
        ["engineering", "agent-run", "campaign", "--max-attempts", "3"]
    )
    assert parsed.engineering_action == "agent-run"
    assert parsed.max_attempts == 3
