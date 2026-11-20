"""Prepare-only namespace and native remote-worker interface checks."""

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from research_decision.gateway import ScienceGateway
    from research_decision.isolation import command

    config = json.loads((ROOT / "config/isolation.local.json").read_bytes())
    route = json.loads((ROOT / "config/ssh-route.local.json").read_bytes())
    binary = PureWindowsPath(route[0])
    route[0] = "/mnt/" + binary.drive[0].lower() + "/" + "/".join(binary.parts[1:])
    environment = dict(os.environ)
    for key in list(environment):
        if key.startswith("CODEX_"):
            environment.pop(key, None)
    with tempfile.TemporaryDirectory(prefix="science-isolation-") as scratch:
        socket_path = Path(scratch) / "transport.sock"
        config["transport_socket"] = str(socket_path)
        with ScienceGateway(socket_path, route, "/srv/simjecture-decision") as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            case = ROOT / "diagnostics/isolation-fixture"
            case.mkdir(parents=True, exist_ok=True)
            (case / "role-packet.json").write_text('{"purpose":"preparation fixture"}')
            prefix = command(config, ["login", "status"], case)
            login = subprocess.run(
                prefix, capture_output=True, text=True, env=environment, timeout=30, check=False
            )
            test = r"""from pathlib import Path
import json
from conjecture_solver.execution_pool import MachineRegistry
assert not Path('/srv/operator-vault').exists()
assert not Path('/private/operator-memory').exists()
assert not Path('/srv/simjecture/research/decision_training/tasks/dev.jsonl').exists()
assert not Path('/srv/simjecture/research/decision_training/sealed/test.aesgcm').exists()
registry=MachineRegistry('/srv/simjecture/research/decision_training/controller-machine-registry')
probe=registry.transport('remote-cpu').call('probe',timeout=30)
assert probe['capacity']['cpus']==32
print(json.dumps(dict(vault_hidden=True,history_hidden=True,unassigned_tasks_hidden=True,
                     remote_worker_ready=probe['execution']['available'],scientific_studies=0)))
"""
            index = prefix.index("--")
            check = subprocess.run(
                prefix[: index + 1] + ["/app/bin/python", "-c", test],
                capture_output=True,
                text=True,
                env=environment,
                timeout=45,
                check=False,
            )
            server.shutdown()
            if login.returncode or check.returncode:
                raise RuntimeError(
                    json.dumps(
                        dict(
                            login_exit=login.returncode,
                            login_error=login.stderr[-1200:],
                            check_exit=check.returncode,
                            check_error=check.stderr[-2000:],
                        )
                    )
                )
            report = json.loads(check.stdout)
            report["native_codex_authentication_readable"] = True
            report["LLM_calls"] = 0
            (ROOT / "reports/isolation_checks.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            print(json.dumps(report))


if __name__ == "__main__":
    main()
