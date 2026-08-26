from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from conjecture_solver.campaign_jobs import (
    KERNEL_WORKER_SCHEMA_VERSION,
    CampaignInterprocessLock,
    CampaignJobStatus,
    CampaignJobSupervisor,
    JobConflictError,
    kernel_worker_request_sha256,
)
from conjecture_solver.campaign_kernel import (
    CampaignBudgetExceededError,
    CampaignKernel,
    CampaignOperationFailedError,
    CampaignWriterBusyError,
)
from conjecture_solver.kernel_worker import execute_worker_request
from conjecture_solver.literature import LiteratureSearchRecord, LiteratureSearchStatus
from conjecture_solver.models import utc_now
from conjecture_solver.mvp_agent import (
    MVPActionKind,
    MVPAgentRunner,
    MVPListSkillsAction,
    MVPWriteFileAction,
    parse_mvp_action,
)
from conjecture_solver.mvp_launch import MVPLaunchRequest, materialize_operator_input


class _OfflineLiterature:
    identity = {
        "name": "public-literature-search",
        "version": "1",
        "providers": ["openalex", "crossref", "duckduckgo_html"],
        "network_location": "host",
        "sandbox_network_enabled": False,
        "credentials_required": False,
    }

    def search(
        self,
        *,
        hypothesis: str,
        query: str,
        purpose: str,
        max_results: int,
    ) -> LiteratureSearchRecord:
        return LiteratureSearchRecord(
            id="literature_search_" + hashlib.sha256(query.encode()).hexdigest()[:16],
            hypothesis_sha256=hashlib.sha256(hypothesis.encode()).hexdigest(),
            query=query,
            purpose=purpose,
            requested_results=max_results,
            status=LiteratureSearchStatus.UNAVAILABLE,
            provider_status={"offline": "unavailable"},
            searched_at=utc_now(),
        )


def _prepare_startup(kernel: CampaignKernel) -> None:
    """Satisfy the mandatory startup gate without network access in tests."""

    kernel.host.literature_search = _OfflineLiterature()
    kernel.execute(
        {
            "action": "search_literature",
            "research_note": "bounded startup reconnaissance",
            "query": "kernel startup",
            "purpose": "satisfy startup reconnaissance before action execution",
            "max_results": 1,
        },
        iteration=0,
    )


class _Host:
    hypothesis = "A kernel must preserve the action boundary."
    manifest_path = "manifest.json"
    artifact_provenance_path = "artifact_provenance.json"
    skills = type("Skills", (), {"hashes": {"demo": "a" * 64}})()
    capabilities = type("Capabilities", (), {"hashes": {"demo": "b" * 64}})()
    _artifact_provenance = {"schema_version": "0.1.0", "artifacts": {}}
    _literature_searches: list[Any] = []

    class _Claims:
        class _Ledger:
            @staticmethod
            def compact_summary(*, max_claims: int = 24) -> dict[str, str]:
                del max_claims
                return {"status": "ready"}

        ledger = _Ledger()

    claim_store = _Claims()

    def __init__(self) -> None:
        self.initialized = 0
        self.recovered = 0
        self.gate_calls = 0
        self.compat_calls: list[tuple[Any, int]] = []

    def _initialize(self) -> None:
        self.initialized += 1

    def _recover_interrupted_action(self) -> None:
        self.recovered += 1

    def _enforce_literature_startup(self, _action: Any) -> None:
        self.gate_calls += 1

    def _perform_compat(self, action: Any, *, iteration: int, **_kwargs: Any) -> dict[str, Any]:
        self.compat_calls.append((action, iteration))
        return {"executed": action.action.value, "iteration": iteration}

    @staticmethod
    def _manifest() -> dict[str, str]:
        return {"schema_version": "0.20.0", "identity": "stable"}


def test_kernel_open_snapshot_and_execute_are_model_neutral() -> None:
    host = _Host()
    kernel = CampaignKernel.open(host)
    assert host.initialized == 1
    assert kernel.snapshot()["manifest"]["identity"] == "stable"
    assert kernel.snapshot()["claim_ledger"] == {"status": "ready"}

    action = MVPListSkillsAction(
        action=MVPActionKind.LIST_SKILLS,
        research_note="Inspect the installed capability surface.",
    )
    result = kernel.execute(action, iteration=3, timeout_seconds=1)
    assert result == {"executed": "list_skills", "iteration": 3}
    assert host.gate_calls == 1
    assert host.compat_calls == [(action, 3)]


def test_kernel_recovery_is_explicit_and_does_not_invoke_model() -> None:
    host = _Host()
    kernel = CampaignKernel(host)
    kernel.recover_interrupted_action()
    assert host.recovered == 1
    assert not host.compat_calls


def test_existing_worker_open_reconstructs_before_taking_writer_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = tmp_path / "campaign"
    CampaignKernel.open(
        workspace=campaign,
        hypothesis="Worker reconstruction must not block campaign status.",
    )
    original = CampaignKernel._build_standalone_host
    observed = {"construction_lock_available": False}

    def checked_build(**kwargs: Any) -> Any:
        # This would fail if open_existing still held its outer campaign lock
        # around the expensive host/ledger reconstruction.
        with CampaignInterprocessLock(campaign):
            observed["construction_lock_available"] = True
        return original(**kwargs)

    monkeypatch.setattr(
        CampaignKernel,
        "_build_standalone_host",
        staticmethod(checked_build),
    )
    reopened = CampaignKernel.open_existing(workspace=campaign)
    assert reopened.hypothesis == "Worker reconstruction must not block campaign status."
    assert observed["construction_lock_available"] is True


def test_existing_worker_open_refuses_an_incomplete_campaign(tmp_path: Path) -> None:
    campaign = tmp_path / "partial"
    campaign.mkdir()
    with pytest.raises(ValueError, match="missing initialized file"):
        CampaignKernel.open_existing(workspace=campaign)


def test_existing_dsh_campaign_ignores_only_native_prompt_hash_drift(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "dsh-campaign"
    materialize_operator_input(
        MVPLaunchRequest(
            campaign_id="dsh_prompt_compatibility",
            hypothesis="DSH role prompts are external to the native runner prompt.",
            output_directory=str(campaign),
            engine="dsh",
        )
    )
    CampaignKernel.open(workspace=campaign)
    manifest_path = campaign / "mvp_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["system_prompt_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    reopened = CampaignKernel.open_existing(workspace=campaign)

    assert reopened.hypothesis == (
        "DSH role prompts are external to the native runner prompt."
    )


def test_existing_native_campaign_rejects_native_prompt_hash_drift(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "native-campaign"
    materialize_operator_input(
        MVPLaunchRequest(
            campaign_id="native_prompt_compatibility",
            hypothesis="Native campaigns retain an exact prompt identity.",
            output_directory=str(campaign),
            engine="native",
        )
    )
    CampaignKernel.open(workspace=campaign)
    manifest_path = campaign / "mvp_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["system_prompt_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    with pytest.raises(ValueError, match="different run contract"):
        CampaignKernel.open_existing(workspace=campaign)


def test_execute_operation_allocates_sequence_replays_exactly_and_enforces_budget(
    tmp_path: Path,
) -> None:
    host = _Host()
    host.output = tmp_path / "campaign"
    host.config = SimpleNamespace(
        max_iterations=2,
        max_wall_seconds=60.0,
        max_command_seconds=3.0,
    )
    host.operation_calls: list[tuple[int, float]] = []

    def perform(
        action: Any,
        *,
        iteration: int,
        timeout_seconds: float,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        host.operation_calls.append((iteration, timeout_seconds))
        return {"executed": action.action.value, "iteration": iteration}

    host._perform_compat = perform
    kernel = CampaignKernel.open(host)
    action = {
        "action": "list_skills",
        "research_note": "allocate a durable action sequence",
    }
    first = kernel.execute_operation("operation-one", action, timeout_seconds=30)
    replay = kernel.execute_operation("operation-one", action, timeout_seconds=30)
    assert replay == first
    assert host.operation_calls == [(1, 3.0)]
    kernel.execute_operation(
        "operation-two",
        {"action": "list_files", "research_note": "second sequence", "path": "."},
    )
    assert host.operation_calls[-1][0] == 2
    with pytest.raises(CampaignBudgetExceededError, match="action budget"):
        kernel.execute_operation(
            "operation-three",
            {"action": "list_claims", "research_note": "budget exhausted"},
        )
    with pytest.raises(JobConflictError, match="different action"):
        kernel.execute_operation(
            "operation-one",
            {"action": "list_claims", "research_note": "conflicting replay"},
            timeout_seconds=30,
        )
    journal = json.loads((host.output / "action_journal.json").read_text())
    assert journal["operations"]["operation-one"]["sequence"] == 1


def test_failed_operation_replay_never_executes_again(tmp_path: Path) -> None:
    host = _Host()
    host.output = tmp_path / "campaign"
    host.config = SimpleNamespace(
        max_iterations=None,
        max_wall_seconds=60.0,
        max_command_seconds=3.0,
    )
    calls = 0

    def fail_once(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise RuntimeError("durable failure")

    host._perform_compat = fail_once
    kernel = CampaignKernel.open(host)
    action = {
        "action": "list_skills",
        "research_note": "Record and replay one failed operation.",
    }
    with pytest.raises(RuntimeError, match="durable failure"):
        kernel.execute_operation("failed-operation", action)
    with pytest.raises(CampaignOperationFailedError, match="durable failure") as replay:
        kernel.execute_operation("failed-operation", action)
    assert "new operation_id" in str(replay.value)
    assert "cannot be rerun" in str(replay.value)
    assert calls == 1


def test_kernel_open_constructs_a_real_model_free_campaign(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A model-free kernel can execute a bounded workspace action.",
    )
    assert kernel.host.literature_search is not None
    _prepare_startup(kernel)
    assert (campaign / "mvp_manifest.json").is_file()
    action = MVPWriteFileAction(
        action=MVPActionKind.WRITE_FILE,
        research_note="Create a durable kernel probe artifact.",
        path="probe.json",
        content='{"ok":true}\n',
    )
    result = kernel.execute(action, iteration=1)
    assert result["path"] == "probe.json"
    assert (campaign / "workspace" / "probe.json").read_text() == '{"ok":true}'


def test_model_free_kernel_adjudicates_and_finalizes_without_completion_client(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "dsh-lifecycle"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="Every member of the declared bounded ensemble passes.",
    )
    _prepare_startup(kernel)
    kernel.execute_operation(
        "contract-root-v1",
        {
            "action": "register_evidence_contract",
            "research_note": "Freeze the bounded ensemble criterion prospectively.",
            "claim_id": "claim_root",
            "observable": "A deterministic ensemble pass flag.",
            "expected_outcomes": "True supports the claim; false challenges it.",
            "decision_rule": "Support exactly when ensemble_pass is true.",
            "required_observation": "Evaluate every member of the declared ensemble.",
            "uncertainty_criterion": "Every declared member must pass independently.",
            "inconclusive_conditions": "Any missing ensemble member is inconclusive.",
            "validation_checks": [{"json_path": "ensemble_pass", "expected_value": True}],
            "additional_execution_bindings": [],
        },
    )
    kernel.execute_operation(
        "write-root-evidence",
        {
            "action": "run_python",
            "research_note": "Generate the complete prospective ensemble result.",
            "argv": [
                "-c",
                "import json; from pathlib import Path; "
                "Path('ensemble.json').write_text(json.dumps("
                "{'ensemble_pass': True, 'members': 12}))",
            ],
            "active_claim_id": "claim_root",
        },
    )
    kernel.execute_operation(
        "link-root-evidence",
        {
            "action": "link_claim_evidence",
            "research_note": "Link the complete bounded ensemble result.",
            "claim_id": "claim_root",
            "path": "ensemble.json",
            "note": "All twelve prospectively declared members passed.",
            "observation_sufficient": True,
            "observation_note": "All declared members and the exact pass flag are present.",
        },
    )
    case = "The complete twelve-member prospective ensemble passed with no missing runs."
    prepared = kernel.prepare_adjudication(
        "judge-root-v1",
        claim_id="claim_root",
        contract_version=1,
        case_for_sufficiency=case,
    )
    assert prepared["already_recorded"] is False
    assert "evidence_contracts" not in prepared["packet"]["claim"]
    assert "evidence" not in prepared["packet"]["claim"]
    assert prepared["packet"]["claim"]["evidence_contract_count"] == 1
    assert prepared["packet"]["claim"]["evidence_count"] == 1
    result = kernel.record_adjudication(
        "judge-root-v1",
        claim_id="claim_root",
        contract_version=1,
        case_for_sufficiency=case,
        case_sha256=prepared["case_sha256"],
        verdict={
            "claim_id": "claim_root",
            "contract_version": 1,
            "decision": "sufficient",
            "scientific_disposition": "supported",
            "claim_tested": True,
            "contract_preserves_claim_semantics": True,
            "rationale": (
                "The complete bounded ensemble and exact validation satisfy the contract."
            ),
            "evidence_gaps": [],
            "next_test": None,
        },
        model="deepseek-chat",
        route="dsh-subagent:deepseek-official",
        judge_run_id="judge-child-session",
        usage={"totalTokens": 100},
    )
    assert result["closure"]["closed"]["status"] == "supported"
    # Simulate a process loss after adjudication/closure persistence but before
    # the final action-journal receipt. Preparation must reconcile, not spawn a
    # second judge or leave the operation permanently in progress.
    journal_path = campaign / "action_journal.json"
    journal = json.loads(journal_path.read_text())
    journal["operations"]["judge-root-v1"]["status"] = "running"
    journal["operations"]["judge-root-v1"].pop("result")
    journal_path.write_text(json.dumps(journal))
    replay = kernel.prepare_adjudication(
        "judge-root-v1",
        claim_id="claim_root",
        contract_version=1,
        case_for_sufficiency=case,
    )
    assert replay["already_recorded"] is True
    assert (
        json.loads(journal_path.read_text())["operations"]["judge-root-v1"]["status"] == "succeeded"
    )

    report = kernel.finalize_campaign(
        "finish-root-v1",
        final_answer="The declared bounded ensemble supports the root claim.",
    )
    assert report["status"] == "completed"
    assert report["final_answer"].startswith("The declared bounded ensemble")
    assert (campaign / "mvp_report.json").is_file()
    assert (
        kernel.finalize_campaign(
            "finish-root-v1",
            final_answer="The declared bounded ensemble supports the root claim.",
        )
        == report
    )
    adjudications = json.loads((campaign / "adjudications.json").read_text())
    assert adjudications[0]["operation_id"] == "judge-root-v1"


def test_kernel_materializes_receipt_backed_terminal_observation(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "terminal-observation"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A bounded scientific execution produces the required observation.",
    )
    _prepare_startup(kernel)
    kernel.execute_operation(
        "contract-root-v1",
        {
            "action": "register_evidence_contract",
            "research_note": "Freeze the scientific decision attempt.",
            "claim_id": "claim_root",
            "observable": "A complete bounded result.",
            "expected_outcomes": "A complete result decides; failure is inconclusive.",
            "decision_rule": "Decide only from a complete successful result.",
            "required_observation": "One complete successful result.",
            "uncertainty_criterion": "The result must contain every declared field.",
            "inconclusive_conditions": "Execution failure is inconclusive.",
            "validation_checks": [],
        },
    )
    state = kernel.start_job(
        {
            "operation_id": "failed-root-attempt",
            "kind": "python",
            "argv": [
                "-c",
                "from pathlib import Path; "
                "Path('failed_attempt.json').write_text('{\"complete\":false}'); "
                "raise SystemExit(7)",
            ],
            "active_claim_id": "claim_root",
            "input_artifacts": [],
            "timeout_seconds": 30,
        }
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = kernel.job_status(state.job_id)
        if state.status.terminal:
            break
        time.sleep(0.02)
    assert state.status is CampaignJobStatus.FAILED
    kernel.execute_operation(
        "link-failed-root-attempt",
        {
            "action": "link_claim_evidence",
            "research_note": "Record the failed prospective attempt without deciding science.",
            "claim_id": "claim_root",
            "path": "failed_attempt.json",
            "note": "The prospective execution failed before the required observation.",
            "observation_sufficient": False,
            "observation_note": "This is an attempt record, not a scientific result.",
        },
    )
    kernel.execute_operation(
        "contract-root-terminal-v2",
        {
            "action": "register_evidence_contract",
            "research_note": "Prospectively freeze the terminal receipt record.",
            "claim_id": "claim_root",
            "evidence_purpose": "terminal_record",
            "observable": "A kernel-authenticated terminal execution record.",
            "expected_outcomes": "A complete record permits independent terminal review.",
            "decision_rule": "Accept only a complete record tied to the failed job receipt.",
            "required_observation": "One receipt-backed terminal JSON record.",
            "uncertainty_criterion": "Job and receipt identities must be kernel verified.",
            "inconclusive_conditions": "Missing receipt identity is incomplete.",
            "validation_checks": [
                {"json_path": "record_complete", "expected_value": True},
                {
                    "json_path": "kernel_verified.selected_jobs_all_terminal",
                    "expected_value": True,
                },
            ],
        },
    )
    result = kernel.record_terminal_observation(
        "record-root-terminal-v2",
        claim_id="claim_root",
        contract_version=2,
        job_ids=[state.job_id],
        path="evidence/terminal_root_v2.json",
        alternatives_considered=[
            "A smaller execution would not realize the required complete observation."
        ],
        feasibility_assessment=(
            "No admissible alternative has yet been shown to realize the exact observation."
        ),
    )
    assert result["terminal_cause"] == "execution_or_instrument_failure"
    document = json.loads(
        (campaign / "workspace/evidence/terminal_root_v2.json").read_text()
    )
    assert document["record_complete"] is True
    assert document["kernel_verified"]["attempts"][0]["job_id"] == state.job_id
    assert document["kernel_verified"]["attempts"][0]["job_report_sha256"]
    assert document["researcher_assessment"]["verified_by_kernel"] is False
    provenance = json.loads((campaign / "artifact_provenance.json").read_text())[
        "artifacts"
    ]["evidence/terminal_root_v2.json"]
    assert provenance["action"] == "run_python"
    assert provenance["execution_succeeded"] is True
    assert provenance["evidence_eligible"] is True
    kernel.execute_operation(
        "link-root-terminal-v2",
        {
            "action": "link_claim_evidence",
            "research_note": "Link the prospective terminal observation for judgment.",
            "claim_id": "claim_root",
            "path": "evidence/terminal_root_v2.json",
            "note": "Kernel-authenticated job receipts and limits are complete.",
            "observation_sufficient": True,
            "observation_note": "The terminal record satisfies both registered checks.",
        },
    )
    prepared = kernel.prepare_adjudication(
        "judge-root-terminal-v2",
        claim_id="claim_root",
        contract_version=2,
        case_for_sufficiency=(
            "The fresh terminal record preserves the failed job receipt for review."
        ),
    )
    assert prepared["packet"]["selected_contract_evidence"][0]["path"] == (
        "evidence/terminal_root_v2.json"
    )


def test_kernel_rejects_adjudication_without_contract_satisfying_evidence(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "unqualified-adjudication"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A surviving observation is not automatically sufficient evidence.",
    )
    _prepare_startup(kernel)
    kernel.execute_operation(
        "contract-root-v1",
        {
            "action": "register_evidence_contract",
            "research_note": "Freeze the exact pass criterion.",
            "claim_id": "claim_root",
            "observable": "A deterministic pass flag.",
            "expected_outcomes": "True survives; false challenges the claim.",
            "decision_rule": "The observation satisfies the contract when passed is true.",
            "required_observation": "Produce one complete JSON result.",
            "uncertainty_criterion": "The exact Boolean has no sampling uncertainty.",
            "inconclusive_conditions": "A missing pass flag is inconclusive.",
            "validation_checks": [{"json_path": "passed", "expected_value": True}],
        },
    )
    kernel.execute_operation(
        "run-root-v1",
        {
            "action": "run_python",
            "research_note": "Generate the prospective observation.",
            "argv": [
                "-c",
                "import json; from pathlib import Path; "
                "Path('result.json').write_text(json.dumps({'passed': True}))",
            ],
            "active_claim_id": "claim_root",
        },
    )
    kernel.execute_operation(
        "link-root-v1",
        {
            "action": "link_claim_evidence",
            "research_note": "Link it without claiming that it meets the contract.",
            "claim_id": "claim_root",
            "path": "result.json",
            "note": "The artifact exists, but the caller marked it non-qualifying.",
            "observation_sufficient": False,
            "observation_note": "This link is intentionally not contract-satisfying.",
        },
    )

    with pytest.raises(ValueError, match="observation_sufficient=true"):
        kernel.prepare_adjudication(
            "judge-root-v1",
            claim_id="claim_root",
            contract_version=1,
            case_for_sufficiency="The observation survived the attempted falsification.",
        )

    assert not (campaign / "adjudications.json").exists()


def test_adjudication_rejects_stale_contract_with_newer_qualifying_evidence(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "stale-adjudication"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A prospectively measured value equals its declared target.",
    )
    _prepare_startup(kernel)

    def register(version: int) -> None:
        kernel.execute_operation(
            f"contract-v{version}",
            {
                "action": "register_evidence_contract",
                "research_note": f"Register prospective contract version {version}.",
                "claim_id": "claim_root",
                "observable": f"The exact integer result equals {version}.",
                "expected_outcomes": "Equality supports; inequality challenges.",
                "decision_rule": f"Support exactly when value equals {version}.",
                "required_observation": "Record one fresh deterministic result.",
                "uncertainty_criterion": "The exact integer has no sampling error.",
                "inconclusive_conditions": "A missing result is inconclusive.",
                "validation_checks": [{"json_path": "value", "expected_value": version}],
                "additional_execution_bindings": [],
            },
        )
        kernel.execute_operation(
            f"write-v{version}",
            {
                "action": "run_python",
                "research_note": f"Generate fresh evidence for contract {version}.",
                "argv": [
                    "-c",
                    "import json; from pathlib import Path; "
                    f"Path('value-v{version}.json').write_text(json.dumps("
                    f"{{'value': {version}}}))",
                ],
                "active_claim_id": "claim_root",
            },
        )
        kernel.execute_operation(
            f"link-v{version}",
            {
                "action": "link_claim_evidence",
                "research_note": f"Link fresh contract {version} evidence.",
                "claim_id": "claim_root",
                "path": f"value-v{version}.json",
                "note": f"The fresh result equals {version}.",
                "observation_sufficient": True,
                "observation_note": "The exact prospective validation check passes.",
            },
        )

    register(1)
    register(2)
    with pytest.raises(ValueError, match=r"contract v1 is stale; newer contract v2"):
        kernel.prepare_adjudication(
            "judge-stale-v1",
            claim_id="claim_root",
            contract_version=1,
            case_for_sufficiency="The obsolete first result passed its earlier contract.",
        )
    prepared = kernel.prepare_adjudication(
        "judge-current-v2",
        claim_id="claim_root",
        contract_version=2,
        case_for_sufficiency="The fresh second result passed the current contract.",
    )
    assert prepared["contract_version"] == 2


def test_kernel_worker_reopens_campaign_and_records_typed_artifact(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A detached worker must execute only a typed action.",
    )
    _prepare_startup(kernel)
    request = campaign / "kernel_jobs" / "worker.json"
    request.parent.mkdir()
    payload = {
        "schema_version": KERNEL_WORKER_SCHEMA_VERSION,
        "operation_id": "worker-probe",
        "campaign": str(campaign),
        "iteration": 2,
        "action": {
            "action": "write_file",
            "research_note": "Record one worker-created artifact.",
            "path": "worker.txt",
            "content": "worker",
        },
    }
    payload["worker_request_sha256"] = kernel_worker_request_sha256(payload)
    request.write_text(json.dumps(payload))
    result = execute_worker_request(request, campaign=campaign)
    assert result["ok"] is True
    assert (campaign / "workspace" / "worker.txt").read_text() == "worker"
    provenance = json.loads((campaign / "artifact_provenance.json").read_text())
    assert provenance["artifacts"]["worker.txt"]["action"] == "write_file"
    assert provenance["artifacts"]["worker.txt"]["generated_iteration"] == 1


def test_detached_worker_replays_custom_resource_roots(tmp_path: Path) -> None:
    skill_root = tmp_path / "custom-skills"
    skill = skill_root / "custom-analysis"
    skill.mkdir(parents=True)
    (skill / "manifest.json").write_text(
        json.dumps(
            {
                "name": "custom-analysis",
                "version": "1.0",
                "description": "A custom analysis skill preserved for workers",
                "entrypoint": "SKILL.md",
                "capability_names": ["custom-python"],
            }
        )
    )
    (skill / "SKILL.md").write_text("# Custom analysis\nUse bounded diagnostics.\n")
    capability_root = tmp_path / "custom-capabilities"
    capability_root.mkdir()
    runtime_root = tmp_path / "custom-runtime"
    (runtime_root / "bin").mkdir(parents=True)
    (runtime_root / "bin" / "python").symlink_to(Path(sys.executable).resolve())
    (capability_root / "custom-python.json").write_text(
        json.dumps(
            {
                "manifest": {
                    "name": "custom-python",
                    "version": "1.0",
                    "description": "Custom manifest root replay probe",
                    "skill": "custom-analysis",
                    "executable_kind": "python",
                },
                "runtime_root": "../custom-runtime",
                "executable": "bin/python",
                "environment": {},
                "read_only_mounts": {},
                "device_paths": [],
            }
        )
    )
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="Detached workers retain custom skill and capability identity.",
        skills=skill_root,
        capabilities=capability_root,
    )
    _prepare_startup(kernel)
    state = kernel.start_job(
        {
            "operation_id": "custom-resource-worker",
            "kind": "python",
            "argv": ["-c", "print('custom resources reopened')"],
            "timeout_seconds": 30,
        }
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = kernel.job_status(state.job_id)
        if state.status.terminal:
            break
        time.sleep(0.02)
    assert state.status is CampaignJobStatus.SUCCEEDED
    resources = json.loads((campaign / "kernel_resources.json").read_text())
    assert resources["skills_root"] == str(skill_root.resolve())
    assert resources["capabilities_root"] == str(capability_root.resolve())
    reopened = CampaignKernel.open(workspace=campaign)
    assert "custom-analysis" in reopened.skills.hashes
    assert "custom-python" in reopened.capabilities.hashes


def test_default_resources_are_frozen_inside_campaign(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "project"
    skill = source / "skills" / "mutable-analysis"
    skill.mkdir(parents=True)
    (skill / "manifest.json").write_text(
        json.dumps(
            {
                "name": "mutable-analysis",
                "version": "1.0",
                "description": "A repository skill frozen for detached workers",
                "entrypoint": "SKILL.md",
            }
        )
    )
    entrypoint = skill / "SKILL.md"
    entrypoint.write_text("# Original\nUse the campaign-pinned procedure.\n")
    capability_root = source / "capabilities"
    capability_root.mkdir(parents=True)

    from conjecture_solver import mvp_skills
    from conjecture_solver.mvp_skills import (
        MVPCapabilityRegistry,
        MVPSkillCatalog,
    )

    def discover_test_resources() -> tuple[MVPSkillCatalog, MVPCapabilityRegistry]:
        return (
            MVPSkillCatalog.discover(source / "skills"),
            MVPCapabilityRegistry.discover(capability_root),
        )

    monkeypatch.setattr(
        mvp_skills,
        "discover_builtin_mvp_resources",
        discover_test_resources,
    )
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="Detached workers must retain their initial skill catalog.",
    )
    original_hashes = kernel.skills.hashes
    resources = json.loads((campaign / "kernel_resources.json").read_text())
    frozen_skills = Path(resources["skills_root"])
    frozen_capabilities = Path(resources["capabilities_root"])
    assert frozen_skills == campaign / "kernel_resource_snapshot" / "skills"
    assert frozen_capabilities == campaign / "kernel_resource_snapshot" / "capabilities"

    entrypoint.write_text("# Mutated\nThis must not alter an active campaign.\n")
    reopened = CampaignKernel.open(workspace=campaign)
    assert reopened.skills.hashes == original_hashes
    assert reopened.skills.read(
        "mutable-analysis",
        None,
        max_chars=1_000,
    )["content"].startswith("# Original")


def test_prebuilt_host_reopens_from_frozen_resources(tmp_path: Path) -> None:
    from conjecture_solver.mvp_skills import (
        MVPCapabilityRegistry,
        MVPSkillCatalog,
    )

    source = tmp_path / "operator-resources"
    skill = source / "skills" / "native-analysis"
    skill.mkdir(parents=True)
    (skill / "manifest.json").write_text(
        json.dumps(
            {
                "name": "native-analysis",
                "version": "1.0",
                "description": "A native-runner resource freeze probe",
                "entrypoint": "SKILL.md",
            }
        )
    )
    entrypoint = skill / "SKILL.md"
    entrypoint.write_text("# Native original\n")
    capability_root = source / "capabilities"
    capability_root.mkdir(parents=True)
    campaign = tmp_path / "campaign"
    campaign.mkdir()

    def host() -> _Host:
        candidate = _Host()
        candidate.output = campaign
        candidate.skills = MVPSkillCatalog.discover(source / "skills")
        candidate.capabilities = MVPCapabilityRegistry.discover(capability_root)
        candidate.sandbox = SimpleNamespace(capabilities=candidate.capabilities)
        return candidate

    first = host()
    CampaignKernel.open(first)
    original_hashes = first.skills.hashes
    assert first.skills.root == campaign / "kernel_resource_snapshot" / "skills"

    entrypoint.write_text("# Native mutation\n")
    reopened = host()
    CampaignKernel.open(reopened)
    assert reopened.skills.hashes == original_hashes
    assert (
        reopened.skills.read("native-analysis", None, max_chars=100)["content"]
        == "# Native original\n"
    )


def test_snapshot_exposes_restart_discoverable_job_and_active_budget(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A restarted supervisor can discover every outstanding job.",
        config={"max_wall_seconds": 60.0, "max_command_seconds": 30.0},
    )
    _prepare_startup(kernel)
    state = kernel.start_job(
        {
            "operation_id": "snapshot-job",
            "kind": "python",
            "argv": ["-c", "import time; time.sleep(60)"],
            "timeout_seconds": 30,
        }
    )

    reopened = CampaignKernel.open(workspace=campaign)
    snapshot = reopened.snapshot()
    visible = {item["job_id"]: item for item in snapshot["jobs"]}
    assert state.job_id in visible
    assert visible[state.job_id]["operation_id"] == "snapshot-job"
    assert not CampaignJobStatus(visible[state.job_id]["status"]).terminal
    assert snapshot["budget"]["remaining_wall_seconds"] > 0
    assert snapshot["budget"]["remaining_actions"] is None

    cancelled = reopened.cancel_job(state.job_id)
    assert cancelled.status is CampaignJobStatus.CANCELLED


def test_kernel_budget_ignores_calendar_downtime(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="An idle stopped session consumes no active execution budget.",
        config={"max_wall_seconds": 2.0, "max_command_seconds": 1.0},
    )
    _prepare_startup(kernel)
    budget_path = campaign / "kernel_budget.json"
    budget = json.loads(budget_path.read_text())
    # Exercise migration from the unpublished calendar-time budget shape with
    # a timestamp far older than the configured two-second allowance.
    budget.pop("accumulated_active_seconds")
    budget["started_at"] = "2000-01-01T00:00:00+00:00"
    budget_path.write_text(json.dumps(budget))

    reopened = CampaignKernel.open(workspace=campaign)
    snapshot = reopened.snapshot()
    assert snapshot["budget"]["remaining_wall_seconds"] == pytest.approx(2.0)
    result = reopened.execute_operation(
        "after-long-downtime",
        {"action": "list_skills", "research_note": "resume after idle downtime"},
    )
    assert "skills" in result
    persisted = json.loads(budget_path.read_text())
    assert "started_at" not in persisted
    assert 0 <= persisted["accumulated_active_seconds"] < 2.0


def test_typed_job_request_is_a_worker_command_not_raw_simulation_argv(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A durable action must pass through the typed worker.",
    )

    class _Jobs:
        def __init__(self) -> None:
            self.request: dict[str, Any] | None = None

        def start(self, **request: Any) -> dict[str, Any]:
            self.request = request
            return {"status": "queued", "job_id": "job_test"}

    jobs = _Jobs()
    kernel._job_supervisor = jobs
    result = kernel.start_job(
        {
            "kind": "python",
            "argv": ["-c", "print('typed')"],
            "iteration": 4,
            "timeout_seconds": 10,
        }
    )
    assert result == {"status": "queued", "job_id": "job_test"}
    assert jobs.request is not None
    request = jobs.request["request"]
    assert request.argv[1:4] == ("-m", "conjecture_solver.kernel_worker", "--request")
    assert "--handshake" in request.argv
    assert request.metadata["action"]["action"] == "run_python"
    assert "input_artifacts" not in request.metadata["action"]
    worker_request = json.loads(Path(request.metadata["request_path"]).read_text())
    assert "iteration" not in worker_request
    assert "input_artifacts" not in worker_request["action"]


def test_legacy_parent_action_keeps_fingerprint_after_new_worker_parse() -> None:
    parent_payload = {
        "action": "run_python",
        "research_note": "Legacy parent request without an input sentinel.",
        "argv": ["-c", "print('legacy')"],
        "active_claim_id": None,
    }
    parsed_by_new_worker = parse_mvp_action(json.dumps(parent_payload))
    canonical = CampaignKernel._canonical_action(parsed_by_new_worker)

    assert canonical == parent_payload
    assert "input_artifacts" not in canonical
    assert CampaignKernel._operation_fingerprint(canonical, 30.0) == (
        CampaignKernel._operation_fingerprint(parent_payload, 30.0)
    )
    assert MVPAgentRunner._action_sha256(parsed_by_new_worker) == (
        "b82f43330e47266326a30d1bbeab426adb2866fcf57c6e8df0deb1841d7b2f97"
    )


def test_real_typed_async_action_reopens_kernel_and_persists_provenance(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A typed worker preserves sandbox action provenance.",
    )
    _prepare_startup(kernel)
    state = kernel.start_job(
        {
            "operation_id": "typed-async-provenance",
            "kind": "python",
            "argv": ["-c", "print('worker sandbox probe')"],
            "iteration": 5,
            "timeout_seconds": 30,
        }
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = kernel.job_status(state.job_id)
        if state.status.terminal:
            break
        time.sleep(0.02)
    report = kernel.job_report(state.job_id)
    assert state.status is CampaignJobStatus.SUCCEEDED, report
    assert report["status"] == CampaignJobStatus.SUCCEEDED.value
    assert report["request"]["kind"] == "python"
    assert report["worker_receipt"]["ok"] is True

    supervisor = CampaignJobSupervisor(campaign / "jobs")
    receipt = supervisor.result_record(state.job_id)
    assert receipt is not None
    assert '"action": "run_python"' in receipt.stdout
    provenance = json.loads((campaign / "artifact_provenance.json").read_text())
    assert any(record.get("action") == "run_python" for record in provenance["artifacts"].values())
    refreshed = kernel.snapshot()["artifact_provenance"]["artifacts"]
    assert any(record.get("action") == "run_python" for record in refreshed.values())

    reopened = CampaignKernel.open(workspace=campaign)
    assert reopened.job_status(state.job_id).status is CampaignJobStatus.SUCCEEDED


def test_durable_job_finalization_preserves_ineligible_input_lineage(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A durable analysis cannot promote a non-evidentiary input.",
    )
    _prepare_startup(kernel)
    source = "non-evidentiary operator datum"
    kernel.execute_operation(
        "write-lineage-source",
        {
            "action": "write_file",
            "research_note": "Create a tracked but non-evidentiary source artifact.",
            "path": "source.txt",
            "content": source,
        },
    )
    state = kernel.start_job(
        {
            "operation_id": "durable-lineage-analysis",
            "kind": "python",
            "argv": [
                "-c",
                "from pathlib import Path; "
                "Path('derived.txt').write_text(Path('source.txt').read_text())",
            ],
            "input_artifacts": [
                {
                    "path": "source.txt",
                    "sha256": hashlib.sha256(source.encode()).hexdigest(),
                }
            ],
            "timeout_seconds": 30,
        }
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = kernel.job_status(state.job_id)
        if state.status.terminal:
            break
        time.sleep(0.02)

    report = kernel.job_report(state.job_id)
    assert state.status is CampaignJobStatus.SUCCEEDED, report
    assert report["worker_receipt"]["ok"] is True
    provenance = json.loads((campaign / "artifact_provenance.json").read_text())["artifacts"]
    derived = provenance["derived.txt"]
    assert derived["job_status"] == CampaignJobStatus.SUCCEEDED.value
    assert derived["execution_succeeded"] is True
    assert derived["input_lineage_eligible"] is False
    assert derived["evidence_candidate"] is True
    assert derived["evidence_eligible"] is False
    assert report["request"]["action"]["input_artifacts"][0]["path"] == "source.txt"


def test_typed_async_action_failure_is_not_reported_as_success(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A failed sandbox action must remain a failed durable job.",
    )
    _prepare_startup(kernel)
    state = kernel.start_job(
        {
            "operation_id": "typed-async-failure",
            "kind": "python",
            "argv": [
                "-c",
                "from pathlib import Path; "
                "Path('partial.json').write_text('{\"partial\":true}'); "
                "raise SystemExit(7)",
            ],
            "iteration": 1,
            "timeout_seconds": 30,
        }
    )
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = kernel.job_status(state.job_id)
        if state.status.terminal:
            break
        time.sleep(0.02)

    assert state.status is CampaignJobStatus.FAILED
    report = kernel.job_report(state.job_id)
    assert report["result"]["returncode"] == 1
    assert report["worker_receipt"]["ok"] is False
    assert report["worker_receipt"]["result"]["returncode"] == 7
    provenance = json.loads((campaign / "artifact_provenance.json").read_text())
    partial = provenance["artifacts"]["partial.json"]
    assert partial["job_status"] == CampaignJobStatus.FAILED.value
    assert partial["execution_succeeded"] is False
    assert partial["evidence_eligible"] is False


def test_reopened_kernel_recovers_authenticated_worker_receipt(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A finished detached job remains known after an MCP restart.",
    )
    _prepare_startup(kernel)
    state = kernel.start_job(
        {
            "operation_id": "restart-receipt-probe",
            "kind": "python",
            "argv": ["-c", "print('restart-safe')"],
            "timeout_seconds": 30,
        }
    )
    supervisor = kernel._jobs()
    process = supervisor._processes[state.job_id]
    assert process.wait(timeout=10) == 0
    for handle in supervisor._streams.pop(state.job_id):
        handle.close()

    reopened = CampaignKernel.open(workspace=campaign)
    recovered = reopened.job_status(state.job_id)
    assert recovered.status is CampaignJobStatus.SUCCEEDED
    report = reopened.job_report(state.job_id)
    assert report["worker_receipt"]["ok"] is True
    assert report["result"]["detail"].startswith("reconciled from authenticated")


def test_unverified_worker_success_is_downgraded_to_unknown(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A typed worker requires an authenticated result receipt.",
    )
    _prepare_startup(kernel)
    state = kernel.start_job(
        {
            "operation_id": "tampered-worker-receipt",
            "kind": "python",
            "argv": ["-c", "print('receipt required')"],
            "timeout_seconds": 30,
        }
    )
    supervisor = kernel._jobs()
    assert supervisor._processes[state.job_id].wait(timeout=10) == 0
    result_path = Path(supervisor.request_record(state.job_id).metadata["worker_result_path"])
    result_path.write_text("{}\n")

    reconciled = kernel.job_status(state.job_id)
    assert reconciled.status is CampaignJobStatus.OUTCOME_UNKNOWN
    report = kernel.job_report(state.job_id)
    assert "valid authenticated" in report["result"]["detail"]
    provenance = json.loads((campaign / "artifact_provenance.json").read_text())
    assert not any(
        record.get("operation_id") == "tampered-worker-receipt"
        and record.get("evidence_eligible") is True
        for record in provenance["artifacts"].values()
    )


def test_running_job_can_be_cancelled_without_admitting_a_second_writer(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "campaign"
    kernel = CampaignKernel.open(
        workspace=campaign,
        hypothesis="A running scientific job remains cancellable and exclusive.",
    )
    _prepare_startup(kernel)
    state = kernel.start_job(
        {
            "operation_id": "long-running-writer",
            "kind": "python",
            "argv": ["-c", "import time; time.sleep(60)"],
            "timeout_seconds": 60,
        }
    )
    with pytest.raises(CampaignWriterBusyError):
        kernel.execute_operation(
            "blocked-concurrent-write",
            {
                "action": "write_file",
                "research_note": "A leased job must exclude a second writer.",
                "path": "must-not-exist.txt",
                "content": "blocked",
            },
        )

    cancelled = kernel.execute_operation(
        "cancel-long-running-writer",
        {"action": "cancel_job", "job_id": state.job_id},
    )
    assert cancelled["status"] in {
        CampaignJobStatus.CANCELLED.value,
        CampaignJobStatus.CANCEL_REQUESTED.value,
    }
    terminal = kernel.job_status(state.job_id)
    assert terminal.status is CampaignJobStatus.CANCELLED
    assert not (campaign / "workspace" / "must-not-exist.txt").exists()
    journal = json.loads((campaign / "action_journal.json").read_text())
    assert journal["operations"]["cancel-long-running-writer"]["status"] == "succeeded"


def test_nonterminal_job_status_does_not_wait_for_campaign_writer_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = CampaignKernel.open(
        workspace=tmp_path / "campaign",
        hypothesis="Status polling stays responsive during worker startup.",
    )
    running = SimpleNamespace(
        job_id="job_running",
        operation_id="running-operation",
        status=CampaignJobStatus.RUNNING,
    )

    class _RunningJobs:
        @staticmethod
        def status(job_id: str) -> Any:
            assert job_id == running.job_id
            return running

    def unexpected_lock(**_kwargs: Any) -> Any:
        raise AssertionError("non-terminal status must not acquire the campaign lock")

    kernel._job_supervisor = _RunningJobs()
    monkeypatch.setattr(kernel, "_writer_lock", unexpected_lock)
    assert kernel.job_status(running.job_id) is running


def test_nonterminal_job_is_the_single_campaign_writer(tmp_path: Path) -> None:
    kernel = CampaignKernel.open(
        workspace=tmp_path / "campaign",
        hypothesis="Only one durable campaign writer may mutate state.",
    )

    class _BusyJobs:
        _operations: dict[str, str] = {}

        @staticmethod
        def jobs() -> tuple[Any, ...]:
            return (
                SimpleNamespace(
                    operation_id="already-writing",
                    status=CampaignJobStatus.RUNNING,
                ),
            )

    kernel._job_supervisor = _BusyJobs()
    write = {
        "action": "write_file",
        "research_note": "A second writer must be rejected.",
        "path": "blocked.txt",
        "content": "blocked",
    }
    with pytest.raises(CampaignWriterBusyError):
        kernel.execute(write, iteration=1)
    with pytest.raises(CampaignWriterBusyError):
        kernel.start_job(
            {
                "kind": "python",
                "argv": ["-c", "print('blocked')"],
                "iteration": 1,
            }
        )
