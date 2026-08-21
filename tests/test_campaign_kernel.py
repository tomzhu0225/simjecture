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
    MVPListSkillsAction,
    MVPWriteFileAction,
)


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
    with pytest.raises(CampaignOperationFailedError, match="durable failure"):
        kernel.execute_operation("failed-operation", action)
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
    worker_request = json.loads(
        Path(request.metadata["request_path"]).read_text()
    )
    assert "iteration" not in worker_request


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
    assert state.status is CampaignJobStatus.SUCCEEDED
    report = kernel.job_report(state.job_id)
    assert report["status"] == CampaignJobStatus.SUCCEEDED.value
    assert report["request"]["kind"] == "python"
    assert report["worker_receipt"]["ok"] is True

    supervisor = CampaignJobSupervisor(campaign / "jobs")
    receipt = supervisor.result_record(state.job_id)
    assert receipt is not None
    assert '"action": "run_python"' in receipt.stdout
    provenance = json.loads((campaign / "artifact_provenance.json").read_text())
    assert any(
        record.get("action") == "run_python"
        for record in provenance["artifacts"].values()
    )
    refreshed = kernel.snapshot()["artifact_provenance"]["artifacts"]
    assert any(record.get("action") == "run_python" for record in refreshed.values())

    reopened = CampaignKernel.open(workspace=campaign)
    assert reopened.job_status(state.job_id).status is CampaignJobStatus.SUCCEEDED


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
    result_path = Path(
        supervisor.request_record(state.job_id).metadata["worker_result_path"]
    )
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
