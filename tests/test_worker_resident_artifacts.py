"""End-to-end synthetic tests for worker-resident output and reuse."""

import hashlib
import json
import sys
import time
from pathlib import Path

import pytest

from conjecture_solver.execution_pool import MachineRegistry
from conjecture_solver.research_service import ResearchService, put


@pytest.fixture
def registry(tmp_path):
    result = MachineRegistry(tmp_path / "registry")
    for name in ("node-a", "node-b"):
        result.save(
            {
                "id": name,
                "kind": "local",
                "root": str(tmp_path / name),
                "python": sys.executable,
                "config": {
                    "cpus": 2,
                    "memory_mb": 4096,
                    "max_jobs": 1,
                    "execution_backend": "process-cooperative",
                },
            }
        )
        result.prepare(name)
    return result


def finish(service, identifier, timeout=25):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        state = service._read("experiments", identifier)
        if state["status"] not in {"queued", "running"}:
            return state
        time.sleep(0.05)
    pytest.fail("synthetic worker did not finish")


def new_service(tmp_path, registry, **kwargs):
    return ResearchService.create(
        tmp_path / "study",
        "A bounded synthetic claim.",
        wall_seconds=120,
        execution_pool=registry.freeze(["node-a", "node-b"]),
        **kwargs,
    )


def produce(service, machine="node-a", key="producer"):
    (service.work / "producer.py").write_text(
        "import json\nfrom pathlib import Path\n"
        "Path('dataset.bin').write_bytes(b'abc123'*100000)\n"
        "Path('summary.json').write_text(json.dumps({'count': 600000}))\n"
    )
    receipt = service.run(
        "producer.py",
        outputs=["dataset.bin", "summary.json"],
        machine=machine,
        stage="exploration",
        key=key,
    )
    result = finish(service, receipt["id"])
    assert result["status"] == "succeeded", result
    return result


def test_default_resident_and_same_worker_analysis_with_on_demand_fetch(tmp_path, registry):
    service = new_service(tmp_path, registry)
    assert service.artifact_policy() == "remote"
    parent = produce(service)
    workspace = service.root / "experiments" / parent["id"] / "workspace"
    assert not (workspace / "dataset.bin").exists()
    assert not (workspace / "summary.json").exists()
    assert parent["remote_artifacts"]["dataset.bin"]["bytes"] == 600000
    assert parent["scientific_status"] == "unreviewed"
    reference = {"input.bin": {"experiment": parent["id"], "path": "dataset.bin"}}
    (service.work / "analyze.py").write_text(
        "from pathlib import Path\n"
        "data=Path('input.bin').read_bytes()\n"
        "Path('answer.json').write_text('{\\\"length\\\":%d}' % len(data))\n"
    )
    analysis = service.run(
        "analyze.py", outputs=["answer.json"], stage="exploration", remote_inputs=reference
    )
    assert analysis["machine"] == "node-a"
    assert not (service.root / "experiments" / analysis["id"] / "workspace/input.bin").exists()
    resolved = analysis["binding"]["remote_inputs"]["input.bin"]
    assert resolved["job"] == parent["remote_job"]
    assert resolved["sha256"] == parent["remote_artifacts"]["dataset.bin"]["sha256"]
    analysis = finish(service, analysis["id"])
    assert analysis["status"] == "succeeded", analysis
    assert "answer.json" in analysis["remote_artifacts"]
    assert not (service.root / "experiments" / analysis["id"] / "workspace/answer.json").exists()
    path = Path(service.fetch_remote(analysis["id"], "answer.json")["path"])
    assert json.loads(path.read_text()) == {"length": 600000}
    assert not (workspace / "dataset.bin").exists()
    assert service.fetch_remote(parent["id"], "dataset.bin")["sha256"] == resolved["sha256"]
    assert (
        hashlib.sha256((workspace / "dataset.bin").read_bytes()).hexdigest() == resolved["sha256"]
    )


def test_resident_bindings_reject_placement_and_namespace_conflicts(tmp_path, registry):
    service = new_service(tmp_path, registry)
    parent = produce(service)
    (service.work / "analyze.py").write_text("print('fixture')\n")
    ref = {"input.bin": {"experiment": parent["id"], "path": "dataset.bin"}}
    with pytest.raises(ValueError, match="same worker"):
        service.run(
            "analyze.py", outputs=["out"], stage="exploration", machine="node-b", remote_inputs=ref
        )
    with pytest.raises(ValueError, match="outputs cannot"):
        service.run("analyze.py", outputs=["input.bin"], stage="exploration", remote_inputs=ref)
    with pytest.raises(ValueError, match="cannot replace"):
        service.run(
            "analyze.py",
            outputs=["out"],
            stage="exploration",
            remote_inputs={"analyze.py": {"experiment": parent["id"], "path": "dataset.bin"}},
        )
    with pytest.raises(ValueError):
        service.run(
            "analyze.py",
            outputs=["out"],
            stage="exploration",
            remote_inputs={"../escape": {"experiment": parent["id"], "path": "dataset.bin"}},
        )
    with pytest.raises(ValueError, match="absent"):
        service.run(
            "analyze.py",
            outputs=["out"],
            stage="exploration",
            remote_inputs={"x": {"experiment": parent["id"], "path": "missing.bin"}},
        )


def test_method_commitment_and_remote_review_metadata_bind_reference(tmp_path, registry):
    service = new_service(tmp_path, registry)
    parent = produce(service)
    ref = {"input.bin": {"experiment": parent["id"], "path": "dataset.bin"}}
    (service.work / "analyze.py").write_text(
        "from pathlib import Path\nPath('result.json').write_text('{}')\n"
        "Path('raw.bin').write_bytes(b'uninspected')\n"
    )
    method = service.method(
        source="analyze.py",
        model="read bytes",
        geometry="none",
        observable="length",
        validation="fixture",
        rationale="bounded fixture",
        remote_inputs=ref,
    )
    frozen = method["binding"]["remote_inputs"]["input.bin"]
    assert frozen["sha256"] == parent["remote_artifacts"]["dataset.bin"]["sha256"]
    assert method["remote_inputs"]["input.bin"]["inspected"] is False
    commitment = service.commit(
        "The fixture reports a bounded length.",
        source="analyze.py",
        cases=[[]],
        acceptance="length is recorded",
        rationale="finite alternative",
        remote_inputs=ref,
    )
    assert commitment["bindings"][0]["remote_inputs"]["input.bin"] == frozen
    record = service.run(
        "analyze.py",
        outputs=["result.json", "raw.bin"],
        stage="evidence",
        remote_inputs=ref,
        commitment=commitment["id"],
    )
    result = finish(service, record["id"])
    assert result["status"] == "succeeded", result
    assert result["binding"] in commitment["bindings"]
    fetched = service.fetch_remote(result["id"], "result.json")
    assert Path(fetched["path"]).read_text() == "{}"
    packet = service.packet(
        {
            "experiments": [result["id"]],
            "claim": commitment["id"],
            "conclusion": "The fixture produces the requested bounded result.",
            "disposition": "falsified",
        }
    )
    view = packet["experiments"][0]["remote_inputs"]["input.bin"]
    assert view["sha256"] == frozen["sha256"] and view["inspected"] is False
    assert packet["experiments"][0]["record"]["scientific_status"] == "unreviewed"
    raw = packet["experiments"][0]["raw_artifacts"]["raw.bin"]
    assert raw["location"] == "worker" and raw["inspected"] is False
    assert raw["sha256"] == result["remote_artifacts"]["raw.bin"]["sha256"]


def test_cross_worker_and_missing_feature_rejected(tmp_path, registry):
    service = new_service(tmp_path, registry)
    first = produce(service, "node-a", "a")
    second = produce(service, "node-b", "b")
    refs = {
        "a.bin": {"experiment": first["id"], "path": "dataset.bin"},
        "b.bin": {"experiment": second["id"], "path": "dataset.bin"},
    }
    with pytest.raises(ValueError, match="share one worker"):
        service.resolve_remote_inputs(refs)
    manifest = dict(service.manifest)
    manifest["execution_pool"]["workers"]["node-a"]["probe"]["features"]["artifact_inputs"] = False
    put(service.root / "research.json", manifest)
    with pytest.raises(ValueError, match="lacks artifact_inputs"):
        service.resolve_remote_inputs({"a.bin": refs["a.bin"]})


def test_resident_outputs_consume_study_storage_allowance(tmp_path, registry):
    service = new_service(
        tmp_path, registry, max_experiment_bytes=2 * 1024**2, max_total_bytes=2 * 1024**2
    )
    parent = produce(service)
    assert service.artifact_storage()["used_bytes"] >= 600000
    (service.work / "analyze.py").write_text("print('fixture')\n")
    with pytest.raises(ValueError, match="storage reservation"):
        service.run(
            "analyze.py",
            outputs=["out"],
            stage="exploration",
            remote_inputs={"input.bin": {"experiment": parent["id"], "path": "dataset.bin"}},
        )


def test_absent_legacy_policy_remains_eager(tmp_path):
    service = ResearchService.create(tmp_path / "study", "synthetic")
    assert service.artifact_policy() == "remote"
    manifest = dict(service.manifest)
    del manifest["artifact_policy"]
    put(service.root / "research.json", manifest)
    assert ResearchService(service.root).artifact_policy() == "eager"


def test_capability_on_different_worker_is_rejected(tmp_path, registry):
    service = new_service(tmp_path, registry)
    parent = produce(service)
    (service.work / "analyze.py").write_text("print('fixture')\n")
    manifest = dict(service.manifest)
    runtime = "a" * 64
    manifest["execution_pool"]["capabilities"]["instrument--node-b"] = {
        "machine": "node-b",
        "runtime_sha256": runtime,
        "worker_capability": "instrument",
    }
    manifest["capability_hashes"]["instrument--node-b"] = runtime
    put(service.root / "research.json", manifest)
    with pytest.raises(ValueError, match="capability on the resident"):
        service.run(
            "analyze.py",
            outputs=["out"],
            stage="exploration",
            capability="instrument--node-b",
            remote_inputs={"input.bin": {"experiment": parent["id"], "path": "dataset.bin"}},
        )


def test_mutated_worker_artifact_is_rejected_by_later_analysis(tmp_path, registry):
    service = new_service(tmp_path, registry)
    parent = produce(service)
    path = (
        Path(registry.machine("node-a").root)
        / "jobs"
        / parent["remote_job"]
        / "workspace/dataset.bin"
    )
    path.write_bytes(b"z" * 600000)
    (service.work / "analyze.py").write_text(
        "from pathlib import Path\nPath('out').write_text('ok')\n"
    )
    record = service.run(
        "analyze.py",
        outputs=["out"],
        stage="exploration",
        remote_inputs={"input.bin": {"experiment": parent["id"], "path": "dataset.bin"}},
    )
    result = finish(service, record["id"])
    assert result["status"] == "failed", result
    assert "hash" in (result.get("error") or "").lower()
    assert result.get("scientific_status", "unreviewed") == "unreviewed"


def test_resident_cache_is_not_double_counted(tmp_path, registry):
    service = new_service(tmp_path, registry)
    parent = produce(service)
    before = service.artifact_storage()["used_bytes"]
    service.fetch_remote(parent["id"], "dataset.bin")
    after = service.artifact_storage()["used_bytes"]
    assert abs(after - before) < 8192


def test_resident_paths_cannot_be_ancestors_of_inputs_or_outputs(tmp_path, registry):
    service = new_service(tmp_path, registry)
    parent = produce(service)
    (service.work / "analyze.py").write_text("print('fixture')\n")
    source = {"experiment": parent["id"], "path": "dataset.bin"}
    with pytest.raises(ValueError, match="cannot contain"):
        service.run(
            "analyze.py",
            outputs=["input.bin/child"],
            stage="exploration",
            remote_inputs={"input.bin": source},
        )
    with pytest.raises(ValueError, match="cannot contain"):
        service.run(
            "analyze.py",
            outputs=["out"],
            stage="exploration",
            remote_inputs={"analyze.py/child": source},
        )
    with pytest.raises(ValueError, match="cannot contain"):
        service.method(
            source="analyze.py",
            model="fixture",
            geometry="none",
            observable="none",
            validation="fixture",
            rationale="fixture",
            remote_inputs={"analyze.py/child": source},
        )


@pytest.mark.parametrize(
    "receipt",
    [
        {"artifacts": []},
        {"artifacts": {"x": {"sha256": "bad", "bytes": 1}}},
        {"artifacts": {"x": {"sha256": "a" * 64, "bytes": True}}},
        {"artifacts": {"x": {"sha256": "a" * 64, "bytes": -1}}},
        {"artifacts": {"../escape": {"sha256": "a" * 64, "bytes": 1}}},
        {"artifacts": {"a//b": {"sha256": "a" * 64, "bytes": 1}}},
        {
            "artifacts": {
                "a": {"sha256": "a" * 64, "bytes": 1},
                "a/b": {"sha256": "a" * 64, "bytes": 1},
            }
        },
        {"artifacts": {}, "execution": {"workspace_bytes": -1}},
        {"artifacts": {}, "execution": {"workspace_bytes": False}},
    ],
)
def test_invalid_terminal_metadata_is_rejected_before_import(receipt):
    from conjecture_solver.execution_pool import import_result

    with pytest.raises(ValueError):
        import_result(object(), {}, object(), receipt)


def test_method_validation_requires_fetching_compact_remote_document(tmp_path, registry):
    service = new_service(tmp_path, registry)
    parent = produce(service)
    kwargs = dict(
        source="producer.py",
        model="fixture",
        geometry="none",
        observable="count",
        validation="synthetic",
        rationale="synthetic example",
        validation_experiments=[parent["id"]],
    )
    with pytest.raises(ValueError, match="fetch remote review documents"):
        service.method(**kwargs)
    assert not service._all("methods")
    service.fetch_remote(parent["id"], "summary.json")
    method = service.method(**kwargs)
    evidence = method["evidence"][0]
    assert json.loads(evidence["documents"]["summary.json"])["count"] == 600000
    assert evidence["raw_artifacts"]["dataset.bin"]["inspected"] is False
    assert method["status"] == "queued"


@pytest.mark.parametrize("observed", [False, True])
@pytest.mark.parametrize("terminal", ["succeeded", "cancelled"])
def test_cancel_racing_terminal_worker_imports_resident_receipt_without_fetch(
    tmp_path, registry, monkeypatch, observed, terminal
):
    import conjecture_solver.execution_pool as module
    from conjecture_solver.execution_worker import Worker

    service = new_service(tmp_path, registry)
    finished = produce(service)
    job = finished["remote_job"]
    worker = Worker(registry.machine("node-a").root)
    state = worker.status(job)
    state["status"] = terminal
    # Simulate the coordinator still writing its record while the worker is terminal.
    record = dict(finished, status="running", worker_identity=None)
    record.pop("cancel_requested", None)
    if observed:
        record["remote_terminal_status"] = terminal
        record["remote_artifacts"] = state["artifacts"]
    else:
        record.pop("remote_terminal_status", None)
        record.pop("remote_artifacts", None)
    put(service.root / "experiments" / (record["id"] + ".json"), record)
    calls = []

    class FakeTransport:
        def call(self, method, **kwargs):
            calls.append(method)
            assert method in {"cancel", "status"}
            assert kwargs["identifier"] == job
            return state

    class FakeRegistry:
        def __init__(self, *_):
            pass

        def transport(self, *_args, **_kwargs):
            return FakeTransport()

    monkeypatch.setattr(module, "MachineRegistry", FakeRegistry)
    result = module.cancel_remote(service, record)
    assert result["status"] == terminal
    assert result["remote_job"] == job
    assert result["remote_artifacts"] == state["artifacts"]
    assert result.get("scientific_status", "unreviewed") == "unreviewed"
    assert not (service.root / "experiments" / record["id"] / "workspace/dataset.bin").exists()
    assert set(calls) <= {"cancel", "status"}


@pytest.mark.parametrize("observed", [False, True])
def test_cancel_race_rejects_mismatched_terminal_request(tmp_path, registry, monkeypatch, observed):
    import conjecture_solver.execution_pool as module
    from conjecture_solver.execution_worker import Worker

    service = new_service(tmp_path, registry)
    finished = produce(service)
    job = finished["remote_job"]
    state = Worker(registry.machine("node-a").root).status(job)
    state["request_sha256"] = "0" * 64
    record = dict(finished, status="running", worker_identity=None)
    if observed:
        record["remote_terminal_status"] = "succeeded"
    else:
        record.pop("remote_terminal_status", None)
    put(service.root / "experiments" / (record["id"] + ".json"), record)

    class FakeTransport:
        def call(self, method, **kwargs):
            assert method in {"cancel", "status"} and kwargs["identifier"] == job
            return state

    class FakeRegistry:
        def __init__(self, *_):
            pass

        def transport(self, *_args, **_kwargs):
            return FakeTransport()

    monkeypatch.setattr(module, "MachineRegistry", FakeRegistry)
    with pytest.raises(ValueError, match="different experiment request"):
        module.cancel_remote(service, record)
    assert service._read("experiments", record["id"])["status"] == "running"
