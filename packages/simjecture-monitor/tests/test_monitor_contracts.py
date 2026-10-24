import json

import pytest
from simjecture_monitor.events import PublicStream
from simjecture_monitor.policy import AlertGate, RulesPolicy


def tool(command, output, exit_code=1):
    return dict(
        type="item.completed",
        item=dict(
            type="command_execution", command=command, aggregated_output=output, exit_code=exit_code
        ),
    )


def test_incremental_public_stream_ignores_reasoning_and_waits_for_complete_lines(tmp_path):
    path = tmp_path / "events.jsonl"
    private = dict(type="item.completed", item=dict(type="reasoning", text="PRIVATE_CHAIN"))
    event = json.dumps(tool("python solve.py", "failed"))
    path.write_text(json.dumps(private) + "\n" + event[:20])
    stream = PublicStream(path)
    assert stream.poll() == []
    with path.open("a") as output:
        output.write(event[20:] + "\n")
    assert len(stream.poll()) == 1
    assert stream.poll() == []
    assert "PRIVATE_CHAIN" not in json.dumps(stream.packet("Task"))


def test_stale_decision_and_duplicate_alerts_cannot_trigger_repeated_wakes(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(
        "\n".join(json.dumps(tool("python solve.py", "failed")) for _ in range(3)) + "\n"
    )
    stream = PublicStream(path)
    stream.poll(now=10)
    packet = stream.packet("Resolve a numerical failure")
    decision = RulesPolicy().predict(packet)
    assert decision["choice"] == "request_worker_help"
    gate = AlertGate(cooldown=60)
    with pytest.raises(ValueError, match="Stale"):
        gate.accept(packet, dict(decision, packet_sha256="other"))
    assert gate.accept(packet, decision, now=10)["origin"] == "coprocessor"
    assert gate.accept(packet, decision, now=80) is None
    assert gate.accept(packet, decision, now=20) is None


def test_healthy_success_does_not_trigger_the_error_counter(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(
        "\n".join(json.dumps(tool("python solve.py", "iteration progressing", 0)) for _ in range(6))
        + "\n"
    )
    stream = PublicStream(path)
    stream.poll()
    assert RulesPolicy().predict(stream.packet("Measure convergence"))["choice"] == "defer"


def test_diagnostic_stream_observes_running_process_before_eof(tmp_path):
    import subprocess
    import sys
    import time

    from simjecture_monitor.events import DiagnosticStream

    output = tmp_path / "run.log"
    with output.open("w") as log:
        child = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "-c",
                'import time; print("step 1 residual 0.1", flush=True); time.sleep(3)',
            ],
            stdout=log,
        )
    try:
        reader = DiagnosticStream(output, subject="simulation-1")
        until = time.monotonic() + 2
        observed = []
        while not observed and time.monotonic() < until:
            observed = reader.poll()
            time.sleep(0.02)
        assert observed and child.poll() is None
        assert "step 1" in observed[0]["body"]["aggregated_output"]
        assert reader.poll() == []
    finally:
        child.terminate()
        child.wait(timeout=5)
