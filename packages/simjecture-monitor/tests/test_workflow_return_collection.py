"""CLI orchestration checks use fake children and never run local physics/models."""

import importlib.util
import json
import os
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from simjecture_monitor.events import digest, put
from simjecture_monitor.sampling_trace import SamplingTrace
from test_sampling_trace import model, observed, response, save


def load(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "workflow_collection_test", scripts / "collect_workflow_returns.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "purpose,fail", [("train", False), ("commissioning", False), ("train", True)]
)
def test_live_lifecycle_commands_export_only_complete_training_cohorts(
    tmp_path, monkeypatch, purpose, fail
):
    module = load(monkeypatch)
    root = tmp_path / "cohort"
    put(tmp_path / "backend", {"scope": "test fixture only"})
    planned = module.plan(
        SimpleNamespace(
            root=root,
            purpose=purpose,
            replicates=2 if purpose == "train" else 1,
            native_cap=12,
            temperature=3.0,
            family=["progressing_work"],
            configuration_seed=13,
            order_seed=19,
            model_policy="adapted",
            adapter_sha256="a" * 64,
            backend=tmp_path / "backend",
        )
    )
    budget = tmp_path / "budget.json"
    put(
        budget,
        dict(
            starts=[], maximum_starts=100, maximum_per_continuation=12, deadline=time.time() + 10000
        ),
    )
    token = tmp_path / "token"
    token.write_text("test-only-not-a-real-credential")
    server_identity = model().identity | {
        "adapter_files_sha256": {"adapter_model.safetensors": "a" * 64}
    }
    monkeypatch.setattr(
        module,
        "request",
        lambda *args, **kw: dict(
            status=dict(
                stage="ready", policies=["adapted"], temperature=3.0, model_identity=server_identity
            )
        ),
    )
    lock = threading.Lock()
    invoked = []
    failed_id = planned["blocks"][0]["trials"][0]["id"]

    class Child:
        def __init__(self, command, **kwargs):
            self.pid = os.getpid()
            folder = Path(command[command.index("--root") + 1])
            folder.mkdir()
            identity = folder.name
            sampled = "--sampling-seed" in command
            invoked.append((identity, sampled))
            assert command[command.index("--arm") + 1] == ("adapted" if sampled else "observe")
            assert kwargs["env"]["SIMJECTURE_CONTINUATION"] == identity
            if not sampled:
                assert "--model-policy" not in command
            self.code = 1 if fail and identity == failed_id else 0
            if self.code:
                return
            physical = folder / "research/runs/control"
            physical.mkdir(parents=True)
            put(physical / "receipt.json", dict(status="succeeded"))
            result = dict(diagnosis="Explicit test fixture", unresolved=False, runs=[])
            put(folder / "research/results.json", result)
            (folder / "research/REPORT.txt").write_text("Test fixture report")
            quality = dict(
                results_sha256=digest(result), report_sha256=digest("Test fixture report")
            )
            put(folder / "QUALITY.json", quality)
            put(folder / "INITIAL.json", dict(criteria=module.CRITERIA))
            put(folder / "incident-ledger.json", dict(feedback=[]))
            put(
                folder / "HOST_CASE.json",
                dict(family="progressing_work", seed=13, arm="adapted" if sampled else "observe"),
            )
            stream = folder / "execution/turn-00001/response.json"
            stream.parent.mkdir(parents=True)
            stream.write_text(
                json.dumps(
                    dict(
                        type="item.completed", item=dict(type="agent_message", text="Test fixture")
                    )
                )
                + "\n"
            )
            starts = 3 if sampled else 2
            with lock:
                lease = json.loads(budget.read_text())
                lease["starts"] += [
                    dict(
                        continuation=identity,
                        native={"pid": self.pid},
                        cwd=str(folder / "research"),
                        started_at=0.0,
                        ended_at=time.time(),
                    )
                    for _ in range(starts)
                ]
                put(budget, lease)
            put(
                folder / "OUTCOME.json",
                dict(
                    stage="completed",
                    quality=quality,
                    elapsed_seconds=200.0,
                    native_starts=starts,
                    observation_violations=[],
                    ledger=dict(duplicate_wakeups=0),
                    turns=[dict(returncode=0, ended_at=time.time())],
                    completion_checks=[dict(allowed=True)],
                    finish_reason="worker_finished_with_obligations_reconciled",
                    verified_complete=True,
                ),
            )
            if sampled:
                trace = SamplingTrace(
                    folder / "monitor",
                    seed=int(command[command.index("--sampling-seed") + 1]),
                    split=purpose,
                )
                packet = observed()
                value = response(trace, packet)
                value["model_identity"] = server_identity
                value["behavior"]["model_identity"] = server_identity
                value["prediction"].update(
                    input_tokens=1000, forward_seconds=0.01, total_seconds=0.02
                )
                save(trace, packet, value)
                trace.close()
                completed = json.loads((folder / "OUTCOME.json").read_text())
                completed["parking"] = [
                    dict(started_at=trace.data["created_at"], ended_at=time.time())
                ]
                put(folder / "OUTCOME.json", completed)

        def wait(self, *, timeout):
            return self.code

    monkeypatch.setattr(module.subprocess, "Popen", Child)
    outcome = module.run(
        SimpleNamespace(
            root=root,
            budget=budget,
            auth_token_file=token,
            socket=tmp_path / "socket",
            backend=tmp_path / "backend",
            wrapper=tmp_path / "wrapper",
            python=tmp_path / "python",
            plasma_assets=tmp_path / "plasma",
        )
    )
    assert len(invoked) == len(planned["blocks"][0]["trials"])
    assert sum(sampled for _, sampled in invoked) == (2 if purpose == "train" else 1)
    assert outcome["export"]["eligible"] is (purpose == "train" and not fail)
    assert (root / "receipts/train.jsonl").exists() is (purpose == "train" and not fail)
    if not fail:
        assert outcome["export"]["sampling_exercised"]
        assert outcome["export"]["collection_verified"]
        if purpose == "commissioning":
            assert (root / "receipts/commissioning.jsonl").exists()
    with pytest.raises(ValueError, match="already attempted"):
        module.run(SimpleNamespace(root=root))


def test_provider_errors_are_not_confused_with_failed_scientific_tool_commands(
    tmp_path, monkeypatch
):
    module = load(monkeypatch)
    folder = tmp_path / "episode"
    p = folder / "execution/response.json"
    p.parent.mkdir(parents=True)
    starts = [dict(continuation=folder.name, native={"pid": 1}, ended_at=1)]
    p.write_text(
        json.dumps(dict(type="item.completed", item=dict(type="command_execution", exit_code=1)))
        + "\n"
    )
    assert module.require_native_evidence(folder, starts) == 1
    p.write_text(json.dumps(dict(type="error", message="Provider unavailable")) + "\n")
    with pytest.raises(ValueError, match="provider failure"):
        module.require_native_evidence(folder, starts)


def test_parked_label_alone_cannot_override_the_actual_worker_timeline(tmp_path, monkeypatch):
    load(monkeypatch)
    from export_workflow_returns import require_parked_requests

    root = tmp_path / "episode"
    out = dict(parking=[dict(started_at=10.0, ended_at=20.0)])
    requests = [dict(requested_at=15.0)]
    require_parked_requests(root, out, requests, [])
    with pytest.raises(ValueError, match="outside"):
        require_parked_requests(root, out, [dict(requested_at=25.0)], [])
    starts = [
        dict(continuation=root.name, cwd=str(root / "research"), started_at=14.0, ended_at=16.0)
    ]
    with pytest.raises(ValueError, match="overlaps an active"):
        require_parked_requests(root, out, requests, starts)
