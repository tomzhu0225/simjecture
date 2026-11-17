"""One non-scientific model-routing handshake in the isolated role launcher."""

import json
import os
import subprocess
import tempfile
import threading
from pathlib import Path


def main():
    from research_decision.gateway import ScienceGateway
    from research_decision.isolation import command
    from research_decision.network import model_network
    from research_decision.remote_control import Remote
    from research_decision.storage import read_json, write_json

    root = Path(__file__).resolve().parents[1]
    cfg = read_json(root / "config/isolation.local.json")
    remote = Remote(read_json(root / "config/pipeline.local.json"))
    case = (
        Path(read_json(root / "config/pipeline.local.json")["case_store"])
        / "diagnostics/model-routing-fixture"
    )
    case.mkdir(parents=True, exist_ok=True)
    write_json(case / "role-packet.json", dict(purpose="Connectivity only; no scientific task."))
    with tempfile.TemporaryDirectory() as scratch:
        cfg["transport_socket"] = str(Path(scratch) / "transport.sock")
        with (
            model_network(cfg["network_proxy"]),
            ScienceGateway(cfg["transport_socket"], remote.route, remote.root) as server,
        ):
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            argv = command(
                cfg,
                [
                    "exec",
                    "--ignore-user-config",
                    "--ignore-rules",
                    "--ephemeral",
                    "--model",
                    "gpt-6.1-sol",
                    "--skip-git-repo-check",
                    "--dangerously-bypass-approvals-and-sandbox",
                    "--json",
                    "Non-scientific tool connectivity check only. Use a shell/code tool to run /app/bin/python -c \"from conjecture_solver.execution_pool import MachineRegistry; p=MachineRegistry('/srv/simjecture/research/decision_training/controller-machine-registry').transport('remote-cpu').call('probe',timeout=30); print('SCIENCE_ROUTE_READY',p['capacity']['cpus'])\". Return SCIENCE_ROUTE_READY 32 only if this succeeds. Do not run any physics, research, training, or other commands.",
                ],
                case,
            )
            environment = {k: v for k, v in os.environ.items() if not k.startswith("CODEX_")}
            try:
                result = subprocess.run(argv, capture_output=True, text=True, env=environment, timeout=180)
            except subprocess.TimeoutExpired as error:
                result = subprocess.CompletedProcess(
                    argv, 124, (error.stdout or b"").decode(), (error.stderr or b"").decode()
                )
            finally:
                server.shutdown()
    (case / "routing-output.jsonl").write_text(result.stdout, encoding="utf-8")
    report = dict(
        requested_model="gpt-6.1-sol",
        exit_code=result.returncode,
        passed=result.returncode == 0 and "SCIENCE_ROUTE_READY 32" in result.stdout,
        non_scientific_connectivity_calls=2,
        teacher_research_trajectories=0,
        physical_studies=0,
        optimizer_updates=0,
        error=result.stderr[-1500:],
    )
    write_json(root / "reports/model_route.json", report)
    print(json.dumps(report))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
